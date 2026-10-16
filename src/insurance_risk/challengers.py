"""The two predeclared challengers; no tuning or final-test scoring here."""
from __future__ import annotations

import hashlib
import json

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import OrdinalEncoder
from threadpoolctl import threadpool_limits

from .common import ROOT, configuration, provenance, save_json, sha256, split_digest, split_name
from .pricing import load_pricing, metrics

CATEGORIES = ["VehPower", "VehBrand", "VehGas", "Area", "Region"]
CONTINUOUS = ["DrivAge", "VehAge", "BonusMalus"]


def category_frame(frame):
    result = frame[CATEGORIES].astype(str).copy()
    result.columns = CATEGORIES
    return result


def tree_design(frame, encoder):
    categorical = encoder.transform(category_frame(frame))
    numerical = np.column_stack([frame[name].to_numpy(dtype=float) for name in CONTINUOUS] + [np.log1p(frame.Density.to_numpy(dtype=float))])
    return np.column_stack([categorical, numerical])


def fit_tree_design(frame):
    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=np.nan, encoded_missing_value=np.nan)
    encoder.fit(category_frame(frame))
    return encoder, tree_design(frame, encoder)


def pricing_assignments(frame, config):
    settings = config["pricing"]
    return np.array([split_name(identifier, "pricing", config["seed"], settings["train_fraction"], settings["development_fraction"]) for identifier in frame.IDpol])


def run_pricing_challenger():
    config = configuration()
    settings = config["pricing"]
    frame = load_pricing()
    assignments = pricing_assignments(frame, config)
    baseline = json.loads((ROOT / "reports/pricing_baseline.json").read_text())
    if split_digest(frame.IDpol, assignments) != baseline["split_sha256"]:
        raise ValueError("Policy assignment changed from the frozen baseline")
    train, dev = frame.loc[assignments == "train"], frame.loc[assignments == "development"]
    encoder, xtrain = fit_tree_design(train)
    xdev = tree_design(dev, encoder)
    shared = dict(learning_rate=settings["challenger_learning_rate"],
        max_iter=settings["challenger_iterations"], max_leaf_nodes=settings["challenger_leaves"],
        l2_regularization=settings["challenger_l2"], early_stopping=False,
        categorical_features=list(range(len(CATEGORIES))), random_state=config["seed"])
    frequency = HistGradientBoostingRegressor(loss="poisson", min_samples_leaf=settings["challenger_frequency_min_leaf"], **shared)
    severity = HistGradientBoostingRegressor(loss="gamma", min_samples_leaf=settings["challenger_severity_min_leaf"], **shared)
    positive = train.ClaimNb.to_numpy() > 0
    print(f"Pricing challenger: fixed 200 iterations; {len(train):,} training policies", flush=True)
    with threadpool_limits(limits=1):
        frequency.fit(xtrain, train.ClaimNb / train.Exposure, sample_weight=train.Exposure)
        severity.fit(xtrain[positive], train.MeanSeverity.to_numpy()[positive], sample_weight=train.ClaimNb.to_numpy()[positive])
        frequency_dev, severity_dev = frequency.predict(xdev), severity.predict(xdev)
    diagnostic = metrics(dev, frequency_dev, severity_dev, settings["primary_tweedie_power"])
    calibration = diagnostic["loss_observed_to_predicted"]
    if frequency.n_iter_ != settings["challenger_iterations"] or severity.n_iter_ != settings["challenger_iterations"]:
        raise ValueError("Unexpected iteration budget")
    artifact = {"encoder": encoder, "frequency": frequency, "severity": severity,
        "pure_premium_calibration": calibration, **provenance()}
    joblib.dump(artifact, ROOT / "artifacts/pricing_hgb.joblib")
    np.savez_compressed(ROOT / "artifacts/pricing_hgb_development_predictions.npz",
        policy_id=dev.IDpol.to_numpy(dtype=str), frequency=frequency_dev, severity=severity_dev)
    report = {**provenance(), "status": "Fixed challenger fitted; development only, no final-test scoring.",
        "split_sha256": baseline["split_sha256"], "split_counts": baseline["split_counts"],
        "development_uncalibrated_hgb": diagnostic,
        "development_loss_calibration_multiplier": calibration,
        "frequency_iterations": int(frequency.n_iter_), "severity_iterations": int(severity.n_iter_),
        "early_stopping": False, "hyperparameter_search": False,
        "category_cardinalities": {name: len(values) for name, values in zip(CATEGORIES, encoder.categories_)},
        "development_unseen_categories": {name: int(np.isnan(xdev[:, i]).sum()) for i, name in enumerate(CATEGORIES)},
        "parameters": {**shared, "frequency_min_leaf": settings["challenger_frequency_min_leaf"], "severity_min_leaf": settings["challenger_severity_min_leaf"]}}
    save_json(ROOT / "reports/pricing_challenger.json", report)
    print("Pricing challenger: development results and private model saved", flush=True)
    return report


def lognormal_parameters(mean, variance):
    mean, variance = np.broadcast_arrays(np.asarray(mean, dtype=float), np.asarray(variance, dtype=float))
    if not np.isfinite(mean).all() or not np.isfinite(variance).all() or (mean <= 0).any() or (variance < 0).any():
        raise ValueError("Lognormal moments must be finite, positive mean, nonnegative variance")
    log_variance = np.log1p(variance / mean**2)
    return np.log(mean) - 0.5 * log_variance, np.sqrt(log_variance)


def simulation_seed(entity, valuation_year, seed):
    return int.from_bytes(hashlib.sha256(f"reserve-simulation:{seed}:{valuation_year}:{entity}".encode()).digest()[:8], "big")


def simulate_remaining_paid(fit, repetitions, seed):
    """Positive factor/process moment simulation; shared factor draws by age.

    Uses only fitted historical moments. Theoretical point mean remains the
    chain-ladder point estimate; simulated means are Monte Carlo diagnostics.
    """
    rng = np.random.default_rng(seed)
    latest = np.asarray(fit["latest"], dtype=float)
    current = np.broadcast_to(latest, (repetitions, len(latest))).copy()
    for age, factor in enumerate(fit["factors"]):
        active = np.flatnonzero(np.asarray(fit["latest_ages"]) <= age)
        if not len(active):
            continue
        variance = fit["variance"][age]
        mu, sd = lognormal_parameters(factor, variance / fit["denominators"][age])
        shared_factor = rng.lognormal(mu, sd, size=repetitions)
        before = current[:, active]
        mu, sd = lognormal_parameters(before * shared_factor[:, None], variance * before)
        current[:, active] = rng.lognormal(mu, sd)
    if not np.isfinite(current).all() or (current <= 0).any():
        raise ValueError("Nonfinite/nonpositive simulated cumulative loss")
    return current.sum(axis=1) - latest.sum()
