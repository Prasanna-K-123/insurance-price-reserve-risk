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

## Valuation boundary completed — 16 October 2026

`scripts/reserve_valuation.py` constructs the 2007 paid-loss view from observed
records only. Five focused tests cover future-value/deletion invariance,
future-only entities, excluded reserve fields, missing history, calendar/key
errors and preservation of negative net amounts. Aggregate results are in
`reports/reserve_valuation_audit.json`; entity rows stay under ignored `data/`.

The view contains 7,513 cells and 143 entities. Of 121 complete observed
triangles, 96 have strictly positive cumulative amounts and qualify for the
chosen Mack domain. Negative increments alone do not exclude an entity. The
Mack/parametric simulation comparison accommodates them explicitly. These
are as-of domain decisions, not selections on future forecasting performance.

The full analysis design, policy/entity splits, model budgets and failure
rules are now frozen in `PROTOCOL.md` and `config.json`, before fitting.
NAIC filing instructions support a thousands-of-dollars convention, but the
exact CAS/S&P export scale remains unverified. Outputs therefore use source
units and dimensionless comparisons without asserting dollar reserves.

No model comparison or final test outcome has been produced at this checkpoint.
