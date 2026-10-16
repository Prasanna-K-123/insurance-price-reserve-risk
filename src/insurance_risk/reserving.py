"""Volume-weighted chain ladder and Mack total prediction error."""
from __future__ import annotations

import csv
import io
import math
from statistics import NormalDist
import sys

import numpy as np

from .common import ROOT, configuration, provenance, save_json, sha256, split_digest, split_name

sys.path.insert(0, str(ROOT / "scripts"))
from reserve_valuation import SOURCE_SHA256, valuation_view


def mack(triangle):
    """Positive cumulative upper triangle/trapezoid, observed cells first.

    Negative incremental losses are allowed. NaN denotes genuinely unobserved
    later development, never an observed zero. No missing internal cells.
    """
    triangle = np.asarray(triangle, dtype=float)
    if triangle.ndim != 2 or triangle.shape[1] < 4:
        raise ValueError("At least four development ages are required")
    observed = np.isfinite(triangle)
    if np.isinf(triangle).any() or not observed[:, 0].all():
        raise ValueError("Invalid first or nonfinite observed development")
    if (triangle[observed] <= 0).any():
        raise ValueError("Mack domain requires positive cumulative losses")
    ages = observed.sum(axis=1) - 1
    for i, age in enumerate(ages):
        if not observed[i, :age + 1].all() or observed[i, age + 1:].any():
            raise ValueError("Missing internal observed cell")
    n, d = triangle.shape
    factors, variance, denominators, counts = [], [], [], []
    for k in range(d - 1):
        paired = observed[:, k] & observed[:, k + 1]
        x, y = triangle[paired, k], triangle[paired, k + 1]
        if not len(x):
            raise ValueError("No historical pair for development factor")
        f = float(y.sum() / x.sum())
        factors.append(f)
        denominators.append(float(x.sum()))
        counts.append(len(x))
        if len(x) > 1:
            variance.append(float(np.sum(x * (y / x - f)**2) / (len(x) - 1)))
        elif k == d - 2 and len(variance) >= 2:
            a, b = variance[-2:]
            variance.append(min(a, b, b * b / a) if a > 0 else 0.0)
        else:
            raise ValueError("Insufficient variance degrees of freedom before the final factor")
    factors, variance, denominators = map(np.array, (factors, variance, denominators))
    full = triangle.copy()
    for i, age in enumerate(ages):
        for k in range(age, d - 1):
            full[i, k + 1] = full[i, k] * factors[k]
    latest = triangle[np.arange(n), ages]
    endpoint = full[:, -1]
    process_variance = np.zeros(n)
    parameter_covariance = np.zeros((n, n))
    for i, age in enumerate(ages):
        process_variance[i] = endpoint[i]**2 * np.sum(variance[age:] / factors[age:]**2 / full[i, age:-1])
        for j, other_age in enumerate(ages):
            start = max(age, other_age)
            parameter_covariance[i, j] = endpoint[i] * endpoint[j] * np.sum(
                variance[start:] / factors[start:]**2 / denominators[start:]
            )
    total_process, total_parameter = float(process_variance.sum()), float(parameter_covariance.sum())
    return {
        "factors": factors, "variance": variance, "denominators": denominators,
        "pair_counts": np.array(counts), "latest_ages": ages, "full": full,
        "latest": latest, "endpoint": endpoint,
        "remaining_paid": endpoint - latest,
        "process_variance_by_origin": process_variance,
        "parameter_covariance": parameter_covariance,
        "total_remaining_paid": float(np.sum(endpoint - latest)),
        "total_process_variance": total_process,
        "total_parameter_variance": total_parameter,
        "total_standard_error": math.sqrt(total_process + total_parameter),
    }


def interval_score(actual, lower, upper, alpha):
    if not 0 < alpha < 1 or lower > upper:
        raise ValueError("Invalid predictive interval")
    return upper - lower + 2 / alpha * max(lower - actual, 0) + 2 / alpha * max(actual - upper, 0)


def matrix_for_entity(records, entity, first_year, last_year, max_lag):
    triangle = np.full((last_year - first_year + 1, max_lag), np.nan)
    for row in records:
        if row["GRCODE"] == entity:
            triangle[row["AccidentYear"] - first_year, row["DevelopmentLag"] - 1] = row["CumPaidLoss"]
    return triangle


