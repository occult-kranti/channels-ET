#!/usr/bin/env python3
"""Independently compile the released source ZIP and check actual paper bindings."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;PAPER=ROOT/'research/transcript-paper'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def output(command,**kwargs):return subprocess.check_output(command,text=True,**kwargs)
def run():
    pdf=PAPER/'channels-et-transcript-paper.pdf';bundle=PAPER/'channels-et-transcript-source.zip';manifest=json.loads((PAPER/'input-manifest.json').read_text());checks=[]
    def check(name,ok):checks.append({'name':name,'passed':bool(ok)});assert ok,name
    for row in manifest['files']:
        path=ROOT/row['path'];check('source_input:'+row['path'],path.stat().st_size==row['bytes'] and sha(path)==row['sha256'])
    released_text=output(['pdftotext',str(pdf),'-']);flat=' '.join(released_text.replace('-\n','').split())
    audio=flat.find('Excluding the declared commercial vocabulary in the audio')
    written=flat.find('The separate written commercial')
    check('commercial_audio_scope_corrected',audio>=0 and '0.998' in flat[audio:audio+400] and '90 percent' in flat[audio:audio+400])
    check('commercial_authored_scope_separate',written>=0 and '1.000' in flat[written:written+400] and '100 percent' in flat[written:written+400])
    check('weak_written_cluster_retained','0.057' in flat and 'separately fitted written clustering' in flat)
    check('multiwindow_synthesis_scope_corrected','Each source synthesis combines the listed inspected windows' in flat)
    for value in ('226,093','226,138','13,575','13,556','11,992','6,319','13,656','1,703,635,307','1,703,879,268'):
        check('numeric_text_presence:'+value,value in released_text)
    info=output(['pdfinfo',str(pdf)]);pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1))
    fonts=output(['pdffonts',str(pdf)]);check('no_type3_fonts','Type 3' not in fonts)
    check('fonts_embedded',all(line.split()[-5]=='yes' for line in fonts.splitlines()[2:] if line.strip()))
    compile_results=[]
    with tempfile.TemporaryDirectory(prefix='transcript-independent-source-') as temp:
        work=Path(temp)
        with zipfile.ZipFile(bundle) as archive:
            for row in archive.infolist():
                check('zip_safe_path:'+row.filename,not row.filename.startswith('/') and '..' not in Path(row.filename).parts and not stat.S_ISLNK(row.external_attr>>16))
                check('zip_no_raw_media:'+row.filename,Path(row.filename).suffix.lower() not in ('.mp3','.mp4','.m4a','.wav','.srt','.vtt','.safetensors'))
            archive.extractall(work)
        env=dict(os.environ,SOURCE_DATE_EPOCH='1792800000',FORCE_SOURCE_DATE='1',TEXMFHOME='/workspace/channels-et-tex/texmf',TEXMFVAR=str(work/'texvar'),TEXMFCONFIG=str(work/'texconfig'),TEXFONTMAPS='/workspace/channels-et-tex/var/fonts/map//:')
        commands=[['pdflatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','main.tex'],['bibtex','main'],
                  ['pdflatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','main.tex'],['pdflatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','main.tex']]
        for command in commands:
            result=subprocess.run(command,cwd=work,env=env,text=True,capture_output=True)
            if result.returncode:(HERE/'paper-clean-compile-failure.txt').write_text(result.stdout+result.stderr)
            check('independent_compile:'+command[0],result.returncode==0)
            compile_results.append({'command':command,'exit_code':result.returncode})
        compiled_text=output(['pdftotext',str(work/'main.pdf'),'-']);check('clean_source_pdf_text_exact',compiled_text==released_text)
        log=(work/'main.log').read_text();check('no_overfull_boxes','Overfull \\hbox' not in log)
        check('no_undefined_citations',not re.search(r'(?:Citation|Reference).*undefined|There were undefined',log))
        compiled_sha=sha(work/'main.pdf')
    return {'schema_version':1,'status':'pass','pdf_sha256':sha(pdf),'source_zip_sha256':sha(bundle),'pages':pages,'input_hashes_checked':len(manifest['files']),
            'checks':len(checks),'failed_checks':[x for x in checks if not x['passed']],
            'independent_clean_compilation':compile_results,'compiled_pdf_sha256':compiled_sha,'compiled_text_exact':True,
            'byte_identical_pdf_required':False,'scope':'Independent direct source/input/PDF-text/font/clean-ZIP checks; selected rendered pages and UI review are recorded separately',
            'prepared_fontmaps_read_only':'/workspace/channels-et-tex/var/fonts/map; temporary TeX writable caches',
            'network_requests':0,'new_llm_or_asr_inference':False}
if __name__=='__main__':
    report=run();(HERE/'paper-release-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
