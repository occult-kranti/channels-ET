#!/usr/bin/env python3
"""Bind proposed questions to the experiments actually executed in this edition."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


def build(args):
    inputs = {}
    bindings = {}
    for key in ('proposed', 'analysis', 'knowledge', 'retrieval', 'asr', 'full_asr', 'sensitivity', 'contextual_terms'):
        path = getattr(args, key)
        if path:
            raw = path.read_bytes(); inputs[key] = json.loads(raw)
            bindings[key] = {'file': path.name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    rows = inputs['proposed']['experiments']
    a, k, r, speech = (inputs[x] for x in ('analysis', 'knowledge', 'retrieval', 'asr'))
    retrieval_summary = {(s['model'], s['condition']): s for s in r['summary']}
    card_sources = {c['source_id'] for c in k['cards']}
    known_support_sources = {sid for q in r['queries'] for sid in q['known_relevant_source_ids']}
    outcomes = {
        'KB-H1-ASR': ('partially_executed', 'asr', [
            f"Executed {speech['summary']['paired_windows']} paired windows from {speech['summary']['recordings']} retained recordings ({speech['summary']['unique_audio_seconds']} audio seconds).",
            f"Parakeet outer stage {speech['upgraded_performance']['outer_stage_wall_seconds']:.2f}s; tiny baseline {speech['baseline_performance']['outer_stage_wall_seconds']:.2f}s, each with two workers.",
            f"Median symmetric token-edit disagreement {speech['summary']['median_symmetric_normalized_word_edit_distance']:.4f}; this is not a reference word-error rate.",
            'Runtime concurrency is measured; no matched serial-versus-parallel speedup experiment or human word-accuracy evaluation was performed.'
        ]),
        'KB-H2-RETRIEVAL': ('executed', 'retrieval', [
            f"Compared lexical and cached MiniLM representations over {a['totals']['selected_documents']} editions and {len(a['pairs'])} dependent document pairs.",
            'All four source-informed audit queries were frozen independently of card construction and before retrieval rankings; unlisted sources remain unjudged.',
            f"Raw-source MiniLM known-support reciprocal-rank mean is {retrieval_summary[('minilm','raw_source')]['mean_reciprocal_rank']:.4f} versus {retrieval_summary[('tfidf','raw_source')]['mean_reciprocal_rank']:.4f} for raw-source TF-IDF in this {len(r['queries'])}-query diagnostic; no general model ranking follows.",
            'Named-query versus paraphrase-query performance and human relevance accuracy remain unmeasured.'
        ]),
        'KB-H3-CONSOLIDATION': ('executed', 'retrieval', [
            f"Compared {r['coverage']['source_chunks']} raw chunks with {r['coverage']['cards']} curated cards covering {r['coverage']['card_sources']} of {r['coverage']['sources']} sources.",
            f"{len(known_support_sources & card_sources)} of {len(known_support_sources)} distinct known supporting sources have cards. Sources outside that subset cannot be recovered by the card-only index.",
            'Naive full-list rank fusion structurally favors every card-covered source. Its original result is retained alongside a disclosed post-hoc top5 candidate repair.',
            'The repair does not outperform the best raw-source baseline across both representations. Cards provide curated interpretation but do not automatically improve evidence retrieval.',
            'No neural weight distillation, synthetic-dream training or Google Sleep benchmark reproduction was executed.'
        ]),
        'KB-H4-SCOPE': ('executed', 'knowledge', [
            f"Created {k['coverage']['questions']} question records and {k['coverage']['cards']} source-linked cards, with {k['coverage']['comparisons']} scoped comparisons.",
            'Relations: ' + ', '.join(f"{name.replace('_', ' ')} {count}" for name, count in k['coverage']['relation_counts'].items()) + '.',
            'Zero scoped contradictions in this small selected set is not evidence of universal agreement. Similarity never assigns a comparison label.',
            'Human inter-annotator reliability, speaker verification and prediction-outcome verification remain unmeasured.'
        ]),
        'KB-H5-CONFOUNDING': ('executed', 'analysis', [
            'Executed exact-name masking, unmasked, centered-window and pooling sensitivities; compared within-medium and cross-medium label strata.',
            'Clusters have weak separation and seed sensitivity. Repeated names and similar language do not establish a shared entity or independent source.',
            'Five explicitly synthetic statements demonstrate that high embedding similarity can survive a negation; these controls are excluded from corpus denominators.'
        ]),
        'KB-H6-RETENTION': ('partially_executed', 'knowledge', [
            'Preserved earlier source editions, corrected card support locators in new annotation editions, and verified unchanged card-index text across the metadata correction.',
            'The primary model and all knowledge cards remain bound to their original body hashes. Recognition upgrades do not silently replace evidence.',
            'Repeated update cycles, automatic re-annotation and human evaluation of qualifier retention remain future work; this is not a test of neural catastrophic forgetting.'
        ]),
        'KB-H7-GRAPH': ('partially_executed', 'knowledge', [
            f"Built {len(k['graph']['nodes'])} typed nodes and {len(k['graph']['edges'])} provenance/attribution/question relationships with checked joins.",
            'The graph supports inspection and navigation. GraphRAG/HippoRAG retrieval algorithms and multi-hop retrieval gains were not implemented or evaluated.',
            'Attribution, source support, interpretation and hypotheses are distinct edge roles; graph density is not corroboration.'
        ]),
        'KB-H8-ANALOGY': ('proposed', 'literature', [
            'Recorded falsifiable connections to information retrieval, measurement error, oral history, argumentation, data versioning and contextual representation geometry.',
            'These are research hypotheses and design analogies, not evidence for physical mechanisms, claim truth or shared supernatural identity.'
        ])
    }
    for row in rows:
        status, module, observations = outcomes[row['id']]
        row.update(status=status, evidence_module=module, observations=observations,
            execution_scope='Bounded local operationalization; unexecuted components and external validity remain explicit.')
    if 'full_asr' in inputs:
        full = inputs['full_asr']['summary']
        next(x for x in rows if x['id'] == 'KB-H1-ASR')['observations'].append(
            f"Completed {full['recordings']} full-recording new editions across {full['chunks']} nonoverlapping chunks, covering {full['covered_audio_seconds'] / 60:.2f} minutes; original ASRs remain preserved.")
    if 'sensitivity' in inputs:
        next(x for x in rows if x['id'] == 'KB-H6-RETENTION')['observations'].append(
            'Executed a separate four-recording recognition-edition sensitivity and affected-card audit; new evidence is not automatically substituted into existing annotations.')
    if 'contextual_terms' in inputs:
        c = inputs['contextual_terms']['coverage']
        rows.append({'id': 'KB-H9-CONTEXTUAL-TERMS', 'title': 'Contextual token states across source usage',
            'status': 'executed', 'evidence_module': 'contextual_terms',
            'cross_field_connection': 'Contextual representation geometry and source-aware digital humanities',
            'hypothesis': 'The same selected term changes its contextual representation across sources; projections and clusters require explicit sampling and distortion diagnostics.',
            'observations': [f"Selected {c['terms']} terms from {c['eligible_terms']} eligible unigrams; {c['sampled_occurrences']} deterministic contexts from {c['available_occurrences']} available occurrences, spanning {c['source_term_pairs']} source-term pairs.",
                'Target subword states are balanced within source and then across sources. One term-centroid PCA also transforms source-context vectors.',
                'This uses token states from a sentence-trained MiniLM baseline. It is not a validated word-sense model, comprehensive vocabulary analysis or ontology of claimed beings.'],
            'limits': ['Context sampling is bounded and purposive.', 'Projection distances lose high-dimensional information.', 'No human word-sense judgments or generalization accuracy.'],
            'source_ids': ['sbert-2019', 'mmteb-2025']})
    result = {'schema_version': 1, 'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope': 'Execution ledger for exploratory, source-bound experiments; proposed, partial and completed components remain separate. No preregistration or human peer-review claim.',
        'input_bindings': bindings, 'experiments': rows,
        'decision': 'Retain raw evidence alongside curated cards, keep generation/recognition editions separate, and use similarity for navigation rather than automatic agreement or truth labels.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'experiments': len(rows), 'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('proposed', 'analysis', 'knowledge', 'retrieval', 'asr', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    for name in ('full-asr', 'sensitivity', 'contextual-terms'):
        p.add_argument('--' + name, type=Path)
    build(p.parse_args())
