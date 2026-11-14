# Qualitative synthesis — non-Bashar self-run ASR pilot (acquisition-2026-11)

All statements below describe **self-run baseline ASR** of public YouTube
audio: provider label `self_run_faster_whisper_tiny.en`, sourceType
`public_youtube_audio_self_run_ASR`. Audio was acquired through the ordinary
public y2mate.gs paste-link interface (sha256-receipted `audio.mp3`) and
transcribed locally with the pinned Systran/faster-whisper-tiny.en model
(CPU int8, beam_size 1, VAD, condition_on_previous_text=false, contiguous
300 s decode windows covering 100% of each file). These transcripts are
**not rendered subtitles** and not original caption tracks; this layer is
independent of the provider-rendered subtitle workstream
(`research/expansion-2026/non-bashar-analysis`). There is **no diarization**,
**no human WER**, and **humanValidated=false** everywhere. Uploader,
practitioner and claimed entity are kept as three distinct metadata roles;
claimed-entity names are **publisher metadata** labels only — nothing here is
a claim about physical origins, entity reality, or cross-entity agreement.

## Corpus and validation

12 of 13 pilot videos are validated and included; **1 of 13** is excluded for
an unsupported language. The included corpus holds 4,190 ASR segments,
47,703 whitespace words and approximately 6.37 hours of audio, all detected
English. Every included record is hash-bound end to end: audio sha256 matches
across `acquisition.json`, `asr-receipt.json`, the acquisition ledger and
`asr-summary.json`; the three ASR output files recompute to the receipt's
`outputSha256`; decode windows demonstrably cover the full decoded duration;
ASR text coverage (last segment end / ffprobe duration) is >= 0.75 for every
included source.

- **Excluded — Pavlina Klemm (`-KVKPRLFte4`, unsupported language).** The
  audio is German. Forced through the English-only tiny.en, it yielded
  degenerate repetitive English at 20.8 words/minute over 63 minutes
  (repeated-trigram share 0.263) — versus 85–157 words/minute for the English
  sources — the recorded signature of an English-only model hallucinating on
  unsupported audio, not a usable transcript. The acquisition-side receipt
  records `excluded_language_mismatch` (detected `de`, expected `en`) and the
  ASR outputs are quarantined, hash-bound, under `quarantine/` and never
  analyzed. An English-only ASR layer cannot represent this source; excluding
  it is the faithful treatment.
- **Edition difference — Aurora Ray (`-8k6d9StYig`).** The prior
  provider-rendered subtitle edition of this video was detected Arabic, but
  the actual audio is English and the ASR text is fluent English
  (131.5 words/minute). The subtitle edition is not the audio language; the
  difference is disclosed as a non-fatal edition note.
- **Coverage notes (non-fatal).** `-leIq8XP15k` ASR text covers 0.924 of the
  audio duration (speech-free/music tail under VAD); `-o4q27DpxaA`'s final
  segment ends marginally past the nominal ffprobe duration (1.0000).
- **Repetition flag (non-fatal).** Christine Day (`-i0dfXWr9Vk`) shows an
  elevated repeated-trigram share (0.210) at a normal 113.5 words/minute;
  this is a slow, mantra-like delivery style and/or ASR repetition loops, and
  is flagged rather than excluded.
- **ASR fidelity caution.** tiny.en deforms names and terms (Yahyel appears
  as "Diyal"/"IELT"/"Yale", Ashtar as "Ashir"/"Ashdar", Val Nek as "Valek",
  Tartaria as "tatyara"). All counts below are literal-ASR-text counts, not
  corrected readings.

## Corpus analysis findings (diagnostics only)

- **TF-IDF** (unigram+bigram, Unicode tokens, stopword and proper-name
  masking) is strongly document-specific: snake/tree-of-life vocabulary for
  The Galactic Guide, eclipse/moon vocabulary for Aurora Ray, DNA/civilization
  vocabulary for both Ishuwa videos, "conscious breath"/"new blueprint" for
  Christine Day, "dear ones"/"love light" for Calenara, astrology vocabulary
  (capricorn/pluto) for Barbara Marciniak, "live streams"/"akashic" for Megan
  Rose, "card"/"toxic"/"ocean" for SOLi School, and panel/event vocabulary for
  the 2027-2030 channeling event.
