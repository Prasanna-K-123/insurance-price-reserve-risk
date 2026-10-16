"""Prespecified metrics and comparisons, with frozen-artifact verification."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from statistics import NormalDist

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from .common import ROOT, configuration, provenance, save_json, sha256, split_digest, split_name
from .pricing import features, load_pricing, metrics
from .challengers import CATEGORIES, pricing_assignments, simulate_remaining_paid, simulation_seed, tree_design
from .reserving import SOURCE_SHA256, interval_score, mack, matrix_for_entity, valuation_view


def tweedie_deviance_rows(actual_rate, predicted_rate, power=1.5):
    y, mu = np.asarray(actual_rate, float), np.asarray(predicted_rate, float)
    if not 1 < power < 2 or (y < 0).any() or (mu <= 0).any() or not np.isfinite(y).all() or not np.isfinite(mu).all():
        raise ValueError("Invalid compound Poisson Tweedie inputs")
    return 2 * (y**(2-power) / ((1-power)*(2-power)) - y * mu**(1-power)/(1-power) + mu**(2-power)/(2-power))


def paired_bootstrap(difference, weights, repetitions, seed):
    difference, weights = np.asarray(difference, float), np.asarray(weights, float)
    if difference.shape != weights.shape or difference.ndim != 1 or len(difference) < 2:
        raise ValueError("At least two aligned pairs are required")
    if not np.isfinite(difference).all() or not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError("Invalid paired bootstrap inputs")
    rng = np.random.default_rng(seed)
    samples = np.empty(repetitions)
    for b in range(repetitions):
        indices = rng.integers(0, len(difference), size=len(difference))
        sampled_weights = weights[indices]
        samples[b] = np.sum(difference[indices] * sampled_weights) / sampled_weights.sum()
    return {"estimate": float(np.sum(difference * weights) / weights.sum()),
        "ci95_percentile": np.quantile(samples, [0.025, 0.975]).tolist(),
        "repetitions": repetitions, "seed": seed, "paired_units": len(difference),
        "uncertainty_scope": "Resampling evaluation units conditional on fitted models and calibration; not training or model-selection uncertainty."}


def wilson_interval(successes, total):
    z = NormalDist().inv_cdf(0.975)
    p, denom = successes / total, 1 + z*z / total
    center = (p + z*z / (2*total)) / denom
    half = z * np.sqrt(p*(1-p)/total + z*z/(4*total*total)) / denom
    return [float(center-half), float(center+half)]


def read_reserve_source():
    path = ROOT / "data/raw/ppauto_pos98_07.csv"
    if sha256(path) != SOURCE_SHA256:
        raise ValueError("Reserve source differs from frozen audit")
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))))


def reserve_forecasts(rows, valuation_year, config, group):
    """Prediction-only function: the valuation view is the sole model input."""
    settings = config["reserving"]
    records, ledger = valuation_view(rows, valuation_year=valuation_year,
        first_accident_year=settings["first_accident_year"], last_accident_year=settings["last_accident_year"],
        max_lag=settings["maximum_development_lag"])
    assignments = {row["GRCODE"]: split_name(row["GRCODE"], "reserving", config["seed"], settings["development_fraction"]) for row in ledger}
    eligible = [row["GRCODE"] for row in ledger if row["eligible_observed_triangle"] and row["strictly_positive_cumulative"] and assignments[row["GRCODE"]] == group]
    forecasts = []
    for entity in eligible:
        triangle = matrix_for_entity(records, entity, settings["first_accident_year"], settings["last_accident_year"], settings["maximum_development_lag"])
        fit = mack(triangle)
        latest = float(fit["latest"].sum())
        samples = simulate_remaining_paid(fit, settings["challenger_simulations"], simulation_seed(entity, valuation_year, config["seed"]))
        forecast = {"GRCODE": entity, "valuation_year": valuation_year, "latest_paid": latest,
            "point_prediction": fit["total_remaining_paid"], "mack_standard_error": fit["total_standard_error"],
            "simulation_mean": float(samples.mean()),
            "simulation_mean_monte_carlo_se": float(samples.std(ddof=1) / np.sqrt(len(samples))),
            "negative_simulated_remaining_fraction": float(np.mean(samples < 0)),
            "minimum_factor": float(fit["factors"].min()),
            "observed_negative_increments": bool(np.any(np.diff(triangle, axis=1) < 0)),
        }
        for level in settings["interval_levels"]:
            alpha, suffix = 1-level, str(round(100*level))
            z = NormalDist().inv_cdf((1+level)/2)
            forecast[f"mack_interval_{suffix}"] = [fit["total_remaining_paid"]-z*fit["total_standard_error"], fit["total_remaining_paid"]+z*fit["total_standard_error"]]
            forecast[f"simulation_interval_{suffix}"] = np.quantile(samples, [alpha/2, 1-alpha/2]).tolist()
        forecasts.append(forecast)
    counts = {"visible_entities": len(ledger), "complete_observed_triangles": sum(r["eligible_observed_triangle"] for r in ledger),
        "positive_cumulative_eligible_entities": sum(r["eligible_observed_triangle"] and r["strictly_positive_cumulative"] for r in ledger),
        "forecast_entities": len(forecasts), "group": group,
        "entity_assignment_sha256": split_digest(assignments.keys(), assignments.values())}
    return forecasts, counts


def score_reserve_forecasts(rows, forecasts, config, seed):
    settings = config["reserving"]
    permitted = {forecast["GRCODE"] for forecast in forecasts}
    endpoints = {}
    for row in rows:
        if row["GRCODE"] in permitted and int(row["DevelopmentLag"]) == settings["maximum_development_lag"]:
            endpoints.setdefault(row["GRCODE"], {})[int(row["AccidentYear"])] = float(row["CumPaidLoss"])
    expected = set(range(settings["first_accident_year"], settings["last_accident_year"]+1))
    records = []
    missing = []
    for forecast in forecasts:
        entity = forecast["GRCODE"]
        if set(endpoints.get(entity, {})) != expected:
            missing.append(entity)
            continue
        if not np.isfinite(list(endpoints[entity].values())).all():
            raise ValueError("Nonfinite observed runoff endpoint")
        actual = sum(endpoints[entity].values()) - forecast["latest_paid"]
        record = {**forecast, "actual_remaining_paid": actual,
            "negative_endpoint_cells": sum(v < 0 for v in endpoints[entity].values()),
            "normalized_error": (forecast["point_prediction"]-actual)/forecast["latest_paid"]}
        for method in ("mack", "simulation"):
            for level in settings["interval_levels"]:
                suffix = str(round(level*100))
                lower, upper = forecast[f"{method}_interval_{suffix}"]
                record[f"{method}_covered_{suffix}"] = bool(lower <= actual <= upper)
                record[f"{method}_score_{suffix}"] = interval_score(actual, lower, upper, 1-level)/forecast["latest_paid"]
                record[f"{method}_width_{suffix}"] = (upper-lower)/forecast["latest_paid"]
        records.append(record)
    if len(records) < 2:
        raise ValueError("Insufficient observable endpoints")
    summary = {"forecast_entities": len(forecasts), "scored_entities": len(records), "missing_endpoints": len(missing),
        "negative_realized_runoff_entities": sum(row["actual_remaining_paid"] < 0 for row in records),
        "negative_endpoint_cells": sum(row["negative_endpoint_cells"] for row in records),
        "historical_negative_increment_entities": sum(row["observed_negative_increments"] for row in records),
        "mean_normalized_error": float(np.mean([row["normalized_error"] for row in records])),
        "mean_absolute_normalized_error": float(np.mean([abs(row["normalized_error"]) for row in records])),
        "simulation_mean_absolute_mc_error_normalized": float(np.mean([abs(row["simulation_mean"]-row["point_prediction"])/row["latest_paid"] for row in records])),
        "simulation_draws_per_entity": settings["challenger_simulations"]}
    for method in ("mack", "simulation"):
        diagnostic = {}
        for level in settings["interval_levels"]:
            suffix = str(round(level*100))
            successes = sum(row[f"{method}_covered_{suffix}"] for row in records)
            diagnostic[f"coverage_{suffix}"] = successes/len(records)
            diagnostic[f"covered_{suffix}"] = successes
            diagnostic[f"coverage_{suffix}_wilson95"] = wilson_interval(successes, len(records))
            diagnostic[f"mean_normalized_score_{suffix}"] = float(np.mean([row[f"{method}_score_{suffix}"] for row in records]))
            diagnostic[f"mean_normalized_width_{suffix}"] = float(np.mean([row[f"{method}_width_{suffix}"] for row in records]))
        summary[method] = diagnostic
    difference = np.array([row["simulation_score_95"]-row["mack_score_95"] for row in records])
    summary["primary_interval_score_difference"] = paired_bootstrap(difference, np.ones(len(records)), settings["bootstrap_repetitions"], seed)
    summary["comparison_caveat"] = "Entity-bootstrap inference assumes sufficiently independent entities; common calendar/corporate shocks and finite simulation quantiles limit precision."
    return summary, records, missing


def run_reserve_challenger():
    config, rows = configuration(), read_reserve_source()
    year = config["reserving"]["primary_valuation_year"]
    forecasts, cohort = reserve_forecasts(rows, year, config, "development")
    summary, records, missing = score_reserve_forecasts(rows, forecasts, config, config["seed"]+200)
    baseline = json.loads((ROOT / "reports/reserve_baseline.json").read_text())
    if not np.isclose(summary["mack"]["mean_normalized_score_95"], baseline["development"]["mean_normalized_interval_score_95"], rtol=1e-13):
        raise ValueError("Mack development result changed")
    report = {**provenance(), "status": "Predeclared simulation evaluated on development entities only.", "cohort": cohort, "development": summary}
    save_json(ROOT / "data/processed/reserve_challenger_development.json", records)
    save_json(ROOT / "reports/reserve_challenger.json", report)
    print("Reserve challenger: development comparison saved", flush=True)
    return report


def computational_hashes():
    paths = sorted((ROOT / "src/insurance_risk").glob("*.py")) + [ROOT / "scripts/reserve_valuation.py"]
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def freeze_models():
    """Seal both pricing fits and all reserve forecasts before test scoring."""
    config, rows = configuration(), read_reserve_source()
    pricing = load_pricing()
    assignments = pricing_assignments(pricing, config)
    train = pricing.loc[assignments == "train"]
    glm, hgb = (joblib.load(ROOT / f"artifacts/pricing_{name}.joblib") for name in ("glm", "hgb"))
    for model in (glm, hgb):
        for key in ("config_sha256", "protocol_sha256"):
            if model[key] != provenance()[key]:
                raise ValueError("Artifact protocol identity mismatch")
    with threadpool_limits(limits=1):
        xglm, xhgb = glm["preprocessor"].transform(features(train)), tree_design(train, hgb["encoder"])
        rates = {"glm": glm["frequency"].predict(xglm)*glm["severity"].predict(xglm)*glm["pure_premium_calibration"],
                 "hgb": hgb["frequency"].predict(xhgb)*hgb["severity"].predict(xhgb)*hgb["pure_premium_calibration"]}
    cutpoints = {name: np.quantile(rate, np.arange(0.1, 1, 0.1)).tolist() for name, rate in rates.items()}
    predictions, cohorts = {}, {}
    for year in [config["reserving"]["primary_valuation_year"], config["reserving"]["secondary_valuation_year"]]:
        predictions[str(year)], cohorts[str(year)] = reserve_forecasts(rows, year, config, "test")
    save_json(ROOT / "artifacts/reserve_test_forecasts.json", predictions)
    manifest = {**provenance(), "status": "Frozen before final-test scoring; no target-derived test metrics included.",
        "computational_hashes": computational_hashes(),
        "artifacts_sha256": {name: sha256(ROOT / "artifacts" / name) for name in ("pricing_glm.joblib", "pricing_hgb.joblib", "reserve_test_forecasts.json")},
        "calibration": {"glm": glm["pure_premium_calibration"], "hgb": hgb["pure_premium_calibration"]},
        "training_risk_decile_cutpoints": cutpoints,
        "pricing_split_sha256": split_digest(pricing.IDpol, assignments),
        "reserve_test_cohorts": cohorts,
        "seed_convention": "SHA256 reserve-simulation:seed:valuation:entity first 64 bits; bootstrap seed+101 pricing, seed+201/202 reserve 2007/2009.",
        "finite_budget": "Two pricing families, fixed iterations/penalties, two reserve uncertainty methods, 2000 simulations/entity, no tuning."}
    save_json(ROOT / "reports/model_freeze.json", manifest)
    print("Model/calibration/code/forecast seal saved; final test still unscored", flush=True)
    return manifest


def verify_freeze():
    manifest = json.loads((ROOT / "reports/model_freeze.json").read_text())
    for key in ("config_sha256", "protocol_sha256"):
        if manifest[key] != provenance()[key]:
            raise ValueError("Frozen protocol changed")
    if manifest["computational_hashes"] != computational_hashes():
        raise ValueError("Computational source changed after the freeze")
    for name, digest in manifest["artifacts_sha256"].items():
        if sha256(ROOT / "artifacts" / name) != digest:
            raise ValueError(f"Frozen artifact changed: {name}")
    return manifest


def grouped_calibration(frame, rate, group_labels):
    result = []
    labels = np.asarray(group_labels, dtype=str)
    for group in sorted(np.unique(labels)):
        mask = labels == group
        part = frame.loc[mask]
        exposure = float(part.Exposure.sum())
        expected = float(np.sum(part.Exposure.to_numpy()*rate[mask]))
        result.append({"group": str(group), "policies": int(mask.sum()), "claims": int(part.ClaimNb.sum()),
            "exposure_years": exposure, "observed_annual_loss_source_units": float(part.Loss.sum()/exposure),
            "predicted_annual_loss_source_units": expected/exposure,
            "observed_to_predicted": float(part.Loss.sum()/expected), "sparse_claims_below_30": bool(part.ClaimNb.sum()<30)})
    return result


def evaluate_pricing(manifest, config):
    frame = load_pricing()
    assignment = pricing_assignments(frame, config)
    if split_digest(frame.IDpol, assignment) != manifest["pricing_split_sha256"]:
        raise ValueError("Policy split changed")
    test = frame.loc[assignment == "test"]
    exposure, actual = test.Exposure.to_numpy(), test.Loss.to_numpy()
    glm, hgb = (joblib.load(ROOT / f"artifacts/pricing_{name}.joblib") for name in ("glm", "hgb"))
    with threadpool_limits(limits=1):
        xglm, xhgb = glm["preprocessor"].transform(features(test)), tree_design(test, hgb["encoder"])
        outputs = {"glm": (glm["frequency"].predict(xglm), glm["severity"].predict(xglm)),
                   "hgb": (hgb["frequency"].predict(xhgb), hgb["severity"].predict(xhgb))}
    models, losses, predictions = {}, {}, {}
    power = config["pricing"]["primary_tweedie_power"]
    age_groups = features(test).DriverBand.to_numpy()
    for name, (frequency, severity) in outputs.items():
        calibration = manifest["calibration"][name]
        rate = frequency*severity*calibration
        predictions[name] = rate
        losses[name] = tweedie_deviance_rows(actual/exposure, rate, power)
        risk_bands = 1 + np.searchsorted(manifest["training_risk_decile_cutpoints"][name], rate, side="right")
        models[name] = {"uncalibrated": metrics(test, frequency, severity, power),
            "calibrated_tweedie_deviance": float(np.average(losses[name], weights=exposure)),
            "calibrated_loss_observed_to_predicted": float(actual.sum()/np.sum(rate*exposure)),
            "calibrated_annual_loss_mae_source_units": float(np.abs(actual-rate*exposure).sum()/exposure.sum()),
            "training_risk_bands": grouped_calibration(test, rate, [f"{band:02d}" for band in risk_bands]),
            "age_groups": grouped_calibration(test, rate, age_groups),
            "region_groups": grouped_calibration(test, rate, test.Region.astype(str).to_numpy())}
    difference = losses["hgb"]-losses["glm"]
    primary = paired_bootstrap(difference, exposure, config["pricing"]["bootstrap_repetitions"], config["seed"]+101)
    # Prespecified descriptive tail sensitivity; no tuning or alternative decision.
    order = np.lexsort((test.IDpol.to_numpy(dtype=str), -actual))
    retained = np.ones(len(test), dtype=bool)
    retained[order[:10]] = False
    tail = {"removed_policies": 10, "removed_actual_loss_fraction": float(actual[~retained].sum()/actual.sum()),
        "paired_deviance_difference_remaining": float(np.average(difference[retained], weights=exposure[retained])),
        "interpretation": "Outcome-selected diagnostic only; does not replace the uncapped primary evaluation."}
    result = {**provenance(), "policies": len(test), "claims": int(test.ClaimNb.sum()),
        "models": models, "primary_difference_hgb_minus_glm": primary, "tail_sensitivity": tail,
        "recommendation": "hgb" if primary["ci95_percentile"][1] < 0 else "glm",
        "recommendation_scope": "Historical predictive loss-cost study, conditional on reported checks; no profit or deployment claim.",
        "hgb_unseen_categories": {name: int(np.isnan(xhgb[:,i]).sum()) for i,name in enumerate(CATEGORIES)},
        "test_source_scope": "Policy split; observation chronology unavailable."}
    np.savez_compressed(ROOT / "artifacts/pricing_final_predictions.npz", policy_id=test.IDpol.to_numpy(dtype=str),
        glm=predictions["glm"], hgb=predictions["hgb"], actual_loss=actual, exposure=exposure)
    save_json(ROOT / "reports/pricing_final.json", result)
    return result


def run_final_evaluation():
    manifest, config = verify_freeze(), configuration()
    print("Freeze verified. Running the predeclared pricing final comparison.", flush=True)
    pricing = evaluate_pricing(manifest, config)
    rows = read_reserve_source()
    forecasts = json.loads((ROOT / "artifacts/reserve_test_forecasts.json").read_text())
    results = {}
    for index, year in enumerate([config["reserving"]["primary_valuation_year"], config["reserving"]["secondary_valuation_year"]]):
        summary, records, missing = score_reserve_forecasts(rows, forecasts[str(year)], config, config["seed"]+201+index)
        results[str(year)] = {"cohort": manifest["reserve_test_cohorts"][str(year)], "evaluation": summary}
        save_json(ROOT / f"data/processed/reserve_final_{year}.json", {"records": records, "missing_endpoints": missing})
    primary = results[str(config["reserving"]["primary_valuation_year"])]["evaluation"]["primary_interval_score_difference"]
    reserve = {**provenance(), "valuations": results,
        "recommendation": "simulation" if primary["ci95_percentile"][1] < 0 else "mack",
        "recommendation_scope": "Choice between two historical uncertainty approximations; neither is guaranteed calibrated.",
        "secondary_does_not_change_primary_decision": True}
    save_json(ROOT / "reports/reserve_final.json", reserve)
    verify_freeze()
    print("Final comparisons saved; frozen artifacts and source remain unchanged.", flush=True)
    return pricing, reserve
