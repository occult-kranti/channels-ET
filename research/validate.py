"""Validate relationships and chronology integrity of the published atlas."""
import json,re
from pathlib import Path
from urllib.parse import urlparse
root=Path(__file__).resolve().parent.parent
d=json.loads((root/'dist/data.json').read_text())
source_ids={s['id'] for s in d['sources']}
assert len(source_ids)==len(d['sources']), 'Duplicate source ID'
assert len({s['url'].rstrip('/') for s in d['sources']})==len(d['sources']), 'Duplicate source URL'
for source in d['sources']:
    u=urlparse(source['url']);assert u.scheme=='https' and u.netloc,source
    assert source['notes'] and source['accessed']=='2026-10-22',source['id']
for key in ['profiles','events','entities','communityItems','videoItems','insights','forecasts']:
    for row in d[key]:
        assert row.get('sourceIds'),(key,row)
        assert not(set(row['sourceIds'])-source_ids),(key,row)
for profile in d['profiles']:
    assert profile['dateBasis'] and profile['datePrecision'],profile['id']
    assert profile['caveats'] and profile['claims'],profile['id']
profile_ids={p['id'] for p in d['profiles']}
assert len(profile_ids)==len(d['profiles'])
for entity in d['entities']:assert not(set(entity['profileIds'])-profile_ids),entity
for event in d['events']:
    assert re.match(r'^\d{4}(?:-\d{2}(?:-\d{2})?)?(?:–\d{4})?$',event['date']),event
    assert int(event['date'][:4])<=2026,event
assert next(x for x in d['profiles'] if x['id']=='hr-ra')['firstDate']=='1981-01-15'
assert next(x for x in d['profiles'] if x['id']=='ar-athina-ashtar')['datePrecision'].startswith('Exact publication')
assert len(d['forecasts'])==2 and all('Future' in f['status'] for f in d['forecasts'])
assert {c['platform'].split(' · ')[0] for c in d['communityItems']}=={'Reddit','WizardForums','BALG'}
print(f"Validated {len(d['sources'])} sources, {len(d['profiles'])} profiles, {len(d['events'])} events and all cross-references.")
