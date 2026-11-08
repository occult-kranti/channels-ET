#!/usr/bin/env python3
"""Focused parser and outbound-boundary regression controls; no network access."""
from io import BytesIO
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from urllib.error import HTTPError

from publisher_discovery import extract, fetch, follow, youtube_identity


def run():
    passed=[]
    for label,url in [('watch','https://youtube.com/watch?v=abcdefghijk'),('short','https://youtu.be/abcdefghijk'),
                      ('shorts','https://youtube.com/shorts/abcdefghijk'),('live','https://youtube.com/live/abcdefghijk'),
                      ('embed','https://youtube-nocookie.com/embed/abcdefghijk')]:
        assert youtube_identity(url)==('video','abcdefghijk','https://www.youtube.com/watch?v=abcdefghijk');passed.append(label)
    for label,url in [('deceptive_host','https://youtube.com.invalid.example/watch?v=abcdefghijk'),
                      ('non_http','javascript://youtube.com/watch?v=abcdefghijk'),
                      ('malformed_account_tracking_path','https://youtube.com/c/fxacrylics&source=gmail&ust=123'),
                      ('playlist_placeholder','https://youtube.com/embed/videoseries?list=123'),
                      ('invalid_id','https://youtu.be/too-short')]:
        assert youtube_identity(url) is None;passed.append(label)
    assert youtube_identity('https://youtube.com/channel/UCztMyD_EcSK7JxeH2cMTcdg')[0]=='channel';passed.append('explicit_uc_route')
    raw=b'<a href="https://youtu.be/abcdefghijk">x</a><iframe src="//youtube.com/embed/abcdefghijk"></iframe><a href="https://publisher.example/a.mp3">audio</a>'
    x=extract(raw,'https://publisher.example/')
    assert len(x['mentions'])==1 and x['linked_media_or_transcripts']==['https://publisher.example/a.mp3'];passed.append('deduplicated_mentions_and_separate_audio_lead')
    x=extract(b'<urlset><url><loc>https://publisher.example/message/</loc><video><player_loc>https://youtube.com/watch?v=abcdefghijk</player_loc></video></url></urlset>','https://publisher.example/sitemap.xml','application/xml')
    assert x['xml_root']=='urlset' and x['mentions'][0]['identity']=='abcdefghijk';passed.append('sitemap_video_url')
    p={'publisher_id':'test','allowed_hosts':['publisher.example'],'follow_path_patterns':['^/message/'],'max_depth':2}
    assert follow('https://publisher.example/message/',None,2,p) and not follow('https://publisher.example/message/',None,3,p);passed.append('declared_depth_boundary')
    assert not follow('https://youtube.com/watch?v=abcdefghijk',None,1,p);passed.append('youtube_never_queued')
    with tempfile.TemporaryDirectory(prefix='publisher-test-',dir='/dev/shm') as work:
        work=Path(work);(work/'pages').mkdir()
        error=HTTPError('https://publisher.example/',302,'redirect',{'Location':'https://youtube.com/watch?v=abcdefghijk'},BytesIO())
        with patch('publisher_discovery.build_opener') as opener:
            opener.return_value.open.side_effect=error
            receipt,parsed=fetch('https://publisher.example/',p,work)
            assert opener.return_value.open.call_count==1 and receipt['status']=='failed' and 'leaves declared publisher hosts' in receipt['error'] and not parsed['mentions']
        passed.append('outbound_redirect_rejected_before_second_request')
    return {'status':'passed','checks':len(passed),'cases':passed,'network_requests':0}


if __name__=='__main__':print(json.dumps(run()))
