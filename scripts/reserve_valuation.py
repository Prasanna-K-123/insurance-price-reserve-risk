"""Build a paid-loss valuation view without consulting subsequent runoff.

This is a data boundary, not a fitted reserving model. No full-panel filter,
future losses, premium fields, or posted reserve estimates enter eligibility.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = "6e838f1e44c67218133ef1c8e28ca2b34b9f21ba4ee94de408c412638f798d96"
FIELDS = ("GRCODE", "AccidentYear", "DevelopmentYear", "DevelopmentLag", "CumPaidLoss")


def valuation_view(rows, *, valuation_year=2007, first_accident_year=1998, last_accident_year=None, max_lag=10):
    """Return historical records and eligibility based only on their contents.

    Eligibility here means a complete observed triangle within the specified
    window, not suitability for every stochastic model. Preserve negative net
    losses; expose model-domain flags instead of silently deleting values.
    """
    if last_accident_year is None:
        last_accident_year = valuation_year
    if not first_accident_year <= last_accident_year <= valuation_year or max_lag < 1:
        raise ValueError("Invalid valuation window")
    expected = {
        (year, lag)
        for year in range(first_accident_year, last_accident_year + 1)
        for lag in range(1, min(max_lag, valuation_year - year + 1) + 1)
    }
    records, entities, seen = [], {}, set()
    for source in rows:
        development_year = int(source["DevelopmentYear"])
        # Do not inspect loss amounts or other fields from future observations.
        if development_year > valuation_year:
            continue
        accident_year = int(source["AccidentYear"])
        if not first_accident_year <= accident_year <= last_accident_year:
            continue
        lag = int(source["DevelopmentLag"])
        if not 1 <= lag <= max_lag:
            raise ValueError("Observed development lag outside the supported horizon")
        if development_year != accident_year + lag - 1:
            raise ValueError("Observed calendar identity mismatch")
        entity = str(source["GRCODE"])
        if not entity.strip():
            raise ValueError("Missing entity identifier")
        key = (entity, accident_year, lag)
        if key in seen:
            raise ValueError("Duplicate observed development cell")
        seen.add(key)
        paid = float(source["CumPaidLoss"])
        if not math.isfinite(paid):
            raise ValueError("Nonfinite observed cumulative paid loss")
        records.append(dict(zip(FIELDS, (entity, accident_year, development_year, lag, paid))))
        entities.setdefault(entity, {})[(accident_year, lag)] = paid

    ledger = []
    for entity, cells in sorted(entities.items()):
        increments = []
        for (year, lag), amount in cells.items():
            if lag == 1:
                increments.append(amount)
            elif (year, lag - 1) in cells:
                increments.append(amount - cells[(year, lag - 1)])
            # An increment across a missing predecessor is unknown, not zero.
        complete = set(cells) == expected
        ledger.append({
            "GRCODE": entity,
            "observed_cells": len(cells),
            "missing_cells": len(expected - set(cells)),
            "eligible_observed_triangle": complete,
            "negative_cumulative_cells": sum(value < 0 for value in cells.values()),
            "zero_cumulative_cells": sum(value == 0 for value in cells.values()),
            "known_increment_cells": len(increments),
            "negative_increment_cells": sum(value < 0 for value in increments),
            "strictly_positive_cumulative": all(value > 0 for value in cells.values()),
            "nonnegative_increments": (
                all(value >= 0 for value in increments) if complete else None
            ),
        })
    records.sort(key=lambda row: (row["GRCODE"], row["AccidentYear"], row["DevelopmentLag"]))
    return records, ledger


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def main():
    path = ROOT / "data/raw/ppauto_pos98_07.csv"
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != SOURCE_SHA256:
        raise ValueError("Reserve source checksum differs from the audited version")
    records, ledger = valuation_view(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    eligible = [row for row in ledger if row["eligible_observed_triangle"]]
    private = ROOT / "data/processed"
    private.mkdir(parents=True, exist_ok=True)
    view_bytes, ledger_bytes = json_bytes(records), json_bytes(ledger)
    (private / "reserve_paid_asof_2007.json").write_bytes(view_bytes)
    (private / "reserve_eligibility_asof_2007.json").write_bytes(ledger_bytes)
    report = {
        "source_sha256": SOURCE_SHA256,
        "valuation_year": 2007,
        "first_accident_year": 1998,
        "maximum_development_lag": 10,
        "expected_cells_per_complete_triangle": 55,
        "allowed_columns": list(FIELDS),
        "visible_records": len(records),
        "visible_entities": len(ledger),
        "eligible_observed_triangles": len(eligible),
        "incomplete_observed_triangles": len(ledger) - len(eligible),
        "eligible_with_negative_cumulative": sum(row["negative_cumulative_cells"] > 0 for row in eligible),
        "eligible_with_zero_cumulative": sum(row["zero_cumulative_cells"] > 0 for row in eligible),
        "eligible_with_negative_increments": sum(row["negative_increment_cells"] > 0 for row in eligible),
        "eligible_with_positive_cumulative_and_nonnegative_increments": sum(
            row["strictly_positive_cumulative"] and row["nonnegative_increments"] for row in eligible
        ),
        "private_view_sha256": hashlib.sha256(view_bytes).hexdigest(),
        "private_ledger_sha256": hashlib.sha256(ledger_bytes).hexdigest(),
        "currency_unit": "Unverified; values retain source units, with no currency conversion or monetary claim.",
        "interpretation": "Observed completeness and model-domain flags only. No model fitted, final cohort selected, or forecast evaluated.",
        "vintage_limitation": "Computational cutoff in a later compiled file; not proof of point-in-time historical release availability.",
    }
    target = ROOT / "reports/reserve_valuation_audit.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(json_bytes(report))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
