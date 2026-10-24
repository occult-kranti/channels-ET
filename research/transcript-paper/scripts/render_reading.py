"""Render only executed, source-bound AI-reading records; no raw source text."""
from collections import Counter


def render_reading(summary, documents, codes, qa, codebook, by_id, windows, families, findings, tex, table):
    docs = documents['documents']
    records = codes['records']
    candidates = qa['records']
    window_by_id = {row['windowId']: row for row in windows['windows']}
    assert len(docs) == len(records) == summary['documents'] == 36
    assert len(window_by_id) == summary['inspectedWindows'] == 105
    assert len(candidates) == summary['qaCandidateRecords'] == 37
    assert len(codebook['codes']) == summary['manualCodebookCodes'] == 10
    assert sum(len(row['codes']) for row in records) == summary['documentCodeAssignments']
    for row in docs:
        assert row['transcriptSha256'] == by_id[row['sourceId']]['transcriptSha256'], row['sourceId']
    for row in records:
        assert row['sourceTranscriptSha256'] == by_id[row['sourceId']]['transcriptSha256']
        assert row['humanValidated'] is False
        for support in row['support']:
            assert all(window_by_id[key]['sourceId'] == row['sourceId'] for key in support['windowIds'])
    for row in candidates:
        assert row['sourceTranscriptSha256'] == by_id[row['sourceId']]['transcriptSha256']
        assert row['supportTextSha256'] == window_by_id[row['supportWindowId']]['textSha256']
        assert row['humanValidated'] is False and row['exactQuotePublished'] is False
    kinds = Counter(row['candidateKind'] for row in candidates)
    assert dict(kinds) == summary['qaCandidateKinds']
    assert summary['uniqueAsrWordsRead'] / summary['asrWordsTotal'] == summary['asrWordCoverageFraction']
    assert summary['uniquePublisherTextWordsRead'] / summary['publisherTextWordsTotal'] == summary['publisherTextWordCoverageFraction']
    result = (f"The model agent inspected {summary['inspectedWindows']} windows: {summary['fixedSampleWindows']} fixed windows plus "
              f"{summary['inspectedWindows']-summary['fixedSampleWindows']} explicitly post-hoc or extended comparison windows. "
              f"The {summary['packetWordsRead']:,} packet words include overlapping windows and are not unique corpus coverage. "
              f"Deduplicated ASR coverage is {summary['uniqueAsrWordsRead']:,}/{summary['asrWordsTotal']:,} whitespace words "
              f"({summary['asrWordCoverageFraction']*100:.2f} percent), across {summary['uniqueAsrSegmentsRead']:,}/{summary['asrSegmentsTotal']:,} segments. "
              f"The written coverage is {summary['uniquePublisherTextWordsRead']:,}/{summary['publisherTextWordsTotal']:,} whitespace words "
              f"({summary['publisherTextWordCoverageFraction']*100:.2f} percent). "
              "Both reading fractions use the same whitespace rule, which differs from the common analytical tokenizer and inherited written-source receipt counts. "
              "The lone Athina transcript and Paul extraction were read completely as text, while the other audio records were sampled. "
              "This asymmetric reading depth is a limitation of qualitative context comparisons. Full computational use of a transcript is not full semantic reading.\n\n"
              f"Ten provisional codes yield {summary['documentCodeAssignments']} source--code assignments supported by inspected windows. "
              "The model-assisted publisher-promotion code occurs in selected windows of 15/20 audio records and 15/16 written records. "
              "Those selected-window source-presence counts are not a population advertising rate. They also differ from a narrow commercial-word dictionary: a source can promote a book or product without matching that dictionary.\n\n"
              f"The candidate database contains {len(candidates)} records in {summary['promptFamilies']} provisional prompt families. "
              f"Of these, {kinds['authored_comparison_prompt']} are analyst-constructed comparison prompts for written sources, "
              "not questions observed in an interaction. The 21 audio question-like candidates comprise 14 explicit interview-prompt candidates, "
              "one fragmentary interview prompt and six rhetorical, self-question or secondary-report candidates. "
              "They retain unsegmented question/answer turns and unknown speaker attribution. Shared family membership does not establish equivalent prompts or agreement.\n\n"
              "The readings provide competing interpretations for numerical resemblance. A skeptical Ross/Carrie passage uses belief/reality vocabulary to criticize the guidance, "
              "whereas an Align middle window contains a retail advertisement. A Gateways reply qualifies agency rather than presenting it as literally unconstrained. "
              "The full Athina ASR separates a creator introduction, a source-framed address and closing reflection, and discusses a staged life-purpose account. "
              "Its NMF words workers, jumps and sole are interpreted in that spiritual/ASR context; the last is a potential soul homophone, not a validated correction. "
              "These paraphrases are model-agent interpretations with retained locators, not verified speaker testimony or independent human coding.")
    result += '\n\nThe following six case comparisons describe the actual selected material. They are interpretive findings of this window-reading exercise; differences in prompts and source formats prevent population or agreement conclusions.\n\n'
    for finding in findings['records']:
        assert finding['humanValidated'] is False and finding['exactQuotesPublished'] is False
        anchors = []
        for key in finding['supportWindowIds']:
            window = window_by_id[key]
            short = by_id[window['sourceId']]['shortId']
            if 'startSeconds' in window:
                anchors.append(short + f" {window['startSeconds']:.2f}--{window['endSeconds']:.2f}s")
            else:
                anchors.append(short + ' ' + window['kind'].replace('_', ' '))
        result += '\\paragraph{' + tex(finding['label']) + '} ' + tex(finding['paraphrase']) + ' ' + tex('Support: ' + '; '.join(anchors) + '.') + '\n\n'
    details = table(['Candidate kind', 'Records'], [[key.replace('_', ' '), value] for key, value in sorted(kinds.items())],
                    'The 37 records are typed reading aids. Sixteen written comparison prompts are analyst constructions; the audio kinds include rhetorical and fragmentary cases.',
                    'p{0.72\\textwidth}r')
    family_rows = []
    for row in families['records']:
        family_rows.append([row['promptFamily'].replace('_', ' '), len(row['candidateIds']), len(row['sourceIds']),
                            row['modalityCounts'].get('audio_asr', 0), row['modalityCounts'].get('publisher_text', 0)])
    details += table(['Provisional family', 'Candidates', 'Source IDs', 'Audio', 'Written'], family_rows,
                     'AI analytic prompt families. Counts organize retrieval; they do not establish prompt equivalence, answer agreement or independent sources.',
                     'p{0.42\\textwidth}rrrr')
    chosen_ids = ['rss-988576741-1ecc5cb023cf', 'rss-425328515-addbc47ecbd7', 'rss-1529629262-6e621316510d', 'athina-ashtar-20230206-5d144c22']
    rows = []
    for source_id in chosen_ids:
        row = next(r for r in records if r['sourceId'] == source_id)
        support_ids = list(dict.fromkeys(w for s in row['support'] for w in s['windowIds']))
        selected = [window_by_id[k] for k in support_ids]
        complete = [w for w in windows['windows'] if w['sourceId'] == source_id and w['kind'] == 'full_ashtar_comparison']
        if complete:
            selected = complete
        anchor = '; '.join(f"{w['startSeconds']:.2f}--{w['endSeconds']:.2f}s" if 'startSeconds' in w else w['kind'].replace('_', ' ')
                           for w in selected)
        rows.append([by_id[source_id]['shortId'], anchor, row['synthesisParaphrase']])
    details += table(['Source ID', 'Supporting windows', 'Model-agent synthesis paraphrase'], rows,
                     'Selected source-linked interpretations, not raw quotations. Each source synthesis combines the listed inspected windows; the full-comparison locator is used for the complete Athina reading. Short IDs join the twenty-source table and sources.json; full window IDs/hashes remain in the reading artifacts. Voices remain unverified.',
                     'lp{0.18\\textwidth}p{0.61\\textwidth}')
    examples = [next(row for row in candidates if row['sourceId'] == key) for key in chosen_ids if any(row['sourceId'] == key for row in candidates)]
    details += table(['Source', 'Candidate type', 'Question and associated answer paraphrase'],
                     [[by_id[row['sourceId']]['shortId'], row['candidateKind'].replace('_', ' '),
                       row['questionParaphrase'] + ' / ' + row['answerParaphrase']] for row in examples],
                     'Illustrative typed Q&A records. Associated evidence can contain a partial adjacent response, rhetorical formulation or reported question; speaker identity and answer boundaries remain unvalidated.',
                     'lp{0.2\\textwidth}p{0.59\\textwidth}')
    details += table(['Provisional code', 'Audio sources', 'Written sources'],
                     [[row['label'], summary['codePresenceByModality']['audio_asr'].get(row['codeId'], 0),
                       summary['codePresenceByModality']['publisher_text'].get(row['codeId'], 0)] for row in codebook['codes']],
                     'Model-agent code presence aggregated from inspected windows. Denominators are 20 audio and 16 written documents, with different reading depths; values are not semantic accuracy or full-corpus theme prevalence.',
                     'p{0.61\\textwidth}rr')
    return result, details
