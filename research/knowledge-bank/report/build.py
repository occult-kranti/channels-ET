#!/usr/bin/env python3
"""Build a source-bound supplement. Temporary TeX output stays in RAM."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
PINNED = {
    'analysis': 'e1407aa84f8eb33375f15647a5635daae0e75b55c365e7771e3ab0b728e818df',
    'retrieval': '0df6a4967ed08fd10aed7a11a9d43c3373c53660a352b66eaaa3121e15a946a4',
    'asr': '11a4242e924fa2509bfc11ef49337defab8d431ac885265913c77d31c48da5f7',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table(headers, rows):
    def cell(value):
        return str(value).replace('|', '/').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(map(cell, headers)) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(map(cell, row)) + ' |' for row in rows])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ['analysis', 'knowledge', 'retrieval', 'asr', 'literature']:
        ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--asr-full', type=Path)
    ap.add_argument('--asr-full-public', type=Path)
    ap.add_argument('--sensitivity', type=Path)
    ap.add_argument('--contextual-terms', type=Path)
    args = ap.parse_args()
    paths = {k: v for k, v in vars(args).items() if v is not None}
    data = {}
    bindings = {}
    for role, path in paths.items():
        digest = sha(path)
        if role in PINNED and digest != PINNED[role]:
            raise ValueError(f'{role} differs from the accepted release; review before updating the pin')
        data[role] = json.loads(path.read_text())
        bindings[role] = {'sha256': digest, 'bytes': path.stat().st_size}
    a, k, r, s, literature = [data[x] for x in ['analysis', 'knowledge', 'retrieval', 'asr', 'literature']]
    if a['totals']['selected_documents'] != 25 or len(r['queries']) != 4:
        raise ValueError('Unexpected frozen study denominator')
    if s['status'] != 'completed_paired_window_pilot':
        raise ValueError('The ASR pilot must be complete')
    if ('asr_full' in data) != ('sensitivity' in data):
        raise ValueError('Full-ASR and sensitivity inputs must be accepted together')
    if 'asr_full_public' in data and 'asr_full' not in data:
        raise ValueError('Public full-ASR metrics require the completed private manifest')
    if 'asr_full' in data:
        if data['asr_full']['status'] != 'completed_full_chunked_asr' or data['sensitivity']['status'] != 'executed_paired_edition_sensitivity':
            raise ValueError('Full-ASR inputs are incomplete')
        if data['sensitivity']['bindings']['new_manifest_sha256'] != bindings['asr_full']['sha256']:
            raise ValueError('Sensitivity does not bind to the supplied full ASR')
        if 'asr_full_public' in data and data['asr_full_public']['provenance']['private_manifest_sha256'] != bindings['asr_full']['sha256']:
            raise ValueError('Public full-ASR metrics bind to another manifest')
    if 'contextual_terms' in data:
        if data['contextual_terms']['status'] != 'executed_contextual_token_exploration' or data['contextual_terms']['bindings']['baseline_analysis_sha256'] != bindings['analysis']['sha256']:
            raise ValueError('Contextual-token exploration is incomplete or bound to another baseline')
    figures = []
    def figure(role, filename, caption):
        entry = next(x for x in data[role]['figures'] if x['file'] == filename)
        source = paths[role].parent / filename
        if sha(source) != entry['sha256'] or source.stat().st_size != entry['bytes']:
            raise ValueError(f'Figure binding failed: {filename}')
        figures.append((source, entry))
        return f'\n![{caption}](figures/{filename}){{width=100%}}\n'
    coverage = k['coverage']
    medium_rows=[]
    for medium in sorted({d['medium_name'] for d in a['documents']}):
        group=[d for d in a['documents'] if d['medium_name']==medium]
        medium_rows.append([medium,len(group),f"{sum(d['words'] for d in group):,}",sum(d['text_origin']=='machine_transcript' for d in group)])
    medium_table=table(['Medium attribution context','Editions','Words','Machine transcript editions'],medium_rows)
    pairnames = {
        'cross_medium_other_label': 'Different medium, different label',
        'cross_medium_same_comparison_label': 'Different medium, same comparison label',
        'same_medium_other_label': 'Same medium, different label',
        'same_medium_same_comparison_label': 'Same medium, same comparison label',
    }
    pairtable = table(['Pair stratum', 'Pairs', 'TF-IDF', 'MiniLM', 'Span TF-IDF', 'Span MiniLM'],
        [[pairnames[x['kind']], x['pairs']] + [f"{x[y]:.3f}" for y in ['lexical_cosine','semantic_cosine','window_lexical_cosine','window_semantic_cosine']] for x in a['pair_summary']])
    conditionnames = {'raw_source':'Raw chunks','answer_cards':'Answer cards','qualified_cards':'Qualified cards','hybrid_rrf':'Naive full-list RRF','hybrid_top5_rrf':'Top-5 RRF repair*'}
    retrievaltable = table(['Model / condition', 'MRR', 'Hit@1', 'Hit@3', 'Hit@5', 'Support coverage'],
        [[('TF-IDF' if x['model']=='tfidf' else 'MiniLM') + ' / ' + conditionnames[x['condition']],
          f"{x['mean_reciprocal_rank']:.3f}", *[f"{int(round(x['known_support_hit_rate'][str(z)]*4))}/4" for z in [1,3,5]],
          f"{int(round(x['known_support_index_coverage']*4))}/4"] for x in r['summary']])
    bas, new = s['baseline_performance'], s['upgraded_performance']
    asrtable = table(['Measured quantity', 'Whisper tiny.en', 'Parakeet 0.6b-v3'], [
        ['Concurrent workers / threads each','2 / 1','2 / 1'],
        ['Outer-stage wall time, seconds',f"{bas['outer_stage_wall_seconds']:.2f}",f"{new['outer_stage_wall_seconds']:.2f}"],
        ['Observed inference overlap, seconds',f"{bas['actual_inference_overlap_seconds']:.2f}",f"{new['actual_inference_overlap_seconds']:.2f}"],
        ['Median 30-second-window inference, seconds',f"{bas['median_window_inference_seconds']:.3f}",f"{new['median_window_inference_seconds']:.3f}"],
        ['Median per-window real-time factor',f"{bas['median_real_time_factor']:.4f}",f"{new['median_real_time_factor']:.4f}"],
        ['Recognized whitespace words',bas['recognized_whitespace_words'],new['recognized_whitespace_words']],
        ['Conservative ASR memory accounting, GiB',f"{bas['max_conservative_asr_memory_bytes']/2**30:.2f}",f"{new['max_conservative_asr_memory_bytes']/2**30:.2f}"],
    ])
    relations = table(['Annotation relation', 'Pairs'], [[key.replace('_',' '),value] for key,value in coverage['relation_counts'].items()])
    clusterrows=[]
    for key in ['lexical','semantic']:
        # Some releases name the neural branch semantically; inspect without guessing.
        branch=a['clusters'].get(key)
        if branch is None: continue
        runs=branch['runs']
        clusterrows.append([key.title(), *[f"{min(x[m] for x in runs):.3f}–{max(x[m] for x in runs):.3f}" for m in ['cosine_silhouette','medium_adjusted_rand','text_origin_adjusted_rand','comparison_label_adjusted_rand']]])
    if not clusterrows:
        raise ValueError('Missing cluster diagnostics')
    clustertable=table(['Representation','Silhouette','Medium ARI','Text-origin ARI','Comparison-label ARI'],clusterrows)
    refs=[]
    for i, record in enumerate(literature['records'],1):
        authors='; '.join(record['authors'])
        refs.append(f"**R{i}. {authors}.** {record['title']}. {record['version']}. "
                    f"Primary source: <{record['url']}>. Access depth: {record['access_depth'].replace('_',' ')}; "
                    f"retrieved {record['retrieved_at'][:10]}. "
                    + (' '.join(record['inspected_sections']) if record['access_depth']=='abstract_only' else 'Inspection details and source hashes are in the literature register.'))
    additional_path=HERE/'additional-references.json'
    additional=json.loads(additional_path.read_text())
    bindings['additional_references']={'sha256':sha(additional_path),'bytes':additional_path.stat().st_size}
    for i,record in enumerate(additional['records'],15):
        refs.append(f"**R{i}. {'; '.join(record['authors'])}.** {record['title']}. {record['version']}. "
                    f"Primary source: <{record['url']}>. Access depth: {record['access_depth']}; "
                    f"retrieved {record['retrieved_at'][:10]}. {record['application']}")
    t=a['totals']; sen=a['sensitivity']; ss=s['summary']
    report=f'''---
title: "Source-bound knowledge consolidation and recognition sensitivity in channeling discourse"
subtitle: "An additive, reproducible technical supplement to Channels ET"
author: "Maintainer/authorship: TBD — AI-assisted technical report"
date: "8 November 2026"
lang: en
documentclass: article
fontsize: 10pt
geometry: margin=24mm
colorlinks: true
toc: false
toc-depth: 2
header-includes:
  - \\usepackage{{microtype}}
  - \\usepackage{{float}}
  - \\usepackage{{xurl}}
  - \\floatplacement{{figure}}{{htbp}}
  - \\setlength{{\\emergencystretch}}{{3em}}
---

# Abstract

We examine how a small, source-bound knowledge bank changes when texts are represented lexically, embedded, consolidated into qualified answer cards, and transcribed by a different recognition pipeline. The frozen frame contains **{t['selected_documents']} distinct source editions, {t['words']:,} whitespace words and {t['mediums']} medium contexts**. Close reading covers {coverage['unique_body_words_read']:,} unique body words in {coverage['read_sources']} sources; it does not cover the entire modeled frame. The public bank contains {coverage['questions']} question labels, {coverage['cards']} answer cards and {coverage['comparisons']} scoped comparisons. A typed graph has {len(k['graph']['nodes'])} nodes and {len(k['graph']['edges'])} edges.

Lexical and neural neighborhoods agree only partially: mean top-five Jaccard is {sen['mean_neighbor_jaccard']:.3f}. Same-medium pairs are descriptively more similar than cross-medium pairs sharing a comparison label; format, editing and speaker context remain confounded. A four-query source-retrieval diagnostic exposes a mathematical coverage bias in naive full-list reciprocal-rank fusion (RRF). A separately labelled post-hoc repair does not establish a general retrieval winner. A paired eight-minute speech-recognition pilot runs NVIDIA Parakeet on two CPU workers and compares its output with Whisper tiny.en. Parakeet takes {new['outer_stage_wall_seconds']:.2f} seconds versus {bas['outer_stage_wall_seconds']:.2f}; disagreement is measured without treating either output as ground truth. This study updates no language-model weights and does not reproduce Google's Sleep training framework. It supports auditable navigation, source criticism and experiment design, rather than verification of the identities or events claimed in channeling discourse.

**Status.** This is an AI-assisted technical report, not a submitted or peer-reviewed paper. Maintainer authorship, institutional affiliations and human annotation validation remain TBD. Earlier corpora, papers and source editions remain unchanged.

\\clearpage
\\tableofcontents
\\clearpage

# 1. Questions and study boundaries

The immediate research questions are methodological. Do lexical and neural representations organize the same editions similarly? Does preserving the conditions of an answer improve useful retrieval, or merely increase index coverage and verbosity? Can two statements be compared without erasing their time, audience, referent or modal force? Does a larger contemporary speech-recognition model change downstream representations enough to require new annotation?

The unit of analysis is a **documentary source edition**, not an extraterrestrial civilization, a verified spiritual speaker, a unique audience member or a complete YouTube channel. A medium is a recorded presentation or attribution context. A comparison label is an analyst grouping of printed identities; broad civilization groups and named personalities occupy different conceptual levels. The frame contains {t['labels']} comparison labels and {t['exact_printed_labels']} exact printed labels. Neither shared wording nor a graph edge authenticates a claimed identity.

The 25-edition sample joins a previous 20-document written pilot with five Council-related texts. It is a purposive, accessible-source frame. It is not the separate, previously completed 228-unit publisher fit, a random sample of channeling, or an inventory of all videos. No new source media were acquired to assemble this particular frame. Existing retained audio was used for the recognition experiments. Duplicate checks removed no editions in this selection; this does not establish independence of their underlying ideas, publishing workflows or audiences.

# 2. Literature and the meaning of consolidation

## 2.1 The identifiable Google paper

The strongest match to the requested recent Google work is **Behrouz, Hashemi, Javanmard and Mirrokni, “Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories,” arXiv:2606.03979v2** [R1]. Version 1 appeared on 2 June 2026, version 2 on 10 July 2026; the metadata also notes an earlier OpenReview version from September 2025. Google's Research blog describes it on **27 October 2026** [R2]. The identification is source-grounded but remains a likely match because no paper link was supplied by the requester.

The authors' framework performs parameter updates. A fast wake memory operates alongside slower memory modules. It expands or activates low-rank mixture-of-experts memory while preserving older parameters, transfers information through generalized on-policy distillation and reinforcement-learning imitation, and resets fast modules after transfer. Its dreaming procedure activates random additional experts, produces synthetic curricula, selects examples using gradients, and trains adaptations. Cross-field connection in this setting is a proposed computational benefit of trained memory recombination; it is not evidence that two discourse traditions share an external referent.

The reported benchmarks require their original denominators. The ten-million-token BABILong result uses task-finetuned small models, and Appendix B.2 reports substantial degradation without that fine-tuning. The filtered ARC experiment uses 11 training tasks and eight held-out tasks, reporting successful-dream fractions from five dreams per test task. Mathematical results use the stated average-at-16 setting. Appendix B.5 reports same-step supervised fine-tuning as four times more efficient, while selected time-to-target comparisons have a different ordering. None of those values forecasts performance on this corpus or CPU environment. The inspected paper and blog did not establish an executable official author release; similarly named third-party repositories are not treated as reproductions.

Our implementation is an **external source-card and index consolidation experiment**. Sources remain immutable, cards are explicit annotations, and retrieval is measured separately. There are no trainable memory experts, imitation training, synthetic-gradient selection, new model weights, fine-tuning or biological sleep measurements. The analogy is limited to preparing a persistent, compressed, auditable representation before later queries.

## 2.2 Adjacent primary methods

Sleep-time Compute [R3] is a distinct Letta/UC Berkeley line of work about offline context preparation; it must not be attributed to Google. Nested Learning [R4] supplies architectural context for nested update frequencies, not proof that storing a card implements continual learning. GraphRAG [R5] motivates document-to-entity-to-community summaries for global questions. HippoRAG [R6] links passage retrieval, OpenIE and personalized PageRank; HippoRAG 2 [R7] broadens factual, associative and sensemaking retrieval. RAPTOR [R8] motivates hierarchical retrieval over summaries. These are design references; the present typed graph is not an executed GraphRAG, HippoRAG or RAPTOR benchmark.

MMTEB [R9] motivates task-specific, multilingual embedding evaluation rather than claiming a universally best encoder. Sentence-BERT [R10] supplies the foundational rationale for sentence-level similarity. The local encoder is a small, pinned MiniLM baseline, not a current universal state-of-the-art claim. Work on contradictions in text [R11] makes referent, scope and modality central: negation or cosine alone cannot decide contradiction. Whisper [R12] provides speech-recognition background, but the inspected abstract is not evidence for a specific observed error mechanism. Datasheets [R13] and W3C PROV-O [R14] motivate explicit collection, processing and agent provenance. The JSON records borrow that conceptual separation without claiming formal RDF conformance.

Access depth is recorded. HippoRAG 2, RAPTOR, Sentence-BERT, Whisper and Datasheets were inspected at abstract level in this literature pass. The report does not imply full-paper validation of their detailed methods. The literature register contains the exact versions, retrieval dates, inspected sections and source hashes for all 14 primary sources.

# 3. Data, provenance and annotation

## 3.1 Coverage is not a single denominator

{table(['Operation','Units actually covered'], [
    ['Representation analysis',f"{t['selected_documents']} editions / {t['words']:,} body words / {t['mediums']} medium contexts"],
    ['Close reading',f"{coverage['read_sources']} editions / {coverage['unique_body_words_read']:,} unique body words"],
    ['Complete retained source bodies read',coverage['read_full_bodies']],
    ['Additional documentary question text',f"{coverage['documentary_question_words_read']} words outside the body denominator"],
    ['Question bank',f"{coverage['analyst_questions']} analyst-authored + {coverage['documentary_questions']} paraphrased printed questions"],
    ['Knowledge cards and comparisons',f"{coverage['cards']} cards / {coverage['comparisons']} comparison records"],
    ['Typed graph',f"{len(k['graph']['nodes'])} nodes / {len(k['graph']['edges'])} edges"],
    ['Fixed retrieval diagnostic','4 source-informed questions; one known support per question'],
    ['Paired ASR pilot',f"{ss['paired_windows']} windows / {ss['recordings']} recordings / {ss['unique_audio_seconds']/60:.0f} unique audio minutes"],
])}

The frozen frame's medium-level distribution is:

{medium_table}

This table counts the retained documentary editions, not a medium's complete output. The source mix is uneven; the machine-transcript column also exposes a major text-origin confound. The five documentary question labels paraphrase printed questions attributed to the Lyssa Royal Holt/Sasha source; the other eight are analyst-written after reading their answers. They are navigation labels, not independently observed matching questions asked to multiple mediums. The analyst questions are excluded from the experimental card index. Automated full-text processing does not count as close reading. No human listening validation or human consensus annotation is claimed.

Source records retain edition identifiers, retrieval context, URL and cryptographic bindings. Normalized text locators use NFKC-normalized, stripped Python strings with end-exclusive character offsets. Source wording is retained privately; public artifacts expose bounded paraphrases, identifiers, evidence locators, summaries and plots. Existing Daniel attribution aliases are resolved to the same person where documented. Pamela Aaralyn and Pamela Rose Kribbe remain distinct. Recognition outputs retain unknown speaker roles where speaker identity is not established.

## 3.2 Cards preserve conditions

A card separates a question label, a concise answer, a scope or qualifier, and support locators. A relation compares propositions, not entities. The annotation record contains:

{relations}

Examples show why qualification matters. A source's advice to trust the Universe or Creator does not license the broader claim that every interpersonal relationship is safe. Comparing it with a boundary-setting passage yields a conditional tension only if an analyst expands the referent to draining relationships; it is not an explicit contradiction in the retained texts. Optional invocation of an Andromedan framing can coexist with a nonhierarchical Jeshua account. Voluntary recentering can coexist with rejection of a compulsory universal formula. A contact passage's near-term discussion concerns isolated contact and does not establish a definite start date for universal contact. These are bounded interpretive comparisons, not endorsements of the source claims.

Independent review corrected qualifiers and locators before acceptance. The graph contains typed source, annotation, question, topic and methodological-hypothesis links. Its printed-label nodes are medium-scoped: Mother Mary and Mary Magdalene each remain separate for Kribbe and Glasson. Consequently, 19 graph label nodes coexist with 17 distinct literal label strings in the analysis. Its 135 edges are not 135 independent corroborations, causal relationships or verified spiritual interactions. A node's degree partly reflects annotation choices and source coverage.

# 4. Representations, topics and source effects

## 4.1 Fixed processing contract

Complete exact medium-name and printed-label phrases are masked before the main similarity analysis. This reduces a direct name cue but leaves aliases, vocabulary, repeated introductions, editing practices and source format. TF-IDF uses unigram and bigram features, sublinear term frequency, smoothed inverse-document frequency, L2 normalization, minimum document frequency one and a 12,000-feature ceiling. Unicode letters and apostrophes define tokens; the stop list retains “no,” “not,” “nor” and “never.” Standalone numerals are not lexical features. Numerical claims therefore require a separate source-level audit.

The semantic encoder is `sentence-transformers/all-MiniLM-L6-v2`, pinned to revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, running through cached ONNX on one CPU thread. Documents are encoded as nonoverlapping 240-content-wordpiece chunks plus special tokens. Attention-mask mean pooling includes those special tokens, each chunk is L2 normalized, and the document mean is weighted by content-wordpiece count before final L2 normalization. All content chunks are processed; this is not head-only truncation. Equal-chunk weighting is a sensitivity condition.

A second condition uses a centered 300-analysis-token span selected before name masking. All 25 editions qualify. It reuses the full-corpus lexical vocabulary and IDF rather than refitting. This is a fixed-span control, not a random excerpt sample. Three NMF factors and three K-means clusters are fixed exploratory displays, not statistically selected doctrine counts. K-means uses ten initializations for seeds 11, 23 and 47.

## 4.2 Similarity is partly a source-context measurement

There are 300 unordered pairs, and pairs sharing an edition are dependent. Their descriptive means are:

{pairtable}

The same-medium/different-label MiniLM mean ({a['pair_summary'][2]['semantic_cosine']:.3f}) exceeds the cross-medium/same-label mean ({a['pair_summary'][1]['semantic_cosine']:.3f}). This is consistent with a source-context effect, but medium, date, editorial style, format, document length and topic selection are confounded. It does not show which medium is more authentic, that comparison labels are meaningless, or that authors deliberately copied one another. No inferential confidence intervals or p-values are assigned to these dependent pair summaries.

{figure('analysis','source-label-contrast.pdf','Dependent pair means by medium context and comparison label. The category denominators are displayed; the study does not treat 300 pairs as 300 independent observations.')}

{figure('analysis','representation-maps.pdf','Two lossy representations of the same 25 editions, with a portable source key. The maps support source navigation; distances and visual clusters do not validate doctrine or identity.')}

The lexical display is an uncentered two-component truncated SVD; the neural display is a centered two-component PCA. Their displayed explained-variance sums are approximately 6.30% and 26.52%, respectively. Trustworthiness at five neighbors is 0.801 and 0.845. Both coordinate systems are centered and scaled to unit root-mean-square radius; orthogonal Procrustes rotates or reflects the neural display only. The alignment RMS of 0.907 is not a latent-space equivalence metric. Axes are not assigned metaphysical meanings.

## 4.3 Stability and lexical overlays

Pair-rank Spearman between TF-IDF and MiniLM is {sen['pair_rank_spearman_lexical_vs_semantic']:.3f}. Mean top-five neighbor Jaccard is {sen['mean_neighbor_jaccard']:.3f}. Full-versus-span overlap is {sen['mean_lexical_window_jaccard']:.3f} for TF-IDF and {sen['mean_semantic_window_jaccard']:.3f} for MiniLM. Name masking produces higher neighbor stability ({sen['mean_name_mask_lexical_jaccard']:.3f} lexical; {sen['mean_name_mask_semantic_jaccard']:.3f} neural), but does not remove all source cues. Equal-versus-content-weighted pooling changes at least one pair cosine by as much as {sen['max_equal_vs_weighted_pair_change']:.3f}.

{figure('analysis','neighbor-stability.pdf','Per-edition top-five neighbor stability across representation, excerpt and masking choices. Set overlap measures modeling sensitivity, not answer correctness.')}

{clustertable}

The table shows ranges across the three fixed seeds. Low lexical silhouettes and changing adjusted Rand indices caution against naming clusters as stable civilizations or belief systems. Neural separation also aligns with text origin in some runs. The lexical overlay averages L2-normalized TF-IDF feature weights per medium with equal edition weights, selecting the union of each medium's top six observed features, capped at 30. It is an observed unigram/bigram overlay, not a neural word-vector map, a prevalence estimate or a unique vocabulary test.

A separate synthetic control compares five constructed statements outside the corpus. “Contact will happen this year” and its negated version have MiniLM cosine approximately 0.830, exceeding the approximately 0.542 score of the selected paraphrase. This small demonstration illustrates why cosine cannot certify agreement. It is not an accuracy benchmark or evidence that a corpus source contradicts another.

# 5. Source-card retrieval experiment

## 5.1 Design and denominators

Four source-informed audit queries were authored independently of the card author and frozen before that author saw them. They ask about a proposed council's initiators and timing, preparedness through sharing rather than hoarding, personal boundaries and external affirmation, and rapid change versus stable internal awareness. This is useful separation of roles, but the questions were still informed by source reading. They are not a human-blinded external held-out test.

The raw index contains 276 nonoverlapping 180-whitespace-word chunks covering all 47,280 words. Twenty-five cards cover 14 sources. Answer-only cards contain 573 words; qualified cards contain 1,458. Lexical vocabulary/IDF are fitted on raw source chunks only, and cards and queries are transformed without refitting. A source receives its maximum unit cosine, so document length and card multiplicity can affect its opportunity to score highly. The neural condition uses the same pinned MiniLM representation contract. The 13 navigation questions are not included in the indexed cards.

Each query has one documented known-support source. Other retrieved sources are **unjudged**, not automatically irrelevant. Known-support Hit@k asks whether that one known source appears among the first k sources. Reciprocal rank is zero if the source is missing and otherwise the inverse of its rank; MRR averages four such values. Coverage asks whether that support exists in an index at all. A 199-repetition source-ID shuffle is a descriptive negative control, not a p-value, sampling confidence interval or estimate of general task accuracy.

{retrievaltable}

*The top-five RRF repair is post-hoc. All fractions have four queries as the denominator. Cards cover only three of their four known support sources, imposing a 3/4 ceiling independently of ranking quality.*

{figure('retrieval','retrieval-audit.pdf','Known-support retrieval for four fixed source-informed queries. Naive full-list fusion is a diagnosed negative control; the top-five repair was added after the first run. Rankings outside the known support are unjudged.')}

## 5.2 A structural coverage bias in naive fusion

For a source appearing in a ranked list, reciprocal-rank fusion contributes $1/(60+r)$, where $r$ starts at one. In the naive condition, all 25 raw sources and all 14 card-covered sources contribute their full lists. Even the worst-positioned card-covered source receives

$$\\frac{{1}}{{60+25}}+\\frac{{1}}{{60+14}} \\approx 0.02528,$$

whereas the best raw-only source receives at most

$$\\frac{{1}}{{60+1}} \\approx 0.01639.$$

Thus **every card-covered source outranks every raw-only source by construction**, regardless of the query. This is a coverage artifact, not an empirical discovery that synthesis improves relevance. An independent critic derived the issue without viewing rankings, but the initial experiment had already run. The correction therefore remains explicitly post-hoc.

The repair fuses fixed top-five candidates from each list, then appends the raw-ranked tail to retain coverage. It does not tune k over the four queries or rewrite questions/cards. TF-IDF Hit@5 rises from 3/4 in naive fusion to 4/4 in the repair; MiniLM remains 3/4. Raw MiniLM itself reaches 4/4 at five with MRR 0.8125. These mixed, tiny-denominator results do not select a universal winner or prove that qualified cards improve retrieval. The operational lesson is to audit coverage and rank mechanics before interpreting an apparent consolidation gain.

# 6. Parallel speech-recognition pilot

## 6.1 Feasibility and actual performance

The candidate is NVIDIA `parakeet-tdt-0.6b-v3`, revision `541d1f99c6b0c3cd0b11a95167540bb8edefd82b`. Its safetensors artifact is 2,508,311,120 bytes; all downloaded model artifacts occupy approximately 2.509 GB temporarily in RAM. The counted floating-state elements are not presented as an independently verified architecture parameter count. The choice is a strong contemporary open-model candidate that runs in this environment, not a universal state-of-the-art finding. Its joint technical report [R16], inspected here at abstract and bibliographic level, announces Parakeet multilingual recognition across 25 languages. That abstract's 1.7-million-hour training and ten-times-faster-than-Whisper claims concern **Canary**, and are not transferred to this Parakeet run.

The pilot covers all four Council recordings plus four eligible recordings from other contexts under a fixed selection rule. Two nonoverlapping 30-second windows are centered near 25% and 75% of each recording, selected before recognition. Six source contexts contribute eight recordings and 16 paired windows: eight unique audio minutes and 32 model-window inferences. Both models receive the same canonical PCM samples. Two workers each use one CPU thread on a shared host with a four-core quota, 32 GiB memory limit and no available CUDA GPU.

{asrtable}

The observed overlap proves that workers actually ran concurrently. There is no matched serial execution on the same workload, so no parallel speedup claim is made. Outer-stage time includes load and orchestration; median real-time factor is a per-window measure. The Parakeet run is slower in this pilot, although it remains faster than real time per 30-second window. Shared host activity, runtime libraries, decoding and model architectures differ; these timings do not isolate a single cause or generalize to GPUs. Conservative memory accounting includes worker RSS and staged artifacts and can overcount shared pages.

## 6.2 Disagreement and timestamp triage

Symmetric normalized word-edit distance divides unit-cost token Levenshtein distance by the longer output token sequence. Its median is {ss['median_symmetric_normalized_word_edit_distance']:.4f} and mean {ss['mean_symmetric_normalized_word_edit_distance']:.4f}; median distinct-token Jaccard is {ss['median_token_set_jaccard']:.4f}. Two windows differ in negation-token counts and zero in numeric-token counts. These flags prioritize inspection; they do not establish semantic contradiction or numerical correctness. Neither output is an independent reference, so these metrics are **not word error rate (WER), accuracy or hallucination rate**.

The retained tiny.en segment output overruns the 30-second window endpoint in six segments across six windows, by at most one second. Raw timestamps are preserved rather than silently repaired. Parakeet here supplies window boundaries rather than comparable word-level alignment; the pilot cannot rank alignment accuracy. Repeated output, omitted speech, boundary artifacts and uncommon names require direct audio review before substantive claim comparison. No such human listening validation is claimed in this report.

A post-hoc repetition screen flags {ss['posthoc_baseline_token_run_ge10_windows']} baseline window and {ss['posthoc_upgraded_token_run_ge10_windows']} Parakeet windows at a threshold of at least ten identical consecutive tokens. In the flagged Ra window, the baseline's longest identical-token run contains 112 tokens. All 16 windows remain in the reported summaries. This is an output-quality triage flag; without independent listening it is not a confirmed hallucination, a diagnosis of the underlying audio, or proof that the other model's output is correct.

The eight-recording recognition pilot and the 25-edition representation frame are separate selections. For example, a pilot Ra window is not a Ra edition in the main 25-source knowledge bank. Results from one denominator must not silently be transferred to the other.

'''
    if 'contextual_terms' in data:
        ct=data['contextual_terms']; cc=ct['coverage']; cp=ct['projection']; cr=ct['clusters']['runs']
        term_positions={x['term']:i for i,x in enumerate(ct['terms'])}
        nearest_examples=', '.join(f"{left}/{right} ({ct['term_cosine_matrix'][term_positions[left]][term_positions[right]]:.3f})" for left,right in [('energy','energies'),('simply','just'),('not','no')])
        context_section=f'''## 4.4 Contextual target-token exploration

A separate add-on addresses literal word-vector overlays without relabelling document embeddings or TF-IDF weights as word embeddings. It selects {cc['terms']} unigrams from {cc['eligible_terms']} eligible candidates by mean fixed-baseline TF-IDF weight, with document frequency at least three and all components of exact medium and printed-label names excluded. The selection spans {cc['source_term_pairs']} source-term pairs in the same {cc['source_editions']} editions. Up to two deterministic ordinal occurrences per source and term yield {cc['sampled_occurrences']} sampled contexts out of {cc['available_occurrences']:,} available occurrences. A single occurrence is used when only one exists; the two-occurrence rule selects the first-third and second-third ordinal positions rather than optimizing visible separation.

For each occurrence, the same pinned MiniLM encoder processes up to 24 wordpieces on each side of the target. Final-layer hidden states for the target's own subwords are averaged and normalized. Occurrences are averaged equally within each source and normalized; source means are then averaged equally for each term and normalized. This limits domination by a source with many repeated occurrences, but medium coverage still differs by term. These are exploratory target-token states from a sentence-trained encoder, not validated word-sense embeddings. Foundational work on contextual representation geometry [R15] was inspected at abstract level; its BERT/ELMo/GPT-2 findings are not presented as measurements of this MiniLM add-on.

One PCA fitted to the {cc['terms']} term centroids transforms all {cc['source_term_pairs']} source-term means in the same coordinate system. The two displayed components explain {100*sum(cp['explained_variance']):.2f}% of centroid variance, with trustworthiness at {cp['trustworthiness_k']} neighbors of {cp['trustworthiness']:.4f}. The first four selected terms—{', '.join(cp['overlay_terms'])}—supply the fixed source-overlay panels. Axes are shared within this add-on only and are not aligned to the document maps. Fixed three-cluster silhouettes range from {min(x['cosine_silhouette'] for x in cr):.3f} to {max(x['cosine_silhouette'] for x in cr):.3f}; seed-pair adjusted Rand indices range from {min(x['value'] for x in ct['clusters']['seed_pair_adjusted_rand']):.3f} to {max(x['value'] for x in ct['clusters']['seed_pair_adjusted_rand']):.3f}. These are sensitivity diagnostics, not an estimated number of meanings or civilizations.

{figure('contextual_terms','contextual-token-overlay.pdf','Selected target-token centroids and source-context overlays in a shared PCA. Sentence-trained token states, two-occurrence sampling and fixed clusters are exploratory; proximity is not common-answer agreement or an ontology.')}

Frequent shared English vocabulary is overrepresented; sparse words, untranslated material and unsampled uses remain outside this view. High-cosine pairs include {nearest_examples}. Morphology and ordinary language usage are competing explanations for these neighborhoods, rather than evidence of a shared channeling teaching. Token states encode spelling, local context and source style as well as possible semantic associations. Nearness cannot establish a shared proposition, agreement, contradiction, or a verified speaker. Source character/token locators and their hashes are retained privately, with no corpus quotations in the public figure. The original document representations and TF-IDF term overlay remain unchanged.

'''
        report=report.replace('# 5. Source-card retrieval experiment\n',context_section+'# 5. Source-card retrieval experiment\n')
    if 'asr_full' not in data:
        report+='''# 7. Full-recording sensitivity: pending

At this report build, four full Council recordings are being processed as a separate run. The accepted report inputs do not yet include a completed full-recording manifest and its downstream sensitivity artifact. No completed full-audio minutes, new transcript word count or downstream result is claimed here. This chapter is populated only when both inputs pass status and hash-binding checks. Existing editions and cards remain unchanged meanwhile.

'''
    else:
        full, sens=data['asr_full'],data['sensitivity']; c=sens['coverage']; sm=sens['summary']
        empty_chunks=sum(chunk['words']==0 for doc in full['documents'] for chunk in doc['chunks'])
        full_performance=''
        if 'asr_full_public' in data:
            fp=data['asr_full_public']['performance']
            full_performance=(f"The measured two-worker stage takes {fp['stage_wall_seconds']/60:.2f} minutes, with one CPU thread per worker and "
                f"{fp['actual_inference_overlap_seconds']/60:.2f} minutes of observed inference overlap. Median chunk real-time factor is "
                f"{fp['median_chunk_real_time_factor']:.4f}; conservative memory accounting is {fp['max_conservative_asr_memory_bytes']/2**30:.2f} GiB. "
                "The stage includes hash checks, model loading and inference, and excludes download, preparation and final projection. "
                "It is a shared-host measurement without a matched serial speedup comparison.\n\n")
        report=report.replace('This study updates no language-model weights',
            f"A separate completed four-recording run covers {full['covered_audio_seconds']/60:.2f} audio minutes and yields {full['words']:,} recognized words; downstream sensitivity preserves older editions and requires re-reading affected cards. This study updates no language-model weights",1)
        report+=f'''# 7. Full-recording paired-edition sensitivity

The separately completed run covers **{full['recordings']} full recordings, {full['covered_audio_seconds']/60:.2f} audio minutes and {full['chunks']} contiguous nonoverlapping windows**, producing {full['words']:,} recognized whitespace words. Exact canonical 16 kHz mono sample bindings, start/end offsets and final partial tails are checked. Complete sample coverage does not establish complete or accurate linguistic recognition. Independent windows can split an utterance or lose discourse context; output is concatenated in sample order without inferred speaker identities or silently repaired wording. All {empty_chunks} empty-text chunks are retained as empty outcomes rather than omitted from coverage.

{full_performance}

For a controlled sensitivity analysis, four old recognition editions are counterfactually replaced within the 25-source frame; 21 editions remain unchanged. The published original fit is preserved. The new 25-source counterfactual has {c['counterfactual_words']:,} words versus {c['baseline_words']:,}; the paired subset changes from {c['old_paired_words']:,} to {c['new_paired_words']:,}. More words are not evidence of better recognition.

The lexical transform freezes the original phrase mask, vocabulary and IDF; new terms outside that vocabulary do not become new features. The semantic transform uses the same pinned MiniLM and complete chunk-pooling contract. This is a recognition-pipeline sensitivity analysis: model, context/VAD handling, segmentation, decoding and punctuation differ, so a change cannot be attributed solely to model weights.

{table(['Observed sensitivity','Value'],[
    ['Mean old/new paired TF-IDF cosine',f"{sm['mean_paired_lexical_cosine']:.4f}"],
    ['Mean old/new paired MiniLM cosine',f"{sm['mean_paired_semantic_cosine']:.4f}"],
    ['All-source mean top-five Jaccard, TF-IDF',f"{sm['mean_all_source_lexical_neighbor_jaccard']:.4f}"],
    ['All-source mean top-five Jaccard, MiniLM',f"{sm['mean_all_source_semantic_neighbor_jaccard']:.4f}"],
    ['Largest pair-cosine change, TF-IDF',f"{sm['max_lexical_pair_change']:.4f}"],
    ['Largest pair-cosine change, MiniLM',f"{sm['max_semantic_pair_change']:.4f}"],
    ['Existing cards requiring edition-specific re-reading',sens['card_reannotation']['affected_cards']],
    ['Cards automatically rewritten',sens['card_reannotation']['cards_rewritten']],
])}

{figure('sensitivity','asr-edition-sensitivity.pdf','Four same-audio pairs under old and new recognition pipelines. Word counts, representation cosines and normalized machine-text disagreement describe sensitivity; neither edition is ground truth.')}

All existing cards remain bound to their old source wording and locators. New editions require independent re-reading and re-annotation before inheriting any claim or relation. Similarity changes do not automatically alter a compatibility or contradiction label. Four deliberately selected Council recordings cannot establish performance across all channels, languages or recording conditions.

Independent model-agent review checked every retained input/output join and all 359 window-duration bindings. A separate scalar dynamic-programming implementation reproduced full token-edit distances of 104, 145, 108 and 1,602. An independent log-TF/IDF reconstruction reproduced the baseline and counterfactual lexical matrices; arithmetic on saved neural-vector witnesses reproduced paired cosines, matrices and neighbor summaries. These checks did not repeat neural-model inference, establish speaker identity, or supply a listening-verified reference. Detailed acceptance scopes are retained in the project's independent-review record.

'''
    report+='''# 8. Cross-field connections and falsifiable next experiments

The useful cross-field transfers are methodological, and each requires a stated failure condition.

**Information retrieval and archive coverage.** Card compression can change both relevance and opportunity to be retrieved. A larger preregistered query set should stratify supports that have and lack cards, hold query families out of tuning, report known-support coverage separately, and audit multiple plausible supports rather than treating all unlisted sources as irrelevant. A claimed gain fails if it disappears under equal source coverage or depends on repeatedly tuning fusion to the same questions. The present four-query diagnostic identifies a structural failure and supplies no population accuracy estimate.

**Oral history, discourse analysis and claim scope.** A statement's practical meaning depends on audience, speaker attribution, date, referent, condition and modality. A blinded annotation exercise can present source spans, qualified cards and answer-only cards to independent reviewers and count which obligatory qualifiers survive. The denominator should be prespecified qualifier obligations, with disagreement and unresolved cases retained. A compression method fails if it systematically turns possibilities into certainties or collective metaphors into dated factual predictions. Current cards are source-bound but have not undergone a human inter-annotator study.

**Stylometry and measurement theory.** Medium and text-origin signals can masquerade as civilization/topic similarity. A balanced future design should sample several matched questions per medium and label, preserve publication and editing metadata, and evaluate held-out medium or publisher conditions. A civilization-level interpretation weakens if separation vanishes after matching genre, length and topic or if medium prediction dominates. Current dependent-pair contrasts are descriptive; the available sample does not permit independent causal separation of those factors.

**Memory consolidation and regression testing.** Immutable sources, compressed cards and a retrieval index form three inspectable layers. Repeated updates can retain a fixed old-question set alongside newly introduced questions, reporting source support, qualifier retention, unsupported synthesis and index coverage after each update. A consolidation proposal fails if gains on new questions hide losses on old questions or erase provenance. This is an external-memory regression design, not evidence that a language model has acquired new parametric knowledge.

**Speech recognition and error propagation.** A future listening-verified reference should stratify quiet speech, noise, repetition, unfamiliar names, negation and numerical claims. Word-level accuracy, named-entity correctness and source-card stability should be assessed separately, using the same audio and explicit pipeline settings. Current machine-to-machine disagreement identifies review targets but cannot show which model is right. A higher-capacity model fails the substantive task if it produces fluent but unsupported names or reverses conditions even when its broad topic embedding remains similar.

**Network epistemology and graph semantics.** Typed provenance paths can distinguish “source supports card,” “analyst compares propositions” and “hypothesis connects methods.” A later graph-retrieval experiment can compare equal-budget lexical, neural and graph retrieval against documented supports. A graph method fails if apparent gains arise from duplicated source edges or label leakage. High degree and dense communities are not independent corroboration. GraphRAG and hippocampal-memory papers motivate tests, not shortcuts to evidential authority.

**Forecast auditing.** Date-bound prediction/outcome matching remains proposed. It requires the original publication timestamp, stable edition text, exact forecast scope, outcome criteria selected before outcome lookup, and listening verification where the decisive date comes from ASR. Retrospective thematic similarity is insufficient. The present study does not score prophecy, supernatural causation, health outcomes or future events.

# 9. Limitations, AI roles and reproducibility

This study is constrained by purposive source access, few mediums, uneven labels and topics, variable edition lengths and mixed text origins. Publisher text is not an independent word-aligned audio reference. Embeddings encode training-distribution biases; numerical claims and negation require direct examination. Lossy maps, selected lexical features and fixed cluster counts are exploratory. The pair observations are dependent. Four retrieval queries and four full-recognition source pairs cannot support general superiority claims. No new weight training, human-blinded accuracy study, verified channeled identity or causal spiritual mechanism is established.

AI agents performed literature inspection, source reading and bounded paraphrase annotation, representation design, code implementation, ASR orchestration, report writing and independent criticism in distinct roles. Independent model-agent review is not independent human replication or inter-annotator agreement. The source-reading and card roles were separated from the four audit-query authorship role before the card author saw the queries. An independent critic identified qualifier issues and the naive-fusion bias; the latter remained post-hoc because the first run already existed. Runtime and script/model/data hashes bind executed outputs. Maintainer authorship and human validation remain TBD.

The report is additive. Earlier source editions, numeric fits, papers and raw evidence are retained. Private full text and audio are excluded from the public source archive. Public materials contain the analysis code, literature register, bounded card paraphrases, question database, typed graph, figures, this report and release hashes. Access restrictions and source licences continue to apply to raw materials. The report source archive is self-contained for typesetting, not a redistribution of the research corpus or downloaded model weights.

To reproduce the PDF from the source archive, run `pdflatex -interaction=nonstopmode -halt-on-error main.tex` twice in a directory containing its `figures/` folder. To regenerate the report's selected numbers, run `build.py` with the accepted analysis, knowledge, retrieval, ASR and literature JSON inputs described in the accompanying README. Full-recording results require both a completed manifest and its hash-bound sensitivity artifact. Missing inputs produce an explicitly pending chapter, never inferred completion. The build verifies selected figure hashes and pins the main numerical and retrieval releases.

## 9.1 Input bindings

'''
    report+=table(['Accepted input role','SHA-256 prefix','Bytes'],[[name,entry['sha256'][:16],f"{entry['bytes']:,}"] for name,entry in bindings.items()])
    report+='\n\nFull SHA-256 values and output/figure bindings are in `manifest.json`. Prefixes above are display abbreviations, not alternate hashes.\n\n# References\n\n'+'\n\n'.join(refs)+'\n'
    HERE.mkdir(parents=True,exist_ok=True)
    (HERE/'figures').mkdir(exist_ok=True)
    for source, entry in figures:
        shutil.copy2(source,HERE/'figures'/entry['file'])
    (HERE/'report.md').write_text(report)
    readme='''# Source-bound knowledge-bank supplement

This additive AI-assisted technical report preserves earlier project papers. It is not peer reviewed or submitted. Authorship/maintainer and human validation: TBD.

`report.pdf` is the reading copy, `report.md` is the readable source, and `main.tex` plus `figures/` is the self-contained typesetting source. `source.zip` contains those sources, README and input bindings, but no raw corpus, audio, full transcripts, model weights or private paths. `manifest.json` binds accepted inputs and generated artifacts.

## Rebuild

```sh
python research/knowledge-bank/report/build.py \\
  --analysis ACCEPTED_ANALYSIS_JSON \\
  --knowledge ACCEPTED_KNOWLEDGE_JSON \\
  --retrieval ACCEPTED_RETRIEVAL_JSON \\
  --asr ACCEPTED_PAIRED_ASR_JSON \\
  --literature research/knowledge-bank/literature-register.json
```

Optional completed full-audio inputs must be supplied together: `--asr-full COMPLETED_MANIFEST_JSON --sensitivity ACCEPTED_SENSITIVITY_JSON`. The sensitivity binding must match the full manifest. Optional `--asr-full-public ACCEPTED_PUBLIC_FULL_ASR_JSON` adds runtime metrics only after verifying its binding to that same private manifest. Optional `--contextual-terms ACCEPTED_CONTEXTUAL_JSON` adds the separately scoped target-token exploration and its verified figure. Main analysis, retrieval and paired-ASR hashes are pinned to reviewed releases; changing those requires review and a deliberate pin update. Two abstract-level primary references are retained in `additional-references.json`, supplementing the original 14-record literature register.

Requirements: Python 3.10+, Pandoc, pdfLaTeX with standard LaTeX packages. Numerical models are not rerun by this report builder. It reads and verifies existing outputs. Temporary compilation goes to `/dev/shm`; durable report artifacts are capped at 5 MB. From an extracted source ZIP, run `pdflatex -interaction=nonstopmode -halt-on-error main.tex` twice. The PDF build is not claimed byte-reproducible because TeX timestamps/metadata can vary; figure and input numerical hashes remain explicit.

## Reading boundaries

Twenty-five source editions are modeled, fourteen are closely read, and four queries are a diagnostic. Naive RRF is a diagnosed coverage-bias condition; the top-five repair is post-hoc. ASR disagreement is not WER or accuracy. Source-card consolidation is external indexing, not Google's parameter-training Sleep algorithm. Full text and speech evidence remain in the private evidence archive.
'''
    (HERE/'README.md').write_text(readme)
    (HERE/'input-bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='knowledge-report-',dir='/dev/shm') as temp:
        tmp=Path(temp)
        shutil.copy2(HERE/'report.md',tmp/'report.md')
        shutil.copytree(HERE/'figures',tmp/'figures')
        subprocess.run(['pandoc','report.md','--standalone','--number-sections','-o','main.tex'],cwd=tmp,check=True,capture_output=True,text=True)
        # Headings already carry deliberate section numbers, so omit automatic numbering.
        tex=(tmp/'main.tex').read_text().replace('\\setcounter{secnumdepth}{5}','\\setcounter{secnumdepth}{-\\maxdimen}')
        tex=tex.replace('\\begin{figure}', '\\begin{figure}[p]')
        tex=re.sub(r'\\texttt\{([A-Za-z0-9/_.-]{30,})\}', lambda m: '\\nolinkurl{'+m.group(1)+'}', tex)
        (tmp/'main.tex').write_text(tex)
        for _ in range(2):
            completed=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=tmp,capture_output=True,text=True)
            if completed.returncode:
                raise RuntimeError(completed.stdout[-8000:])
        shutil.copy2(tmp/'main.tex',HERE/'main.tex')
        shutil.copy2(tmp/'main.pdf',HERE/'report.pdf')
        warnings=[line for line in (tmp/'main.log').read_text(errors='replace').splitlines() if 'Overfull' in line or 'undefined' in line]
    members=['README.md','main.tex','report.md','input-bindings.json','additional-references.json']+[str(Path('figures')/entry['file']) for _,entry in figures]
    with zipfile.ZipFile(HERE/'source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for member in members: archive.write(HERE/member,member)
    files=['report.pdf','source.zip','report.md','main.tex','README.md','input-bindings.json','additional-references.json','build.py']+[str(Path('figures')/entry['file']) for _,entry in figures]
    manifest={'schema_version':1,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'status':'completed_with_full_asr_sensitivity' if 'asr_full' in data else 'completed_report_full_asr_pending',
        'report_type':'AI-assisted technical supplement; not peer-reviewed or submitted; maintainer authorship TBD',
        'inputs':bindings,'artifacts':[{'file':name,'sha256':sha(HERE/name),'bytes':(HERE/name).stat().st_size} for name in files],
        'raw_corpus_included':False,'new_model_weights':False,'typesetting_warnings':warnings}
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    durable=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
    if durable>5_000_000: raise ValueError(f'Report budget exceeded: {durable}')
    print(json.dumps({'status':manifest['status'],'durable_bytes':durable,'pdf_bytes':(HERE/'report.pdf').stat().st_size,'figures':len(figures),'warnings':warnings}))


if __name__=='__main__':
    main()
