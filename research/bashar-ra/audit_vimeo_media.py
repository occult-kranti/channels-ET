#!/usr/bin/env python3
"""Hash-bound packet/log audit of retained public publisher audio editions.

Continuity and transport evidence do not verify a speaker, an original historical
session, or every audible word. No media is downloaded or altered by this tool.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import acquire_bashar as B


def packet_summary(probe, gap_tolerance=.05):
    rows=probe['packets']
    if not rows:raise ValueError('No audio packets')
    positive=[float(r.get('duration_time',0)) for r in rows if float(r.get('duration_time',0))>0]
    if not positive:raise ValueError('Packet durations are unavailable')
    typical=statistics.median(positive);ends=[];starts=[]
    for row in rows:
        start=float(row['pts_time']);duration=float(row.get('duration_time',0)) or typical
        if not math.isfinite(start) or not math.isfinite(duration) or duration<0:raise ValueError('Invalid packet time')
        if starts and start<starts[-1]-.001:raise ValueError('Nonmonotonic audio packet timestamps')
        starts.append(start);ends.append(start+duration)
    gaps=[{'after_packet':i,'end_seconds':ends[i],'next_start_seconds':starts[i+1],'gap_seconds':starts[i+1]-ends[i]}
        for i in range(len(rows)-1) if starts[i+1]-ends[i]>gap_tolerance]
    return {'packet_count':len(rows),'first_pts_seconds':starts[0],'last_end_seconds':ends[-1],
        'median_packet_duration_seconds':typical,'gap_tolerance_seconds':gap_tolerance,
        'duration_zero_fallback':'Median positive packet duration; handles first AAC packet with missing/zero duration metadata',
        'boundary_anomalies':([{'kind':'nonzero_initial_pts','observed_seconds':starts[0],'expected_seconds':0.0}] if abs(starts[0])>gap_tolerance else [])+([{'kind':'terminal_pts_vs_container','observed_seconds':ends[-1],'expected_seconds':float(probe['format']['duration'])}] if abs(ends[-1]-float(probe['format']['duration']))>gap_tolerance else []),
        'gaps_over_tolerance':gaps,'gap_total_seconds':sum(r['gap_seconds'] for r in gaps),
        'max_gap_seconds':max((r['gap_seconds'] for r in gaps),default=0.)}


def require_pass(audit_path, publication_id, audio_sha256):
    """Recheck a positive exact-edition audit before downstream reuse/inference."""
    audit_path=B.private_path(audit_path);data=B.read(audit_path)
    matches=[r for r in data['records'] if r['publication_id']==publication_id and r['audio_sha256']==audio_sha256]
    if len(matches)!=1 or matches[0]['disposition']!='passed':raise ValueError('Exact media edition lacks a unique passed integrity audit')
    row=matches[0];B.verify_artifact(row['source_audio']['path'],row['source_audio'])
    packet_path=B.verify_artifact(row['raw_packet_probe']['path'],row['raw_packet_probe'])
    raw=gzip.decompress(packet_path.read_bytes())
    if len(raw)!=row['raw_uncompressed_bytes'] or hashlib.sha256(raw).hexdigest()!=row['raw_uncompressed_sha256']:
        raise ValueError('Packet audit evidence changed')
    checked=packet_summary(json.loads(raw),.05)
    if checked['gaps_over_tolerance'] or checked['boundary_anomalies']:raise ValueError('Packet continuity or boundary audit failed')
    if row.get('download_log'):
        log=B.verify_artifact(row['download_log']['path'],row['download_log'])
        if re.search(r'HTTP Error\s+[45][0-9][0-9]|unavailable fragment|Skipping fragment|Got error',log.read_text(),re.I):
            raise ValueError('Recorded transport failure prohibits complete-source admission')
    return B.artifact(audit_path,'media_integrity_audit')


def audit(media_manifest, output, boundary=None, repairs=(), gap_tolerance=.05, reuse_audit=None):
    if not math.isfinite(gap_tolerance) or gap_tolerance<0 or gap_tolerance>.05:raise ValueError('Gap tolerance must be between zero and50ms')
    media_manifest=B.private_path(media_manifest);output=B.private_path(output,False)
    if output.exists():raise ValueError('Choose a fresh audit directory')
    output.mkdir(parents=True,mode=0o700);packets=output/'packets';packets.mkdir(mode=0o700)
    items=[];manifest=B.read(media_manifest)
    previous={r['audio_sha256']:r for r in B.read(B.private_path(reuse_audit))['records']} if reuse_audit else {}
    executed=output/'executed-sources';executed.mkdir(mode=0o700)
    audit_code=executed/'audit_vimeo_media.py';audit_code.write_bytes(Path(__file__).read_bytes())
    helper_code=executed/'acquire_bashar.py';helper_code.write_bytes(Path(B.__file__).read_bytes())
    for row in manifest['records']:
        if row['status']=='completed':
            rp=B.verify_artifact(row['receipt']['path'],row['receipt']);rec=B.read(rp)
            items.append({'publication_id':rec['source_id'],'source_audio':rec['audio'],'acquisition_receipt':B.artifact(rp,'acquisition_receipt'),
                'source_edition':'initial','log_path':str(rp.parent/'download.log')})
    for value in repairs:
        rp=B.private_path(value);rec=B.read(rp)
        items.append({'publication_id':rec['source_id'],'source_audio':rec['audio'],'acquisition_receipt':B.artifact(rp,'repair_acquisition_receipt'),
            'source_edition':'strict_repair','log_path':str(rp.parent/'download.log')})
    if boundary:
        boundary=B.private_path(boundary);rec=B.read(boundary)
        items.append({'publication_id':rec['source_id'],'source_audio':rec['unadmitted_retained_artifact'],
            'eligibility_exclusion':B.artifact(boundary,'duration_exclusion'),'source_edition':'duration_boundary','log_path':str(Path(rec['unadmitted_retained_artifact']['path']).parent/'download.log')})
    distinct={item['source_audio']['sha256']:item['source_audio'] for item in items}
    def inspect(binding):
        audio=B.verify_artifact(binding['path'],binding)
        command=['ffprobe','-v','error','-select_streams','a:0','-show_packets','-show_entries',
            'format=duration,start_time:stream=codec_name,sample_rate,start_time,duration:packet=pts_time,duration_time,size','-of','json',str(audio)]
        if binding['sha256'] in previous:
            prior=previous[binding['sha256']];compressed=B.verify_artifact(prior['raw_packet_probe']['path'],prior['raw_packet_probe'])
            raw=gzip.decompress(compressed.read_bytes())
            if len(raw)!=prior['raw_uncompressed_bytes'] or hashlib.sha256(raw).hexdigest()!=prior['raw_uncompressed_sha256']:raise ValueError('Retained packet probe changed')
        else:raw=subprocess.check_output(command,timeout=120)
        probe=json.loads(raw);summary=packet_summary(probe,gap_tolerance)
        target=packets/(binding['sha256']+'.json.gz');target.write_bytes(gzip.compress(raw,mtime=0))
        return binding['sha256'],{'packet_summary':summary,'container_duration_seconds':float(probe['format']['duration']),
            'streams':probe.get('streams',[]),'raw_packet_probe':B.artifact(target,'ffprobe_packets_json_gzip'),
            'raw_uncompressed_sha256':hashlib.sha256(raw).hexdigest(),'raw_uncompressed_bytes':len(raw)}
    with ThreadPoolExecutor(max_workers=2) as pool:results=dict(pool.map(inspect,distinct.values()))
    records=[]
    for item in items:
        binding=item['source_audio'];r=results[binding['sha256']];log=Path(item['log_path'])
        log_binding=B.artifact(log,'download_log') if log.exists() else None
        contents=log.read_text() if log.exists() else ''
        transport_error=bool(re.search(r'HTTP Error\s+[45][0-9][0-9]|unavailable fragment|Skipping fragment|Got error',contents,re.I))
        continuous=not r['packet_summary']['gaps_over_tolerance'] and not r['packet_summary']['boundary_anomalies']
        integrity=continuous and not transport_error
        disposition=('excluded_below_actual_duration' if item['source_edition']=='duration_boundary' else ('passed' if integrity else 'failed_integrity'))
        records.append({**item,**r,'audio_sha256':binding['sha256'],'integrity_status':'passed' if integrity else 'failed',
            'disposition':disposition,'transport_error_recorded':transport_error,'download_log':log_binding,
            'log_observation':'Retained downloader error/warning log inspected' if log.exists() else 'No error/warning log file; packet continuity is the positive independent check'})
    result={'schema_version':1,'kind':'publisher-audio-fragment-and-packet-audit','checked_at':B.now(),
        'records':records,'source_manifest':B.artifact(media_manifest,'initial_acquisition_manifest'),
        'code':B.artifact(audit_code,'executed_audit_code'),'helper_code':B.artifact(helper_code,'artifact_validation_code'),'reused_packet_audit':B.artifact(reuse_audit,'prior_packet_probe_audit') if reuse_audit else None,
        'protocol':{'workers':2,'gap_tolerance_seconds':gap_tolerance,'audio_changed':False,'network_requests':0,
            'checks':['Exact media SHA/size','All first-audio-stream packet timestamps, initial zero and terminal container boundary','Retained downloader warning/error logs']},
        'summary':{'edition_rows':len(records),'distinct_media_hashes':len(distinct),'dispositions':dict(__import__('collections').Counter(r['disposition'] for r in records))},
        'limits':'Pass means no detected packet gap above tolerance and no recorded transport error; it does not verify historical full-session coverage, speech accuracy, voice identity or source claims.'}
    B.write(output/'manifest.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--media-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--boundary',type=Path);p.add_argument('--repair',type=Path,action='append',default=[]);p.add_argument('--gap-tolerance',type=float,default=.05);p.add_argument('--reuse-audit',type=Path)
    a=p.parse_args();print(json.dumps(audit(a.media_manifest,a.output,a.boundary,a.repair,a.gap_tolerance,a.reuse_audit)['summary'],indent=2))
if __name__=='__main__':main()
