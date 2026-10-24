#!/usr/bin/env python3
"""Inspect retained access evidence; probe once only after a runtime revision change."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, proxy_bypass

HERE = Path(__file__).resolve().parent
URL = 'https://www.youtube.com/watch?v=fZmY4xS_qXE'


class HTTPSWatchRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, target):
        parsed = urlsplit(target)
        if parsed.scheme != 'https' or parsed.hostname not in {'www.youtube.com', 'youtube.com'} or parsed.username or parsed.password:
            raise ValueError('Preflight redirect left the HTTPS YouTube origin; no redirected request made')
        if proxy_bypass(parsed.hostname):
            raise ValueError('Redirect target would bypass the configured proxy')
        return super().redirect_request(request, response, code, message, headers, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', help='Make one ordinary request; default is offline inspection')
    parser.add_argument('--runtime-snapshot', type=Path)
    parser.add_argument('--reason', help='Concrete configuration change or new diagnosis, not simply another retry')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    prior = []
    for path in (HERE / 'diagnostics').glob('*watch-probe.json'):
        row = json.loads(path.read_text())
        prior.append({'path': str(path.relative_to(HERE)), **row})
    if not args.probe:
        print(json.dumps({'mode': 'offline_inspection', 'networkRequests': 0, 'watchEvidence': prior}, indent=2))
        return
    if not args.runtime_snapshot or not args.output or not args.reason:
        parser.error('--probe requires --runtime-snapshot, --reason and a new --output path')
    if args.output.resolve().parent != (HERE / 'diagnostics').resolve() or not args.output.name.endswith('watch-probe.json'):
        parser.error('Keep a dated *watch-probe.json in diagnostics/ so later runs can see existing denials')
    runtime = json.loads(args.runtime_snapshot.read_text())
    revision = str(runtime.get('observed_spec_revision', ''))
    if not runtime.get('observations_current') or not revision:
        parser.error('A current supported runtime observation is required')
    for row in prior:
        if row.get('proxyTunnelDenied') and str(row.get('runtimeObservationBeforeProbe', {}).get('specRevision')) == revision:
            parser.error('Same-revision proxy denial already recorded; use supported configuration/platform diagnosis instead of retrying')
    if args.output.exists():
        parser.error('Output already exists; preserve dated observations')
    if not (os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')):
        parser.error('The inherited HTTPS proxy is required; direct fallback is disabled')
    if proxy_bypass('www.youtube.com'):
        parser.error('The target is excluded from the configured proxy; direct fallback is disabled')
    result = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'url': URL,
              'method': 'ordinary urllib HTTPS GET through inherited proxy with TLS verification enabled',
              'purpose': args.reason, 'proxyConfigurationPreserved': True, 'tlsVerificationEnabled': True,
              'runtimeObservationBeforeProbe': {'mode': runtime.get('network_policy', {}).get('mode'),
                                               'state': runtime.get('network_policy', {}).get('state'),
                                               'specRevision': revision, 'observationsCurrent': True}}
    try:
        with build_opener(HTTPSWatchRedirect()).open(Request(URL, headers={'User-Agent': 'channels-ET-public-source-preflight/1'}), timeout=30) as response:
            body = response.read(2 * 1024 * 1024)
            looks_like_watch = b'ytInitialPlayerResponse' in body or b'ytInitialData' in body
            final = urlsplit(response.geturl())
            expected_id = parse_qs(urlsplit(URL).query)['v'][0]
            final_watch = (final.scheme == 'https' and final.hostname in {'www.youtube.com', 'youtube.com'}
                           and not final.username and not final.password and final.path == '/watch'
                           and parse_qs(final.query).get('v') == [expected_id])
            result.update(status='success' if response.status == 200 and looks_like_watch and final_watch else 'response_received_unconfirmed',
                          http_status=response.status, httpStatus=response.status, contentType=response.headers.get('Content-Type'),
                          bytesInspected=len(body), pageLooksLikeWatch=looks_like_watch, finalHttpsWatchIdentityVerified=final_watch,
                          sanitizedFinalOrigin=f'{final.scheme}://{final.hostname}', finalPath=final.path,
                          expectedVideoId=expected_id, finalQueryKeysOnly=sorted(parse_qs(final.query)))
    except Exception as exc:
        result.update(status='request_failed', errorType=type(exc).__name__, error=str(exc),
                      proxyTunnelDenied='Tunnel connection failed: 403' in str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
