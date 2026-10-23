#!/usr/bin/env python3
"""Generate expansion-paper values from executed, source-addressable outputs."""
import hashlib
import json
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parents[1]
EXP = HERE.parent
ATLAS = EXP.parents[1]
OUT = HERE / 'generated'
OUT.mkdir(exist_ok=True)

def read(p):
    return json.loads(p.read_text())

def esc(value):
    value = str(value).replace('–', '--').replace('—', '---').replace('≥', '$\\geq$').replace('≤', '$\\leq$')
    mapping = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    # Character-wise replacement avoids escaping inserted commands twice.
    return ''.join(mapping.get(c, c) for c in value)

def table(headers, rows, widths, caption):
    spec = ''.join('p{' + str(w) + r'\textwidth}' for w in widths)
    body = '\n'.join(' & '.join(esc(x) for x in row) + r' \\' for row in rows)
    return '\n'.join([r'\begin{table}[htbp]', r'\small\centering',r'\setlength{\tabcolsep}{4pt}', '\\begin{tabular}{'+spec+'}',r'\toprule',' & '.join(headers)+r' \\ \midrule',body,r'\bottomrule',r'\end{tabular}','\\caption{'+caption+'}',r'\end{table}',''])

a = read(EXP / 'analysis/results.json')
q = read(EXP / 'qa/summary.json')
c = read(EXP / 'acquisition/acquisition-summary.json')
base = read(ATLAS / 'dist/analysis/data.json')
cov = {r['measure']:r for r in a['coverage']['missingness']}
values = {
    'UploadN': a['coverage']['uploads'],
    'DurationN': cov['Positive upload duration']['available'],
    'DateN': cov['Exact upload date']['available'],
    'TitleN': cov['English-likely eligible title']['available'],
    'QAN':q['coverage']['qaCandidates'],
    'QAVideoN':q['coverage']['videosWithQACandidates'],
}
(OUT / 'values.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+str(v)+'}' for k,v in values.items())+'\n')
rows = [[r['measure'], r['available'], r['total'], f"{100*r['availableShare']:.1f}%"] for r in a['coverage']['missingness']]
(OUT/'coverage-table.tex').write_text(table(['Measurement layer','Available','Indexed pool','Share'],rows,[.43,.13,.14,.14], 'Inherited snapshot coverage. The caption row is selected pilot inclusion, not estimated caption availability. Denominators describe known uploads.'))

text = []
add = text.append
def section(s):add('\\subsection{'+s+'}')
def fig(stem,caption):
    source=EXP/'analysis/generated/figures'/f'{stem}.pdf'
    dest=OUT/'figures'/source.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(source,dest)
    add('\\begin{figure}[p]\n\\centering\n\\includegraphics[width=\\textwidth]{generated/figures/'+source.name+'}\n\\caption{'+caption+'}\n\\label{fig:'+stem+'}\n\\end{figure}')

section('Implemented collection and observed access')
u=c['units']
add(f"The new plan contains {u['practitioner_candidates']} inherited practitioner/lineage/partial-name candidates, {u['keyword_queries']} planned keyword queries, {u['account_routes']} planned account crawls and {u['caption_candidates']} proposed caption candidates, alongside {u['historical_upload_ids']} retained upload IDs. These are different units and are not additive. The recorded initial preflight attempted {c['recorded_preflight_attempts']} ordinary watch request and observed {c['recorded_blocks']} policy block; newly successful collection operations total {c['new_successful_operations']}. Therefore no new search results, channel histories, metadata records or captions are added by this collection phase.")
add('The installed collector dependencies are \\texttt{yt-dlp '+esc(c['software']['yt-dlp'])+'} and \\texttt{youtube-transcript-api '+esc(c['software']['youtube-transcript-api'])+'}. The observed watch preflight used Python standard-library \\texttt{urllib}; no successful tool-backed crawl or caption retrieval occurred. Package import and dependency checks establish local availability, while mocked safety tests establish selected control behavior; neither is successful platform retrieval. The documented query forms are quoted practitioner name with \\emph{channeling}, \\emph{questions answers}, or \\emph{interview}, plus documented name/entity combinations. Other spelling variants are proposed sensitivity checks.')

