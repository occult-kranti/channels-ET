# Model panel — round 11 challenge and implementation

Reviewed round-10 archive SHA-256:
`5681c632f4b4f0fd857711d0d7ee2c6483bd39963cd2ff48c564d7710e7f2008`.
Role: AI implementation/research reviewer, not human peer review.

The original50 model responses and all primary five-arm metrics remain
unchanged. Their hashes are checked against the saved round-10 verification.
Changes below add actual experiments, counterexamples and portability checks.

| Finding | Revision / execution | Evidence |
|---|---|---|
| Strict underscore marker missed ordinary refusal wording | Add separately disclosed post-hoc refusal-phrase diagnostic; preserve original metric | Base closed-book says `Insufficient evidence.` on both controls, while strict marker count is0/2 |
| Answer reconstruction does not establish reliability | Retain the LoRA closed-book control's unsupported23°C studio claim | Exact raw output, prompt and evidence in `posthoc-diagnostics.json` |
| Heldout RAG often lacks useful evidence | Add two answer-present exact training-source query controls for each of base+RAG and LoRA+RAG | Four actual outputs;0/4 emit the requested source label; none enters heldout metrics |
| Local LLM use should analyze source material, not only reconstruct answers | Run12 fixed digest excerpt classifications from12 distinct source families | Nine JSON records parse; three fail; all nine parsed primary labels collapse to `contact_forecast` |
| Generated support spans can be invented | Check every parsed model span against the exact answer gist and an eight-word maximum | Zero valid spans among nine parsed records; all failures retained |
| Dictionary concordance is not annotation accuracy | Compare conditional wording labels to inherited regex indicators |5/9 parsed-label concordance; balanced purposive selection and no human labels |
| A broad dictionary pattern can misfire | Identify `depend\w*` matching `dependency` without a logical condition | Retained as a codebook limitation, not silently corrected in the old release |
| Small old baseline does not establish current-family feasibility | Actually load and run official Qwen3.5-0.8B text-only on CPU in a separate environment | Verified1,746,942,600-byte weights;23 generated tokens in3.881313s, valid requested provenance JSON |
| Adapter provenance was insufficient for reuse | Add48 source hash/pointer entries, QA/split/protocol hashes and separate license NOTICE to actual adapter ZIP | New ZIP SHA19bd5b720446af07603390e276baebfb0010fb4df7971199262cae64fd7adb0c |
| Frozen-source checks should not require external weights | Add source-only `--offline` verification and portable adapter ZIP hashes |280 checks pass with tokenizer audit explicitly skipped;327 current-cache checks pass with48 exact tokenization checks |

The content-label task uses existing AI-generated digests only. It does not
validate original transcripts, human questions, actual speakers, claimed
entities or the truth of asserted mechanisms. All nine parsed primary-theme
outputs choosing the same first option is a model/prompt failure signal, not a
claim that all source texts concern contact. A future option-order sensitivity
is planned separately; it was not run in this round.

The Qwen3.5 smoke test uses revision
`2fc06364715b967f1860aea9cf38778875588b17`, Apache-2.0, Transformers5.20.2,
Torch2.6.0+cpu, float32 and two threads. Its image-text architecture received
**text only**. Reference PyTorch implementations were used because optional
optimized causal-convolution/linear-attention kernels are absent. Peak process
RSS was5,593,472KiB. The single prompt explicitly supplied the provenance facts
it asked the model to encode. It demonstrates local runtime/schema feasibility,
not unseen-content accuracy or a state-of-the-art ranking. No GPU or newer-model
fine-tuning experiment was performed.

`round11-verification.json` records102 source/bookkeeping checks. Initial
round-10 tokenization evidence remains in `full-verification-round10.json`;
current full and offline receipts distinguish what was recomputed from retained
history. Generation-cap flags are a censoring audit, not an executed longer-token
budget experiment. Removing source-label tokens is a post-hoc overlap sensitivity,
with the original scores retained.
