# Round 4: source and standalone figure review

Reviewer: dashboard/design workstream. Actual artifacts inspected: body.tex plus generated duration.png and matched-similarity.png on2026-10-23. This is a pre-PDF review; full-page layout review is pending a successful manuscript build.

## Findings

1. **Major, figure bounds:** matched-similarity panelA uses a zero lower horizontal limit although the generating data includes a negative matched-title cosine. The figure workstream independently identified a minimum below−0.045 and will expose it in round 5. Points must not disappear solely because the plotting range omits valid observations.
2. **Medium, overlap:** duration legend lower-right overlaps the Divine Insights interquartile segment. Move it into unused upper-right space; do not abbreviate the data or cover a point.
3. **Medium, readability:** matched-similarity has two panels but the first body version used a single-column include. Use full two-column width; root has already confirmed changing it. PanelB's deletion diagnostic must be described in the caption with its dashed full-sample baseline. Remove the hypothetical diagonal caveat because no such diagonal is drawn.
4. **Medium, precision:** the duration caption's wording `Dots, means, and quartile marks` does not identify which dot is the median. State circles=median, diamonds=mean, spans=25th–75th percentiles, units=minutes, available n next to each label. The graphic measures sample summaries, not all individual uploads.
5. **Low, flow:** the introduction defines observational-unit and text-layer distinctions before the RQs, and the discussion returns to those distinctions. This gives the paper an identifiable measurement contribution. Keep resource/duration findings as context for the matched comparison; do not let a broad dashboard catalog replace a research argument.
6. **Status precision:** any claim that all three manuscript review rounds are already recorded is provisional until rounds 5/6 complete. The final closure record must identify exact PDF hashes and actual inspections.

## Decisions

- Root owns main/body edits and figure workstream owns generated plots. No unauthorized edits to their artifacts.
- Figure workstream acknowledged1–3 and will correct after root seals the first PDF snapshot; root confirmed wider figure and revised caption binding.
- Use the official 2027 style's supported preprint option. Fonts were installed from CTAN into a local TeX tree; dependency probe passes without style changes. The full paper must still be compiled and inspected.
- Preserve all 35 official-linked ICWSM checklist questions, with human-review TBD answers. The draft cannot assert ethics approval or author acceptance.