section('Coverage and publisher concentration')
co=a['concentration']
add(f"Of {a['coverage']['uploads']} retained uploads, {co['attributedUploads']} resolve to {co['accountGroupsWithUploads']} nonempty publisher groups, while {co['unattributedUploads']} remain unresolved. The largest ten groups contribute {100*co['top10Share']:.2f}\\% of attributed uploads; the largest twenty contribute {100*co['top20Share']:.2f}\\%. Thus the exploratory direction check that the largest ten exceed half is disconfirmed in this sample. These checks were recorded after inspection of the schema and prior summaries, before the new computations; they are not preregistered. The upload-count Gini is {co['gini']:.3f}; inverse-Herfindahl effective representation is {co['effectiveEquallyRepresentedAccounts']:.2f} equally sized groups. These are sample concentration measures, not audience or practitioner statistics.")
fig('coverage','Availability of retained measurement layers. The selected caption-pilot row is inclusion in this released pilot, not a census of offered-caption availability. Missing observations are not negative content findings.')
fig('concentration','Publishing-account concentration among attributed retained uploads. Ranks and cumulative shares describe sample composition. They do not measure followers, views, influence or unique human practitioners.')

section('Caption selection does not favor longer recordings in this snapshot')
s=a['captionSelection'];p=s['captionPilotKnownDuration'];o=s['otherIndexedKnownDuration'];w=s['otherUploadsInPilotAccountsKnownDuration']
add(f"The {p['n']} English pilot uploads have median observed length {p['median']:.2f} minutes, compared with {o['median']:.2f} minutes in the other {o['n']} indexed uploads with known duration. Restricting the comparison to the pilot's {s['pilotAccounts']} publisher groups gives median {w['median']:.2f} minutes among {w['n']} other known-duration uploads. The pilot therefore does not have a larger median in either descriptive contrast. This disconfirms the proposed longer-pilot direction, but it is not an estimate of how duration causes caption availability: the pilot selection was purposive and its failures were limited.")
fig('caption-selection','Observed duration distributions for the English caption pilot, other indexed uploads, and other uploads from pilot publishers. Quartile spans describe observed records; they are not confidence intervals or corrected population estimates.')

section('Length and title-keyword framing depend on aggregation')
k=a['keywordContrasts'];den=k[0]
add(f"The title/duration diagnostic uses {den['shortTitles']+den['longTitles']} eligible titles with measured duration: {den['shortTitles']} uploads shorter than thirty minutes and {den['longTitles']} of at least thirty minutes. Only {den['eligiblePairedAccounts']} accounts meet the paired-account rule on both sides. The pooled direction agrees with the paired-account median direction in two of nine dictionary families. Six paired medians are exactly zero; they must not be described as six reversed effects.")
soc=next(x for x in k if x['topicId']=='society')
add(f"The society/world-events family illustrates an actual sign change: its pooled long-minus-short presence contrast is {100*soc['pooledLongMinusShortShare']:+.2f} percentage points, whereas the median paired-account contrast is {100*soc['accountDifferenceSummary']['median']:+.2f} points. The compared pools and weighting differ; this is evidence to inspect composition, not a causal duration effect or a full Simpson-paradox identification.")
add(table(['Dictionary family','Pooled long--short, pp','Median account contrast, pp','Groups'],[[x['topic'],f"{100*x['pooledLongMinusShortShare']:+.2f}",f"{100*x['accountDifferenceSummary']['median']:+.2f}",x['eligiblePairedAccounts']] for x in k],[.39,.19,.22,.08], 'Duration contrast among eligible titles. Families overlap. Per-account estimates use the separately eligible paired-account subset; a zero median is not a directional reversal.'))
fig('keyword-duration','Title dictionary presence by observed upload-duration band. Cell denominators are eligible titled uploads with measured duration. Keywords indicate visible framing, not time spent on a theme or validated spoken content.')

