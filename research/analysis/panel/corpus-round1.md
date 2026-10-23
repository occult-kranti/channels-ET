# Caption corpus — round 1 evidence handoff

Actual package retrieval succeeded. This is an intentionally small and auditable pilot; it is not a complete transcript census.

## Observation and scope

{
  "selected": 36,
  "caption_success": 34,
  "caption_failures": [
    {
      "video_id": "OooAhzBX5T8",
      "person": "Megan Rose",
      "error": {
        "type": "TranscriptsDisabled",
        "message": "\nCould not retrieve a transcript for the video https://www.youtube.com/watch?v=OooAhzBX5T8! This is most likely caused by:\n\nSubtitles are disabled for this video\n\nIf you are sure that the described cause is not responsible for this error and that a transcript should be retrievable, please create an issue at https://github.com/jdepoix/youtube-transcript-api/issues. Please add which version of youtube_transcript_api you are using and provide the information needed to replicate the error. Also make sure that there are no open issues which already describe your problem!"
      }
    },
    {
      "video_id": "t_OYRnFXEHQ",
      "person": "Mônica de Medeiros",
      "error": {
        "type": "VideoUnplayable",
        "message": "\nCould not retrieve a transcript for the video https://www.youtube.com/watch?v=t_OYRnFXEHQ! This is most likely caused by:\n\nThe video is unplayable for the following reason: Join this channel to get access to members-only content like this video, and other exclusive perks.\n\nIf you are sure that the described cause is not responsible for this error and that a transcript should be retrievable, please create an issue at https://github.com/jdepoix/youtube-transcript-api/issues. Please add which version of youtube_transcript_api you are using and provide the information needed to replicate the error. Also make sure that there are no open issues which already describe your problem!"
      }
    }
  ],
  "languages": {
    "en": 29,
    "en-US": 2,
    "cs": 1,
    "ja": 2
  },
  "caption_types": {
    "automatic": 32,
    "manual": 2
  },
  "total_whitespace_words": 64683,
  "channels_selected": 18,
  "roles": "Publisher accounts sampled, not all speakers or proof of channeling. ZIP may assign a practitioner to a brand channel. Captions may include introductions, host speech, promotional material, music captions, and content unrelated to ET claims.",
  "selection": "First two supplied recent-video entries for each status-ok ZIP channel plus Darryl Anka and Athina Król, excluding donation/register/all-day-event titles; Aluna Ash had only one supplied entry. One extra Scranton text-concordance video kept separately.",
  "content_access": "YouTube caption text downloaded with youtube-transcript-api1.2.4. Not audio-listened or human-corrected. Public watch metadata independently fetched.",
  "rights": "Raw transcripts remain scratch-only; source manifests and derived metrics may be integrated. Do not publish fulltext or extensive quotations.",
  "repository_digest_corpus": "75 structured researcher digests in bashar-index data/videos.json; no transcript files found in207-entry pinned tree. Digest word_count/percentages/clusters are inherited and cannot substitute for direct transcript analysis."
}

## Skill applicability

- **opensync-audio-research** (read): transferable instructions applied are labelling inherited transcript digests, preserving provenance, keeping interpretation separate from measurement, and reviewing actual code/source outputs. Its brainwave_opensync repository, audio DSP, frequency presets, rendering and playback controls are inapplicable here.
- **gateway-evidence-audit** (read, including evidence-contract): transferable instructions applied are pinning source bytes/versions, distinguishing originals/captions/digests/pointers, preserving access failures, recording exact fields and units, and keeping documentary provenance separate from mechanism claims. Its Gateway archival corpus, waveform/EEG/force coupling and stimulus checks are inapplicable here.

## Round 1 objection → response → decision

1. **Objection:** Repository approximated word counts and summaries could be mistaken for transcripts. **Response:** Inspect all75record fields and207-entry pinned Git tree. **Decision:**75digests identified; no raw transcript paths. Kept out of direct-caption corpus.
2. **Objection:** A package capable of retrieving captions does not prove this environment can retrieve them. **Response:** Three concrete caption fetches succeeded, then the36-record pilot ran. **Decision:** Report actual success/failure denominators and package version.
3. **Objection:** Language preference failures are not absent captions. **Response:** Inspect offered languages for three NoTranscriptFound errors; request en-US and cs offered tracks. **Decision:** Retain initial failure provenance, mark corrected access successes; never claim captions were disabled on those three.
4. **Objection:** English-only sentence models are not comparable across Japanese/Czech original captions. **Response:** Expose track language and do not request automatic translation. **Decision:** English-only analysis must select en/en-US31docs, or use a multilingual model with validation; two Japanese and one Czech tracks remain separately documented.
5. **Objection:** Recent uploads include personal updates, teaching and promotional material. **Response:** Select first available items consistently rather than only ET-labelled titles, except explicit donation/event announcements. **Decision:** Describe channel-content similarity, not identity of claimed ET sources or a validity test.
6. **Objection:** Average length from30recentvideo samples could be presented as lifetime mean. **Response:** Root authorized union925public-watch metadata requests; all successes/failures logged and partial states retained. **Decision:** Any means are means of indexed videos with recovered durations, with denominators and coverage, never whole-channel means.

## Access ledger

- Direct public YouTube watch request: succeeded; actual publisher/video ID/duration/date available.
- YouTube via generic search open: DisabledError on pilotwatch, a route-specific failure; not used to infer total inaccessibility.
- L/LResearch Ra-session1 direct and web-open: HTTP403. No alternate circumvention attempted.
- Scranton Oct2026 official fulltext: accessible in normal requests and websearch. One linked video ID in ZIP used as extra concordance sample; only derived similarity/features may be exported.
- youtube-transcript-api documentation inspected at https://github.com/jdepoix/youtube-transcript-api. Package1.2.4 installed locally. No proxy, cookies, credentials or blocked-request evasion.

## Remaining work for later review rounds

Validate cohort sizes, languagefilter, identity binding, lengths, date handling, duplicates and captioncorpus hashes against final pipeline; independently inspect dashboard captions and sensitivity plots. Bulk metadata access still running at handoff; consume final metadata.json once present.
