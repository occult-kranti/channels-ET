---
name: source-bound-channeling-knowledge
description: Extend the Channeling Atlas knowledge bank with source-bound question and claim cards while preserving editions, qualifiers and attribution limits.
---

# Source-bound knowledge maintenance

Use this workflow when extending `research/knowledge-bank/`. Read `CODEBOOK.md`,
`KNOWLEDGE-SCHEMA.md` and the current manifest before adding material.

1. Keep the source edition immutable. Recheck the original artifact's bytes/hash;
   compute the normalized body hash with `knowledge_sources.py`. Preserve the
   source URL, publication date, source-specific label and text/ASR format.
2. Record exactly what was read. Complete bodies and selected spans have distinct
   coverage; merge overlapping spans before counting unique inspected words.
3. Separate printed documentary question/response pairs from analyst comparison
   questions. ASR punctuation does not identify a questioner or assign a response.
4. Write a bounded paraphrase with conditions, timeframe, uncertain speaker role
   and qualifications. Bind each substantive part to source/character hashes and,
   where available, exact recognition turn/time locators.
5. Do not turn a source's claim into an accepted world fact. Energy, entity,
   religious identity, historical, health, financial and political assertions
   retain their source-attributed status.
6. Ask an independent role to inspect decisive supports. Apply substantive
   corrections in a fresh annotation edition with parent hash and correction log.
7. Run `knowledge_build.py` to a fresh private directory. Release only its exact
   public allowlist; preserve source bodies and evidence slices privately.

Completion requires executable hash/span/SQLite checks and source reading, not
the existence of a proposed schema. Human word-accuracy and annotation reliability
remain unmeasured unless actually evaluated. This workflow does not authorize
messages to outside people, credential exposure or automatic publication.