section('Publisher resemblance remains a descriptive property of text')
e=a['embeddingWithinBetween'];mc=e['matchedCaption'];mt=e['matchedTitle']
add(f"The new upload-pair diagnostic intersects the existing title and caption derivatives, yielding {mc['documents']} uploads from {mc['publishers']} publishers. This includes groups that do not meet the older two-document account-centroid threshold, so it differs from the prior 22-video/eleven-account centroid comparison. Both new text-layer diagnostics use the same {mc['documents']} uploads. The mean same-publisher minus different-publisher cosine is {mc['meanDifference']:.3f} for captions and {mt['meanDifference']:.3f} for titles. The scores describe resemblance under fixed representations, not the probability of shared authorship, an attributed entity or answer agreement.")
add(f"There are {mc['within']['n']} same-publisher and {mc['between']['n']} different-publisher upload pairs; {mc['publishersWithWithinPairs']} accounts have a within-account pair and {mc['singletonPublishers']} accounts are singletons. An equal-account sensitivity gives separation {mc['accountBalanced']['meanDifference']:.3f} for captions and {mt['accountBalanced']['meanDifference']:.3f} for titles across {mc['accountBalanced']['eligiblePublishers']} eligible focal publishers. Omitting each publisher in turn gives caption separation {mc['leaveOnePublisherOut']['summary']['min']:.3f}--{mc['leaveOnePublisherOut']['summary']['max']:.3f} and title separation {mt['leaveOnePublisherOut']['summary']['min']:.3f}--{mt['leaveOnePublisherOut']['summary']['max']:.3f}. These deterministic influence ranges are not confidence intervals.")
add(f"Caption minus title pooled separation is {e['crossLayerContrast']['captionMinusTitlePooledMeanDifference']:+.3f}; its equal-account analogue is {e['crossLayerContrast']['captionMinusTitleAccountBalancedDifference']:+.3f}. Cosine scales are representation-specific, so the difference is a descriptive sensitivity rather than a calibrated amount of semantic or practitioner signal.")
add('The label-shuffle reference permutes publisher labels on the fixed vectors while preserving group sizes (2,000 seed-42 permutations). It is a descriptive negative control, not a population p-value or independent-pair confidence interval. Unresolved original-session reuse, account boilerplate, hosts and publisher formatting remain explanations for a within-publisher advantage. A failure to resemble arbitrary shuffled labels does not isolate a practitioner mechanism.')
fig('publisher-similarity','Same- versus different-publisher cosine summaries on fixed title and caption derivatives. Pair entries reuse uploads and are dependent. The new matched upload pool differs from the earlier thresholded centroid cohort.')
fig('negative-control','Fixed-vector publisher-label shuffle reference. Labels are permuted with group sizes preserved. The distribution is a descriptive diagnostic, not a population null distribution, a calibrated p-value or evidence about communication origin.')

section('Repeated title strings are not original-session families')
d=a['duplicateTitles']['variants']['normalized'];old=a['duplicateTitles']
add(f"The new explicitly normalized eligible-title audit finds {d['repeatedStringFamilies']} repeated-string families involving {d['documentsInRepeatedFamilies']} documents among {d['nonemptyEligibleTitleDocuments']} eligible titles; none spans different resolved publishers. Its normalization is different from the inherited embedding-deduplication pipeline. The inherited pipeline's pair-order correlation after its own exclusion rule is {old['publishedEmbeddingDeduplication']['spearmanRankCorrelation']:.3f}, while raw versus name/genre-masked title rankings correlate at {old['publishedMaskSensitivity']['spearmanRankCorrelation']:.3f}. These are distinct operations and counts. Neither audit establishes that differently titled uploads are different original performances.")