def run_reserve_baseline():
    config, path = configuration(), ROOT / "data/raw/ppauto_pos98_07.csv"
    settings = config["reserving"]
    if sha256(path) != SOURCE_SHA256:
        raise ValueError("Reserve source checksum mismatch")
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
    records, ledger = valuation_view(rows,
        valuation_year=settings["primary_valuation_year"],
        first_accident_year=settings["first_accident_year"],
        last_accident_year=settings["last_accident_year"],
        max_lag=settings["maximum_development_lag"])
    assignments = {
        row["GRCODE"]: split_name(row["GRCODE"], "reserving", config["seed"], settings["development_fraction"])
        for row in ledger
    }
    eligible = [row["GRCODE"] for row in ledger if row["eligible_observed_triangle"] and row["strictly_positive_cumulative"]]
    development = [entity for entity in eligible if assignments[entity] == "development"]
    print(f"Reserving: fit {len(development)} development triangles; final-test runoff remains unscored", flush=True)
    # Endpoint values are collected for development entities only, never used to choose eligibility.
    endpoints = {}
    development_set = set(development)
    for row in rows:
        if row["GRCODE"] in development_set and int(row["DevelopmentLag"]) == settings["maximum_development_lag"]:
            endpoints.setdefault(row["GRCODE"], {})[int(row["AccidentYear"])] = float(row["CumPaidLoss"])
    results, unavailable = [], 0
    expected_years = set(range(settings["first_accident_year"], settings["last_accident_year"] + 1))
    for entity in development:
        fit = mack(matrix_for_entity(records, entity, settings["first_accident_year"], settings["last_accident_year"], settings["maximum_development_lag"]))
        latest = float(fit["latest"].sum())
        result = {"GRCODE": entity,
            "predicted_remaining_paid_source_units": fit["total_remaining_paid"],
            "standard_error_source_units": fit["total_standard_error"],
            "latest_paid_source_units": latest,
            "normalized_prediction": fit["total_remaining_paid"] / latest,
            "normalized_standard_error": fit["total_standard_error"] / latest,
            "minimum_factor": float(fit["factors"].min()),
            "endpoint_observed": set(endpoints.get(entity, {})) == expected_years,
        }
        if result["endpoint_observed"]:
            actual = float(sum(endpoints[entity].values()) - latest)
            result["actual_remaining_paid_source_units"] = actual
            result["normalized_error"] = (fit["total_remaining_paid"] - actual) / latest
            for level in settings["interval_levels"]:
                alpha = 1 - level
                z = NormalDist().inv_cdf((1 + level) / 2)
                lower = fit["total_remaining_paid"] - z * fit["total_standard_error"]
                upper = fit["total_remaining_paid"] + z * fit["total_standard_error"]
                suffix = str(round(level * 100))
                result[f"coverage_{suffix}"] = bool(lower <= actual <= upper)
                result[f"normalized_interval_score_{suffix}"] = interval_score(actual, lower, upper, alpha) / latest
                result[f"normalized_width_{suffix}"] = (upper - lower) / latest
                result[f"negative_total_paid_lower_{suffix}"] = bool(lower + latest < 0)
        else:
            unavailable += 1
        results.append(result)
    scored = [row for row in results if row["endpoint_observed"]]
    if not scored:
        raise ValueError("No observable development endpoints; cannot evaluate baseline")
    diagnostic = {
        "scored_entities": len(scored),
        "mean_normalized_error": float(np.mean([row["normalized_error"] for row in scored])),
        "mean_absolute_normalized_error": float(np.mean([abs(row["normalized_error"]) for row in scored])),
        "negative_realized_remaining_paid_entities": sum(row["actual_remaining_paid_source_units"] < 0 for row in scored),
    }
    for level in settings["interval_levels"]:
        suffix = str(round(level * 100))
        for metric in ("coverage", "normalized_interval_score", "normalized_width"):
            diagnostic[f"mean_{metric}_{suffix}"] = float(np.mean([row[f"{metric}_{suffix}"] for row in scored]))
        diagnostic[f"negative_total_paid_lower_{suffix}_entities"] = sum(row[f"negative_total_paid_lower_{suffix}"] for row in scored)
    report = {
        **provenance(),
        "source_sha256": SOURCE_SHA256,
        "valuation_year": settings["primary_valuation_year"],
        "status": "Development-only Mack baseline evaluation. Final-test entities and 2009 evaluation not scored.",
        "visible_entities": len(ledger),
        "complete_observed_triangles": sum(row["eligible_observed_triangle"] for row in ledger),
        "positive_cumulative_eligible_entities": len(eligible),
        "eligible_development_entities": len(development),
        "eligible_test_entities": len(eligible) - len(development),
        "development_missing_endpoints": unavailable,
        "entity_split_sha256": split_digest(assignments.keys(), assignments.values()),
        "development": diagnostic,
        "currency_policy": "Unconverted source units privately; dimensionless public aggregate metrics.",
        "target": "Remaining net paid loss through lag 10, not unknown ultimate loss.",
        "interval_caveat": "Normal approximation to Mack moments; nominal coverage is not guaranteed.",
    }
    save_json(ROOT / "data/processed/reserve_baseline_development.json", results)
    save_json(ROOT / "reports/reserve_baseline.json", report)
    print("Reserving: development diagnostics saved", flush=True)
    return report