- **NMF (k=6)** mostly separates individual documents or formats; mean
  best-match seed-stability cosine is 0.7867 across ten random-init runs.
  Repeatability of document-specific components is not evidence of stable
  semantic structure across the corpus.
- **KMeans diagnostics** (k=2..8) have near-zero silhouettes (maximum 0.0127):
  no defensible cluster structure; there is no evidence of natural clusters.
  All values are exploratory diagnostics on 12 short documents.
- **Document similarity network**: pairwise TF-IDF cosine is weak (mean
  0.0567, maximum 0.1089). The only threshold-level edge joins the two
  same-publisher Ishuwa/Yahyel videos (0.108) — same-source topical
  continuity, not cross-publisher convergence. Most below-threshold
  strongest-neighbor edges point at the long multi-speaker event video
  (`1XnCFCcbunc`), a size artifact of its broad vocabulary. All-zero nodes
  remain isolated; no zero-weight pseudo-edges exist.
- **Topic × claimed-entity heatmap** mirrors document/format separation. This
  compares publisher-attached labels only; it is not evidence that claimed
  entities agree, disagree, or form natural ontological groups.
- **Sensitivity**: maximum proper-name share is 0.41% per document and proper
  names are excluded from TF-IDF/NMF. Commercial-pattern hits are three in
  SAM THE ILLUSIONIST and one in Christine Day; the regex is English-oriented,
  not a cross-language detector.
- **Temporal/duration profiles**: question-rate per 10 minutes and per-third
  placement are reported per source in `analysis.json`; question density is a
  format property (interview/panel vs solo monologue), not an entity property.

## Literal Q&A findings (164 units, 216 question sentences)

- **Questions are format-dependent.** The multi-host panel event (40 units),
  Barbara Marciniak's interview (36), Calenara (22), The Galactic Guide (19)
  and Megan Rose's relay Q&A (16) carry most units; solo monologues carry few.
- **Automatic discourse classes**: 92 unclear_dialogue_context, 66 direct
  candidates, 5 rhetorical candidates, 1 secondary report.
- **AI review** (`ai_agent_review`, not human annotation): a stratified sample
  of **67 reviewed units** (>= 60) spanning every claimed-entity label, each
  verdict bound to the current question sha256 and source metadata. Verdicts:
  19 confirm, 34 reclassify, 14 boundary errors (21%). Quoted dialogue inside
  anecdotes and practitioner-relayed entity speech moved to secondary_report;
  audience-addressed teaching questions in solo monologues moved to
  rhetorical; several imperative/topical questions were promoted to direct on
  explicit textual evidence. tiny.en's multi-sentence segments make sentence
  splitting the main source of mid-clause cuts.
- **Question families** (types, not truth): other_theme 146, predictions 9,
  reality_agency 4, healing 3, contact_timing 1, ascension 1.
- **Answer orientation** is predominantly descriptive_explanatory (142), with
  conditional_hedged 14, process_practice_oriented 4 and timing_specific 4.
  Orientation describes captured text shape only; no answer truth, agreement
  or cross-entity consensus is assessed.
- **Common-question families**: 144 token-keyed families; 3 recur across
  videos and all three are generic-wording collisions on high-frequency
  content tokens ("what/do/now"-type wording), not substantive recycled
  questions. 16 stopword-only units (tag questions such as "right?", "You
  follow?", "Okay?") are family-less rows in the public registry and are
  excluded from family grouping so no spurious empty-key "common question" is
  created. `common-questions.csv` exposes the full registry.

## Key limitations (attach to every use of these numbers)

Self-run baseline ASR (faster-whisper tiny.en int8 CPU, English-only, 300 s
windows) over public YouTube audio; **not rendered subtitles** or original
caption tracks; ASR accuracy unmeasured (no human WER); no diarization or
speaker verification; **humanValidated=false**; AI review only; no human peer
review; 12 of 13 pilot videos (German-audio source excluded as unsupported by
the English-only model); small-corpus NMF/KMeans diagnostics; 300 s window
boundaries can split words; uploader != practitioner != claimed entity;
claimed-entity labels are publisher metadata; the Q&A layer records question
TYPES and answer ORIENTATION only — never answer agreement, truth, or
cross-ET consensus; literal `?` extraction misses reported-speech questions
without a question mark and inherits tiny.en's transcription errors verbatim.