section('Question-answer candidates: useful retrieval, one practitioner context')
qc=q['coverage']
add(f"The database indexes all {qc['qaCandidates']} retained question/answer-gist entries from {qc['videosWithQACandidates']} Q\\&A-bearing digests among {qc['digestVideos']} source digests. All belong to one Darryl Anka-related practitioner context. They span {qc['publishingAccountsWithQA']} resolved publisher IDs; {qc['candidatesWithoutResolvedPublisherId']} candidates lack a resolved publisher ID and remain in {qc['unresolvedPublisherNameGroups']} inherited-name groups. There are {qc['literalTranscriptTurns']} literal transcript turns, {qc['speakerVerifiedCandidates']} verified answer-speaker candidates, and {qc['humanReviewedCandidates']} human-reviewed candidates in this layer. The other inherited practitioner candidates do not acquire Q\\&A rows merely because they appear in the discovery frame.")
add(table(['Source-digest format',r'Q\&A-bearing uploads','Candidates'],[[x['format'],x['videos'],x['qaCandidates']] for x in q['formats']],[.48,.23,.15], 'Inherited digest format labels among Q\\&A-bearing uploads. Labels are retained source metadata, not a newly validated format taxonomy or answer-speaker annotation.'))
add(table([r'Q\&A dictionary family','Question matches','Answer-gist matches'],[[x['label'],x['questionCount'],x['answerCount']] for x in q['themes']],[.49,.18,.2], 'Overlapping keyword matches in question paraphrases and answer gists. Both columns use 949 candidates but different text fields and lengths. Counts are neither validated themes nor measures of agreement.'))
add(f"There are {qc['distinctNormalizedQuestions']} unique normalized question strings and {qc['repeatedNormalizedQuestions']} repeated-string groups. Across distinct uploads, {qc['questionSimilarityPairsAt040']} question pairs meet the lexical cosine threshold of 0.40. Excluding identical normalized question wording leaves {q['sensitivity']['similarQuestionPairsExcludingIdenticalQuestionWording']['retainedPairs']} pairs. These are candidate retrievals, not independent question occurrences or evidence that separate original sessions answered the same prompt.")
thresholds=q['sensitivity']['retrievalThresholds'];con=q['sensitivity']['uploadPairConcentration']
add(f"The retrieval count is sensitive to its exploratory cutoff: increasing question cosine from 0.40 to 0.90 reduces candidate pairs from {thresholds[0]['candidatePairs']} to {thresholds[-1]['candidatePairs']}. At 0.40, the {con['totalQuestionPairs']} candidate matches occupy {con['distinctUploadPairs']} distinct upload pairs; the three leading upload pairs supply {con['topThreeUploadPairCandidateMatches']} matches ({100*con['topThreeUploadPairShare']:.1f}\\%). Concentration can reflect shared questions, reused original material or summary normalization. It is not an observed repost rate or an independent-session count.")
add(table(['Minimum question cosine','Candidate question pairs','Distinct upload pairs'],[[f"{x['minimumQuestionCosine']:.2f}",x['candidatePairs'],x['distinctUploadPairs']] for x in thresholds],[.31,.29,.27], 'Exploratory lexical retrieval sensitivity. These thresholds recount the retained question candidates and are not validated equivalence cutoffs. Distinct upload pairs can still share an original performance.'))
add(f"The summary preview displays {len(q['questionPairs'])} of the {qc['questionSimilarityPairsAt040']} retained pairs; the complete records are in \\texttt{{question-pairs.json}} and SQLite. Preview truncation is not a lower analyzed denominator. CSV verification/speaker fields retain explicit false values rather than blank strings; null timestamps still mean that no precise turn time is available.")
pair=q['questionPairs'][0]
add('One retrieved pair repeats the digest question '+r'\emph{'+esc(pair['leftQuestion'])+'} across two uploads. Its question cosine is '+f"{pair['questionCosine']:.3f}"+' but its answer-gist cosine is '+f"{pair['answerCosine']:.3f}"+'. The source relation is unresolved: this could involve distinct explanations, summary wording or shared original material. The database correctly marks answer agreement as not assessed rather than converting either score into an agreement verdict.')
add('Twenty deterministically selected digest candidates received model-assisted close reading. The review observes that a contact-oriented question can receive an excitement/formula answer; nested reported speech is not a direct entity turn; precise dates and percentages remain attributed assertions; and a physical-claims keyword is not a clinical validation. The inspected material was the retained question/gist fields. No reviewer listened to the audio or inspected a new transcript in this phase, and the twenty readings do not establish accuracy or inter-rater agreement.')
paired=read(EXP/'qa/pair-close-reading.json')
add(f"A subsequent purposive paired reading inspects {len(paired['records'])} high-question-similarity examples, selecting the first distinct left-question strings in descending cosine order. The model annotations identify compatible paraphrases with low answer-gist cosine, different facets that are not necessarily contradictions, and possible repeated source families. For example, the question of preparing for contact receives passion/formula/vibration advice in both summaries despite low lexical answer similarity. Another pair uses a relative time window versus calendar windows; without original recording dates, it cannot establish chronological drift. Every answer-agreement field remains undetermined. These selected examples refine interpretation of retrieval, not its representative accuracy.")

