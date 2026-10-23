# Dashboard round 10 — baseline and first continuation build

Reviewer: AI design/implementation role; not human participant research or independent human peer review.

## Baseline

The new cross-channel repository starts at `faefa36`. Its historical atlas and the imported five-view expansion explorer preserve the earlier source evidence. The original Bashar repository was not edited. This work owns only `research/continuation/dashboard/`, `dist/research/`, this role's review records, and one additive navigation link in the new repository's existing `dist/app.js`.

The prior explorer distinguishes 925 metadata records, 30 English caption derivatives, and 949 digest-paraphrase Q&A candidates in one Darryl Anka context. It does not provide a local-generation/training experiment view, a continuation leakage analysis, or an integrated operation-level collection index.

## Implemented candidate

- Four task views: research overview; local-model experiments; collection and coverage; methods and artifacts.
- Actual continuation analytical figures with exact captions and downloadable numerical results; pending figures/results are not fabricated.
- A local-model view that requires a result artifact before showing arm performance. At this first browser pass no completed benchmark artifact existed, so the UI explicitly said pending; a model download was not counted as inference or training.
- Per-candidate collection rows from the new dated acquisition manifest, enriched only by an exact inherited candidate-ID bridge to contextual entity labels. General access-probe failures were not assigned as individual candidate failures.
- Filtered coverage CSVs, public database/download routes, exact per-artifact SHA-256 display, and links to the preserved evidence explorer and historical atlas.
- A build that copies an explicit allowlist of derived artifacts, not raw captions, model weights, adapter checkpoints or local training caches.

## Executed verification

`dashboard/round10-browser.json` records **39 passing checks, zero page errors** for the first candidate. It covers all four views at 1440px and 390px widths, the explicit pending model state, candidate/alias filtering, filtered CSV scope, truthful unattempted states, empty search, keyboard form submission, keyboard disclosure, 200% CSS zoom reflow and byte-bound artifact downloads. Screenshots were produced and the desktop overview was visually inspected. This does not establish a full accessibility audit or a model result.

## Issues carried to the next review

Integrate actual benchmark/training/prediction outputs once the model workstream finishes; bind the current paper/source package; verify metric denominators and proxy interpretation against the executed evaluator; independently inspect model examples and source-leakage exclusions; then rerun browser/download/source checks on that changed candidate. Model-data presence and successful arms must remain distinct.

The shared Data App Contract resource read failed again, and no Sites/browser deployment tool is callable. The existing buildless stack is extended deliberately. Local verification does not establish a published Site or shared Data runtime compliance.

## Complete first candidate after the model workstream executed

Before the round-10 freeze, the five-arm benchmark and 14-page paper became available. The dashboard was updated to actual completed CPU/LoRA metrics, the 48-example/48-microstep/12-update/65.04-second training receipt, all 50 prediction outputs, a keyboard-operable question/control inspector, source-retrieval details, exact n=8 question and n=2 control denominators, a clearly labeled strict `INSUFFICIENT_EVIDENCE` marker metric, and the current paper/source/adapter downloads. A plain-language refusal can score zero under that strict marker metric, so zero is not described as failure to refuse. No general RAG-versus-fine-tuning superiority claim is made. The small adapter is an explicitly labeled derived pilot requiring the pinned base; base weights remain excluded.

Only affected model/paper/download bindings were rechecked: `dashboard/round10-model-bindings.json` records **64 passing focused checks, zero page errors**, including actual fields/outputs, keyboard selection, narrow and 200% CSS zoom layout, all public artifact HTTP routes, displayed hashes and source/public byte equality. The prior full four-view interaction checks remain applicable to unchanged views. Current-family Qwen3.5 smoke testing is still a separate pending experiment.
