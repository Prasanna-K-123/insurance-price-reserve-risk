# Audit decisions before model fitting

## Recorded now — 16 October 2026

- Keep both case studies separate; retain raw source bytes and fixed checksums locally.
- Pricing audit: 677,991 unique policy IDs, 26,444 severity rows, no missing cells, no unmatched claims and exact count reconciliation for every policy. The current maintainer data has 12 frequency columns. Preserve categorical ID labels exactly.
- All claim amounts and exposures are positive; 1,224 exposures exceed one year, with a maximum of 2.01. These are investigated as recorded durations rather than automatically clipped.
- Preserve exposure above one year for investigation rather than silently truncating it. A long exposure is not automatically invalid.
- Reconcile reported claim counts against severity rows by policy before defining a frequency–severity target. Do not fill an unmatched positive claim with an invented zero loss.
- Use actual policy separation for pricing; no fabricated time ordering.
- The reserve file has 143 entities and 13,250 rows. Only 121 entities contain all 100 accident-year/development cells. Incomplete panels cannot be labelled complete ten-year histories.
- There are 92 negative cumulative paid cells and 733 negative paid increments. These are net amounts; investigate recovery/correction interpretation and model-domain restrictions. Do not silently clip or remove them based on forecasting performance.
- There are 1,300 zero and 60 negative net-premium rows. Premium-based ratios need explicit denominator rules. Premium is constant within each observed insurer/accident-year group.
- No duplicate insurer/accident-year/development keys or calendar-identity errors were observed.

## Decisions still required

Pricing reconciliation is complete. Establish reserve currency units; define training/validation eligibility using information available at each historical diagonal; disclose any retrospective complete-panel selection. Then freeze split identifiers, candidate model budgets, calibration strategy, evaluation targets, uncertainty methods and failure handling before fitting.

No model comparison or final test outcome has been produced at this checkpoint.
