# Insurance Price Adequacy and Reserve Uncertainty

Two independent actuarial case studies: French motor pricing and U.S. private-passenger auto reserving. The datasets represent different populations and are never joined.

**Status:** source audit, frozen analysis protocol and both actuarial baselines
are complete. Development results are available; final holdouts remain
unscored. Challenger comparisons, final reports and a released demonstration
are the next stages.

The comparison connects actuarial baselines to calibration, tail sensitivity
and documented decision assumptions. The [protocol](docs/PROTOCOL.md) was
committed before fitting. Read the [baseline report](reports/BASELINE_REPORT.md)
for the measured findings and their limitations.

- Pricing: development Tweedie deviance is 6.76% lower than a training-only
  constant tariff, with unresolved aggregate underprediction and worse
  severity-component deviance.
- Reserving: nominal 95% Mack-normal intervals cover 41 of 53 development
  outcomes (77.4%). Negative net increments are retained where cumulative
  losses remain in the model's positive domain.

These are development findings, not final evidence of superiority or a
commercial pricing/reserving recommendation.

## Reproduce the baseline milestone

Python 3.12:

```bash
python -m pip install -r requirements.txt
python scripts/audit_data.py
python scripts/reserve_valuation.py
python -m unittest discover -s tests -v
python scripts/run_baselines.py
python scripts/report_baselines.py
```

The downloader checks fixed hashes and stops on upstream changes. Raw observations remain outside this repository. Audit outputs contain aggregates and source identifiers.

The pricing files reconcile exactly across all 677,991 policies and 26,444
claims. A valuation cutoff separates observed reserve history from subsequent
runoff; model eligibility never consults future completeness or loss outcomes.
Eleven tests check the numerical baseline, exposure/claim weighting and data
boundaries. Intermediate fitted models and row-level predictions remain local.

See [data provenance](docs/DATA.md) and [current audit decisions](docs/AUDIT_DECISIONS.md).

Project: Prasanna K · M.A. Actuarial Economics, Madras School of Economics.