(OUT/'expansion-results.tex').write_text('\n\n'.join(text)+'\n')
close=read(EXP/'qa/close-reading.json')
close_rows='\n'.join(' & '.join(esc(x) for x in [row['candidateId'],row['interpretation'],row['caution']])+r' \\' for row in close['records'])
(OUT/'close-reading-table.tex').write_text('\n'.join([r'\begingroup\footnotesize',r'\setlength{\tabcolsep}{3pt}',r'\begin{longtable}{p{0.19\textwidth}p{0.36\textwidth}p{0.40\textwidth}}',r'\toprule Candidate ID & Model-assisted interpretation & Recorded caution \\ \midrule\endhead',close_rows,r'\bottomrule',r'\end{longtable}',r'\endgroup'])+'\n')
pair_rows='\n'.join(' & '.join(esc(x) for x in [row['leftId']+' / '+row['rightId'],row['reading']+' '+row['interpretation'],row['caution']])+r' \\' for row in paired['records'])
(OUT/'paired-reading-table.tex').write_text('\n'.join([r'\begingroup\footnotesize',r'\setlength{\tabcolsep}{3pt}',r'\begin{longtable}{p{0.23\textwidth}p{0.36\textwidth}p{0.36\textwidth}}',r'\toprule Candidate pair IDs & Model-assisted paired reading & Recorded caution \\ \midrule\endhead',pair_rows,r'\bottomrule',r'\end{longtable}',r'\endgroup'])+'\n')
inputs={str(p.relative_to(ATLAS)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [EXP/'analysis/results.json',EXP/'qa/summary.json',EXP/'qa/question-pairs.json',EXP/'qa/close-reading.json',EXP/'qa/pair-close-reading.json',EXP/'acquisition/acquisition-summary.json',ATLAS/'dist/analysis/data.json',EXP/'literature/scholarly-register.json']}
(HERE/'input-manifest.json').write_text(json.dumps({'sourceCommit':'1d6eb36379ed7730dc0cb2e85d83b9e77205b07b','inputs':inputs,'note':'Generated values bind the current expansion manuscript to executed outputs; review receipts apply only to their named artifacts.'},indent=2)+'\n')
print(json.dumps({'generated_values':len(values),'figures':6,'inputs':len(inputs),'qa_candidates':qc['qaCandidates'],'qa_bearing_uploads':qc['videosWithQACandidates']}))
