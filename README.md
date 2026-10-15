# Insurance Price Adequacy and Reserve Uncertainty

Two independent actuarial case studies: French motor pricing and U.S. private-passenger auto reserving. The datasets represent different populations and are never joined.

**Status:** source acquisition and aggregate data audit completed; analysis protocol and modelling are next. No models fitted, performance results claimed or pricing recommendations issued yet.

The intended comparison connects actuarial baselines to calibration, tail sensitivity and documented decision assumptions. The analysis protocol will be fixed after the source audit and before fitting models.

## Audit the inputs

Python 3.12:

```bash
python -m pip install -r requirements-data.txt
python scripts/audit_data.py
```

The downloader checks fixed hashes and stops on upstream changes. Raw observations remain outside this repository. Audit outputs contain aggregates and source identifiers.

The pricing files reconcile exactly across all 677,991 policies and 26,444 claims. The reserve panel contains incomplete histories and negative net paid increments; these limitations are recorded before choosing model eligibility.

See [data provenance](docs/DATA.md) and [current audit decisions](docs/AUDIT_DECISIONS.md).

Project: Prasanna K · M.A. Actuarial Economics, Madras School of Economics.
