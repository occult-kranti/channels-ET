#!/usr/bin/env python3
"""Build a concise source/depth register from actual public documentation receipts."""
import hashlib
import json
import pathlib

H = pathlib.Path(__file__).resolve().parent
records = []
for name in ['fetch-receipts.json', 'fetch-source-code.json']:
    for row in json.loads((H / name).read_text())['records']:
        records.append({**row, 'receipt_file': name})
records += [{**r, 'receipt_file': 'fetch-publisher-leads.json'} for r in json.loads((H / 'fetch-publisher-leads.json').read_text())['records'] if r['id'] == 'github-pages-limits']
records += [{**r, 'status': 'retrieved', 'requested_url': r['source_url'], 'receipt_file': 'wiki-receipt.json'} for r in json.loads((H / 'wiki-receipt.json').read_text())['records']]
notes = {
 'yt-dlp-readme': ('Official project reference; selected update/licensing/dependency/CLI sections read, not the whole179KB file', 'README lines139–174,203–215,317–397,493–595,675–690,775–805,840–850,888–910', 'EJS/runtime dependencies, API/CLI semantics, resume/archive, fragment concurrency, subtitle selection, error and finite-retry options', 'Documentation does not establish this environment can access YouTube; HEAD docs are distinct from the installed release.'),
 'yt-dlp-license': ('Official license; full short file read', 'LICENSE entire file', 'yt-dlp core is Unlicense', 'Bundled executables/dependencies have different licenses; do not apply the core license to acquired media.'),
 'yt-dlp-version': ('Official version module; full short file read', 'yt_dlp/version.py', 'HEAD version string2026.10.21 and recorded release commit', 'MainHEAD and release commit are different pins, even when version strings match.'),
 'ejs-readme': ('Official runtime/installation/licensing sections read', 'Runtime requirements table; Manual Installation; Licensing', 'Runtime minima Deno2.3/Node22, deprecated Bun range, separate developer requirements, Unlicense with MIT/ISC bundled components', 'Developer tool versions differ from end-user runtime minima; no EJS challenge was executed.'),
 'ejs-license': ('Official license; full short file read', 'LICENSE entire file', 'EJS core Unlicense', 'Its wheels contain MIT/ISC components; no license on publisher media is implied.'),
 'yt-dlp-pypi': ('Official package-index metadata; info.version/requires_python/requires_dist inspected', 'info.version,info.requires_python,info.requires_dist', 'Stable2026.10.21 requires Python>=3.10; default extra pins EJS0.8.0', 'Retrieved index metadata is not an installation or signature validation of a wheel.'),
 'github-large-files': ('Official online article; main size/distribution sections read', 'File size limits; Repository size limits; Distributing large binaries', '50MiB warning/100MiB block/browser25MiB; prefer small code repositories', 'Generic release-size text differs from release-specific article; use stricter bound and account-plan checks.'),
 'github-repository-limits': ('Official online article; repository-size and activity sections read', 'Repository size; Activity', '10GB on-disk recommendation,2GB enforced push,100MB enforced single-object limit; generated files in object storage', 'Recommendations are not unlimited entitlements; same article names additional UI/operation limits.'),
 'github-lfs': ('Official online article; complete short main text read', 'Plan/file-size table; pointer format; notes', 'LFS stores objects separately,2/4/5GB per-file plan limits; not supported by GitHubPages', 'Does not identify this account plan or authorize media redistribution.'),
 'github-releases': ('Official online article; storage/bandwidth section read', 'Storage and bandwidth quotas', 'Up to1000 assets/release; each under2GiB; no stated total size/bandwidth limit', 'No automatic rights basis to publish third-party recordings; use specific limit over generic conflicting phrasing.'),
 'github-lfs-billing': ('Official online article; measurement,free allowances,budget sections read', 'How use is measured; Free use; Using more; Managing budget', 'Free/Pro10GiB storage+download allowance; whole binary versions and archive downloads count; budgets affect blocking/billing', 'No account-specific usage or price quote established.'),
 'github-pages-limits': ('Official online article; usage limits read', 'Usage limits', 'Published site<=1GB;100GB/month soft bandwidth;10min deploy timeout;10build/hour exception for customActions workflows', 'Static hosting quotas are separate from repository and LFS quotas.'),
 'yt-dlp-pyproject': ('Official project source; optional dependency pins inspected', 'project.optional-dependencies.default', 'Matched EJS dependency requirement for the inspected source', 'MainHEAD source pin is not a claim to be byte-identical to installed release.'),
 'yt-dlp-youtubedl': ('Official implementation; selected subtitle/archive/skip-download methods inspected', 'process_subtitles3155–3205; skip_download3457; archive-write3144/3372', 'Manual subtitles shadow same-language automatic captions; simulated/skipped media archive writes need forcing', 'No source-media extraction was performed during code inspection.'),
 'yt-dlp-http-downloader': ('Official implementation; known-size check and download loop inspected', 'download(): Content-Length and max_filesize around lines200–230', 'Known-size cap depends on observed Content-Length; external raw-budget checks remain necessary', 'Does not claim every downloader/protocol has identical cap behavior.'),
 'wiki-ejs': ('Official maintained online setup guide; runtime and installation sections read', 'Step1/Step2 runtime tables and package-version matching', 'Only Deno default enabled; Node needs explicit selection; compatible EJS required; default extra installation', 'Remote-component delivery is unnecessary with installed compatible package; not a denial workaround.'),
 'wiki-faq': ('Official maintained online FAQ; archive,dependencies,403/429 sections inspected', 'How to download only new videos; dependencies; HTTP errors', 'Archive records successful downloads; ffmpeg requirements; origin/bot errors differ from transport failures', 'Cookie/IP/proxy recipes present in the FAQ are explicitly not adopted for this task.'),
 'wiki-installation': ('Official maintained online installation guide; pip/updates sections inspected', 'Using the release binary; With pip', 'Use supported installation/update routes and compatible dependency extras', 'No install command executed by the documentation reviewer.'),
}
out = []
for row in records:
    depth, locations, support, limitation = notes[row['id']]
    entry = {k: row.get(k) for k in ['id', 'requested_url', 'final_url', 'attempted_at', 'retrieved_at', 'status', 'http_status', 'bytes', 'sha256', 'commit', 'path', 'receipt_file'] if row.get(k) is not None}
    entry.update(read_depth=depth, locators=locations, supported_use=support, limits=limitation,
                 source_class='official_project_or_platform_documentation_not_peer_reviewed_evidence')
    if row['id'].startswith('yt-dlp-') and row['id'] != 'yt-dlp-pypi':
        entry['repository_commit'] = 'fa9886678eb65103303c627b8e013f13f8999b41'
    if row['id'].startswith('ejs-'):
        entry['repository_commit'] = '6f8587bb7009a1fc81038538071d2cb66b8b8ed0'
    out.append(entry)
assert len(out) == len({x['id'] for x in out}) == 18
result = {'checked_on': '2026-10-23', 'scope': 'Targeted current official tool/platform documentation audit, not a paper review or systematic search.',
          'sources': out, 'source_count': len(out), 'retrieval': 'Ordinary HTTPS/Git via inherited session proxy and CA; TLS verification preserved.',
          'raw_document_cache': 'source-cache/ is local and ignored; hashes and reading depth retained publicly.',
          'youtube_network_requests_by_this_reviewer': 0,
          'known_current_failure': 'Coordinator revision5 preflight records proxyCONNECT403 beforeTLS; tool/runtime changes do not repair that transport denial.',
          'recommendations_file': 'RECOMMENDATIONS.md'}
(H / 'source-register.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'sources': len(out), 'all_retrieved': all(x['status'] == 'retrieved' for x in out),
                  'register_sha256': hashlib.sha256((H / 'source-register.json').read_bytes()).hexdigest()}, indent=2))
