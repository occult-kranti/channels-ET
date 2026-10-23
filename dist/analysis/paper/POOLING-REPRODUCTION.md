# Paper round 5 pooling diagnostic

The phase 1 snapshot remains pinned to f3b1eec291a8b4e82aac31fb75c679ae61ad030527915fe90e9579410a7acbcc.

## Offline regeneration

Run `python3 research/paper/scripts/analyze_paper.py` followed by `python3 research/paper/scripts/generate_results.py` from the repository. This re-derives metadata, duration, matched-pair and omission diagnostics from the pinned snapshot, and reuses the text-free `chunk-weighting.json` experiment. The saved experiment hash is checked against the source snapshot. Model inference is not repeated by this command.

## Optional inference replay

If the original locally retained caption corpus and pinned model files are available, run `python3 research/paper/scripts/analyze_paper.py --chunk-weighting --model-dir /path/to/model --corpus-file /path/to/corpus.json`. An optional `CHANNELING_ANALYSIS_VENDOR` directory can provide the same ONNX Runtime 1.23.2 and tokenizers 0.22.1 dependencies used in the original run. The script validates the model manifest and all model file hashes, validates each caption's text hash, and checks the equal-chunk replay against the published vectors before comparing pooling methods.

The corpus is not distributed here because it contains third-party caption text. This prevents independent raw-text replay from this release alone. Text-free video vectors, document IDs, chunk lengths, pairs and summaries permit downstream centroid and ranking verification. `chunk-weighted-embeddings.npz` stores the same 30 video IDs and equal-chunk/token-weighted 384-dimensional vectors.

## Experiment definition

The same name-and-genre-masked text is split into nonoverlapping chunks with at most 240 content WordPiece tokens, plus classification and separator tokens. Token-level attention-mask mean pooling and per-chunk L2 normalization are unchanged. The baseline takes the normalized mean of unit chunk vectors. The alternative takes their normalized weighted mean, with weight equal to content WordPiece count excluding special tokens. Both publisher centroids retain equal video weights. Thirty documents yield 320 chunks and 73,170 content WordPieces; only the 26 documents from 13 two-video publishers contribute to the 78 pair comparisons. Spearman ranks use the exported six-decimal cosines, as in the published comparison. No p-values or confidence intervals are computed.

The experiment changes only pooling weights; it does not evaluate ground-truth thematic similarity or separate hosts, promotions, audience questions and purported channeled speech.
