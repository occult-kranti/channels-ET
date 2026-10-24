# Published transcript study

The live default is [the transcript explorer](https://occult-kranti.github.io/channels-ET/dist/transcripts/).
Its [22-page paper](https://occult-kranti.github.io/channels-ET/dist/transcripts/paper.pdf)
and [Overleaf source ZIP](https://occult-kranti.github.io/channels-ET/dist/transcripts/source.zip)
match the final reviewed source bytes.

[Pages Action 40053311432](https://github.com/occult-kranti/channels-ET/actions/runs/40053311432)
succeeded for exact commit `c51a268b32201af37a9ab3501cbd016789bb8ace`.
The official Git-data API published the identical local tree and commit after
verifying 266 immutable blobs, without forcing the branch or changing local
history. The static workflow performed no media acquisition or model inference.

`live-verification.json` checks all 396 staged files and 135 actual live HTTP
routes, including the 70 source-bound transcript-study downloads. The deployment
manifest reports clean static inputs. `live-browser.json` additionally verifies
the actual public root redirect, application boot, exact data bytes and a
20-ASR-to-16-authored corpus switch through the inherited proxy with certificate
verification enabled. It records no page errors or out-of-scope page requests.
The live screenshot is `live-overview.png`.

Later research-only proof commits do not trigger another Pages build; the live
deployment source remains the commit recorded above. For an independent live
check from the current checkout, use:

```sh
python3 scripts/pages/verify_site.py \
  --base-url https://occult-kranti.github.io/channels-ET/ \
  --expected-commit c51a268b32201af37a9ab3501cbd016789bb8ace
```

The private managed-cloud archive contains 200 verified local files. This
deployment publishes metadata and derived research artifacts; it contains zero
YouTube videos and no raw recordings, full third-party transcript bodies,
browser profiles or model weights. Drive uploads remain zero. Source attribution,
recognition, semantic interpretation and sampling limitations remain in the
paper and review ledger.
