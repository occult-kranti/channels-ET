# Source and storage distributions

These exports distinguish indexed YouTube uploads, selected IDs, actual retained
independent-publisher files, and the separately verified managed-cloud archive.
They are input tables for the new transcript dashboard and research paper.

`distributions.json` contains:

- `youtube`: 362 literal routes, publisher groups with indexed IDs, practitioner
  associations, raw entity labels and publisher-declared civilization labels.
  Every row counts distinct IDs within that group. Memberships overlap and must
  not be summed as worldwide unique channels, people, entities or videos.
- `sourceStorage`: actual source artifacts by publisher, practitioner context,
  source context and publication provider. Each of these four views partitions
  the same 99 source artifacts and bytes. Measured audio duration counts each
  recording once, without adding its three transcript outputs as new recordings.
- `localArchive`: the actual archive owner's source-bound state, once supplied.
  This distinguishes verified local copies from Drive uploads and from public
  Git/Pages assets. An absent state is unknown, never a claimed completed copy.
- `attributionCoverage`: explicit assigned and unassigned unique-ID coverage for
  every view, plus overlapping membership counts. Only 454 of 942 indexed IDs
  have a practitioner association; 642 have an entity label and 428 a declared
  civilization label. Publisher groups cover 886 IDs and routes cover 898. A
  missing association does not mean a recording lacks that identity or topic.

The current inherited frame has 942 unique YouTube IDs and 733 selected IDs.
There are zero observed completed YouTube video/caption files or bytes; RSS
recordings are never assigned to a YouTube account by similar titles. A nonzero
future collection deliberately stops this builder until actual artifact-level
IDs and sizes are joined. The independently published recordings comprise 19
Bashar-related interview/promotion/commentary editions and one Athina Król
creator episode with a publisher-attributed Ashtar context. Context labels do
not identify every audible speaker or establish an extraterrestrial source.

Duration columns include finite inherited lengths without unresolved conflicts;
unknown and conflicting counts remain separate. They describe upload time,
which may repeat older original sessions. Whole-channel lifetime counts remain
unknown. Publisher groups with indexed IDs differ from the broader discovery
inventory, whose groups can have no indexed uploads. Raw inherited civilization
labels are distinct from the new analysis's explicit lexical mention dictionary.

Rebuild from the repository root after the cloud archive owner reaches HOLD:

```sh
python3 research/storage-distributions/build_distributions.py \
  --archive-state research/cloud-archive/archive-state.json
```

The builder performs no network, media acquisition, transcription or inference.
It retains exact input hashes and CSV exports. Full recordings and transcripts
remain private outside Git. The local archive's retention depends on the managed
environment snapshot; it is not permanent chat-attachment or Drive storage.
