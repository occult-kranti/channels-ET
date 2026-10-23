# GitHub Pages deployment

The public entry is https://occult-kranti.github.io/channels-ET/. Root `index.html` sends ordinary visits to `dist/research/`; existing `#/…` atlas links continue to `dist/`. The artifact preserves the complete `dist/` directory, including historical dashboards and downloadable research outputs. All paths retain the `/channels-ET/` project prefix.

`.github/workflows/pages.yml` deploys on pushes to `main` that change the root entry, `.nojekyll`, `dist/`, deployment scripts, or the workflow. It also supports manual workflow dispatch. A receipt-only commit under `research/deployment/` therefore does not redeploy or change the source commit recorded in the live artifact. Rebuild changed research into `dist/` before publishing it. The build job reads repository content and Pages metadata. Only the separate deployment job receives Pages-write and OIDC-token permissions. All official Actions are pinned to immutable commits. The workflow packages the retained static release; it does not collect YouTube material, train models, or recompute research. Acquisition network restrictions are not bypassed through Actions.

Run the same static preparation and project-prefix checks locally with Python 3.10 or newer, using a fresh output directory:

```sh
python3 scripts/pages/stage_site.py --output /tmp/channels-et-pages-site
python3 scripts/pages/verify_site.py --directory /tmp/channels-et-pages-site --serve-prefix /channels-ET/
```

The stage contains `deployment-manifest.json`, recording the checkout commit, whether root/static inputs have uncommitted changes, and SHA-256/size of every staged file except that manifest itself. A local working-tree preflight binds staged bytes through those hashes; its checkout commit alone does not certify uncommitted changes. The production workflow checks out the committed release. Verification checks every local file, then requests ten representative routes over HTTP at the project prefix and checks response bytes against the manifest. The download checks include the paper, source archive, LoRA adapter archive, and Q&A SQLite database. Static checking does not execute browser JavaScript; browser interaction is checked separately by the dashboard review.

When `dist/research/harvest.js` exists in the deployment manifest, verification also downloads that script and every published `harvest-*` file and checks their hashes. It reconciles the dashboard data with the downloadable source summaries, the complete worker ledger with the inventory-derived video/channel/playlist universe, operation attempts and state counts, and SQLite counts with JSON/JSONL inventories. It recomputes publisher download totals and ASR totals and joins each ASR receipt to its completed publisher source by ID, audio hash and enclosure URL. These checks use the bound manifests rather than fixed expected future counts. They inspect public bookkeeping only: no private raw paths or external media URLs are followed, and no media collection runs in Actions.

After Actions succeeds, verify the real site and retain an operational receipt:

```sh
python3 scripts/pages/verify_site.py --base-url https://occult-kranti.github.io/channels-ET/ --expected-commit FULL_COMMIT_SHA --receipt research/deployment/live-verification.json
gh run list --repo occult-kranti/channels-ET --workflow pages.yml
```

GitHub Pages must use **GitHub Actions** as its build source. It was already configured this way during the initial preflight. No personal token is saved in this repository; hosted Actions uses its scoped `GITHUB_TOKEN` and OIDC. Local administration reuses supported injected GitHub authentication without displaying credentials.
