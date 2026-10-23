# Round 2: observed implementation review and corrections

Reviewed artifact: round1 UI, actual pipeline round1 dataset (925 unique videos, 189 account routes, 449 durations), four generated static figures. Root performed browser interaction and supplied observed findings; method_panel independently inspected source/data bindings. UI worker performed static/dynamic rendering checks, not browser QA.

| Finding | Evidence | Impact | Decision / implementation | Acceptance |
| --- | --- | --- | --- | --- |
| Account table renders all 189 rows at once | Root browser observation | Long scan and repeated scroll burden | Page by 25 with Next/Previous and 26–50-style range, retain search/sort | Node render verifies 25 data rows and page 2 range |
| No-video accounts show “— of this sample” | Root browser observation | Denominator ambiguity | Explicit “No indexed videos” | Node render verifies state |
| Exact dates display Unresolved in source table | Independent method_panel: actual schema uses `date`, UI read other keys | Misstates source evidence | Read `date` and retain compatibility fallbacks | Node render asserts an actual date appears |
| Supplied/fresh source distinction absent from detail table | Independent method_panel | Implied evidence uniformity | Show titleSource, durationSource, dateSource | Generated source output reviewed |
| Static chart data/cutoff not linked nearby | Independent method_panel caption contract | Hard to audit values | Add snapshot date plus underlying CSV alongside figure download | HTML source checks; root browser follow-up pending |
| Unknown-duration bins plotted as zeros | UI worker source audit | Missingness could look observed | Empty-state chart when durationCount=0 | Source and rendering checked |
| Topic comparison without eligible titles treated absence as zero | UI worker source audit | Unsupported absence inference | Null/— values for absent eligible-title denominator | Rendering checked |

Actual checks: `node --check dist/app.js`; `node analysis_work/ui/check-render.cjs`, exercising all four renderer functions against real data, no NaN/object-string results, pagination, exact-date binding and missing coverage. These are not user studies or screen-reader tests.

Next round: integrate actual learned-embedding/transcript schema (if generated), root browser interaction review, independent caption/metric review, fix remaining blockers.
