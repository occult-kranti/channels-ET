# Methods implementation handoff

Final source-bound artifacts are private; copy only each output manifest's public allowlist.

| Study | Private directory under `/workspace/channels-et-private/expanded-channeling-2026-11/` | Public JSON SHA256 |
| --- | --- | --- |
| 292-unit joint source-context fit | `analysis/final-02` | `34ac7bbeb61d83f8d782392008c39e252a335381b8b481c88258c1130e7a6722` |
| 20 new written messages, title sensitivity | `pilot/final-02` | `2fd5c74456ffe522f382d3ba800c128c8d8316abd2b8fd42e719877d0cc2d8b6` |
| Three-context audio/caption/ASR snapshot | `collected-audio/three-context-final-02` | `ef96c13266ca90bd87377eda124d9a2bac215e33e1f33ebda3bdba96f8eff66c` |
| 20-message neural contrast + bounded reading | `semantic-pilot/final-01` | `014c5f5bef87898e284d2e0342225fc1c2c5a1e5b6e91192fb194efec6e80cd5` |

The first two filenames are `analysis.json` and `new-message-pilot.json`; the last two are `collected-audio-analysis.json` and `semantic-pilot.json`. Figure directories in the dashboard are respectively `figures/`, `pilot-figures/`, `collected-audio-figures/`, and `semantic-figures/`. The counts are different overlapping studies, not additive independent sessions.

The exact live shipped-register graph is built with `claim_graph.py` from **sanitized public registers**, not private-register bytes. `verify_registry.py` recomputes it against those shipped bytes and the pilot. The most recent graph membership fix incorporates explicit `channellees[].comparison_group_id` declarations while preserving distinct label IDs, shared practice dependence and edge types.

Independent review receipts are in the private `review/` directory. The main critic reconstructed joint, pilot and collected TF-IDF matrices and neural vector-derived cells; the scoped collected-audio review additionally checked 243 artifacts and original RSS joins. No independent NMF/KMeans rerun is asserted.

For a later collection edition, run the producer against completed acquisition/ASR manifests with a **fresh** output directory. It snapshots exact bytes before fitting and supports repeated `--asr` options. Do not mutate these accepted outputs or promote later acquisition counts into an older fitted study. New manifests can contain more records; the public collection study verifier is count-generic. The fixed 292-unit and 20-message verifiers intentionally enforce their frozen denominators.

The legacy helpers remain unchanged:

- `research/bashar-ra/analyze.py`: `6f4d9ab73ad479b7d84e7a299a5c74276847d961030d98cdb2ad059b40b30506`
- `research/batch-media/audio.py`: `7308256c26471a65561d685edc26e693cc0a771fdab6fcb02ce3c38559f3af64`
