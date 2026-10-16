"""Policy-separated, exposure-aware Poisson/Gamma actuarial baseline."""
from __future__ import annotations

import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import GammaRegressor, PoissonRegressor
from sklearn.metrics import mean_gamma_deviance, mean_poisson_deviance, mean_tweedie_deviance
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from .common import ROOT, configuration, provenance, save_json, sha256, split_digest, split_name

SOURCE_HASHES = {
    "freMTPL2freq.rda": "82c8598513d9fa78226b6c7d271a9940eca4b8083e9e32320a75d377bdfe15a3",
    "freMTPL2sev.rda": "78e6e5016ae046603b37e88ff8ad8ca327f5d59f827c1f75d140388de09b14b3",
}
CATEGORICAL = ["DriverBand", "VehicleBand", "VehPower", "VehBrand", "VehGas", "Area", "Region"]
NUMERIC = ["BonusMalus", "LogDensity"]


def aggregate_claims(frequency, severity):
    """Validate the policy/claim relationship before defining loss targets."""
    frequency, severity = frequency.copy(), severity.copy()
    if frequency.IDpol.isna().any() or severity.IDpol.isna().any():
        raise ValueError("Missing policy/claim ID")
    frequency["IDpol"] = frequency.IDpol.astype(str)
    severity["IDpol"] = severity.IDpol.astype(str)
    if frequency.IDpol.duplicated().any():
        raise ValueError("Duplicate policy ID")
    if not severity.IDpol.isin(frequency.IDpol).all():
        raise ValueError("Unmatched claim ID")
    if not (severity.ClaimAmount > 0).all() or not (frequency.Exposure > 0).all():
        raise ValueError("Losses and exposures must be positive")
    grouped = severity.groupby("IDpol").ClaimAmount.agg(["size", "sum"])
    n_claims = frequency.IDpol.map(grouped["size"]).fillna(0).to_numpy()
    if not np.array_equal(n_claims, frequency.ClaimNb.to_numpy()):
        raise ValueError("Policy count and linked severity count disagree")
    frequency["Loss"] = frequency.IDpol.map(grouped["sum"]).fillna(0).astype(float)
    frequency["MeanSeverity"] = np.divide(
        frequency.Loss, frequency.ClaimNb,
        out=np.full(len(frequency), np.nan), where=frequency.ClaimNb.to_numpy() > 0,
    )
    return frequency


def load_pricing():
    import rdata
    for name, digest in SOURCE_HASHES.items():
        if sha256(ROOT / "data/raw" / name) != digest:
            raise ValueError(f"Checksum mismatch: {name}")
    frequency = rdata.read_rda(ROOT / "data/raw/freMTPL2freq.rda")["freMTPL2freq"]
    severity = rdata.read_rda(ROOT / "data/raw/freMTPL2sev.rda")["freMTPL2sev"]
    return aggregate_claims(frequency, severity)


def features(frame):
    # Explicit feature allowlist; outcome columns never reach preprocessing.
    result = frame[["VehPower", "VehBrand", "VehGas", "Area", "Region", "BonusMalus"]].copy()
    result["DriverBand"] = pd.cut(frame.DrivAge, [-np.inf, 21, 26, 36, 51, 66, 81, np.inf], right=False).astype(str)
    result["VehicleBand"] = pd.cut(frame.VehAge, [-np.inf, 2, 6, 11, 21, np.inf], right=False).astype(str)
    result["LogDensity"] = np.log1p(frame.Density.astype(float))
    for name in CATEGORICAL:
        result[name] = result[name].astype(str)
    result = result[CATEGORICAL + NUMERIC]
    # R parsers may supply numpy.str_ headers mixed with Python str headers.
    result.columns = [str(column) for column in result.columns]
    return result


def make_preprocessor():
    return ColumnTransformer([
        ("categories", OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=True), CATEGORICAL),
        ("numeric", StandardScaler(), NUMERIC),
    ], sparse_threshold=1.0)


def metrics(frame, frequency, severity, power):
    exposure, count = frame.Exposure.to_numpy(), frame.ClaimNb.to_numpy()
    loss, positive = frame.Loss.to_numpy(), count > 0
    annual_loss = frequency * severity
    for value in (frequency, severity, annual_loss):
        if not (np.isfinite(value).all() and (value > 0).all()):
            raise ValueError("Invalid baseline predictions")
    return {
        "policies": len(frame),
        "exposure_years": float(exposure.sum()),
        "claims": int(count.sum()),
        "frequency_poisson_deviance": float(mean_poisson_deviance(count / exposure, frequency, sample_weight=exposure)),
        "severity_gamma_deviance": float(mean_gamma_deviance(frame.MeanSeverity.to_numpy()[positive], severity[positive], sample_weight=count[positive])),
        "pure_premium_tweedie_deviance": float(mean_tweedie_deviance(loss / exposure, annual_loss, sample_weight=exposure, power=power)),
        "frequency_observed_to_predicted": float(count.sum() / np.dot(exposure, frequency)),
        "loss_observed_to_predicted": float(loss.sum() / np.dot(exposure, annual_loss)),
        "annual_loss_weighted_mae_source_units": float(np.sum(np.abs(loss - exposure * annual_loss)) / exposure.sum()),
    }


def run_pricing_baseline():
    config = configuration()
    settings = config["pricing"]
    print("Pricing: read and reconcile pinned source files", flush=True)
    frame = load_pricing()
    assignments = np.array([
        split_name(key, "pricing", config["seed"], settings["train_fraction"], settings["development_fraction"])
        for key in frame.IDpol
    ])
    train = frame.loc[assignments == "train"].copy()
    development = frame.loc[assignments == "development"].copy()
    preprocessor = make_preprocessor()
    train_features, dev_features = features(train), features(development)
    design_train = preprocessor.fit_transform(train_features)
    design_dev = preprocessor.transform(dev_features)
    frequency = PoissonRegressor(alpha=settings["frequency_alpha"], max_iter=settings["glm_max_iter"], tol=settings["glm_tolerance"])
    severity = GammaRegressor(alpha=settings["severity_alpha"], max_iter=settings["glm_max_iter"], tol=settings["glm_tolerance"])
    positive = train.ClaimNb.to_numpy() > 0
    print(f"Pricing: fit GLMs on {len(train):,} training policies / {int(positive.sum()):,} positive policies", flush=True)
    with threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        frequency.fit(design_train, train.ClaimNb / train.Exposure, sample_weight=train.Exposure)
        severity.fit(design_train[positive], train.MeanSeverity.to_numpy()[positive], sample_weight=train.ClaimNb.to_numpy()[positive])
        predicted_frequency = frequency.predict(design_dev)
        predicted_severity = severity.predict(design_dev)
    constant_frequency = float(train.ClaimNb.sum() / train.Exposure.sum())
    constant_severity = float(train.Loss.sum() / train.ClaimNb.sum())
    model_metrics = metrics(development, predicted_frequency, predicted_severity, settings["primary_tweedie_power"])
    constant_metrics = metrics(development, np.full(len(development), constant_frequency), np.full(len(development), constant_severity), settings["primary_tweedie_power"])
    calibration = model_metrics["loss_observed_to_predicted"]
    unknown = {
        column: int((~dev_features[column].isin(train_features[column].unique())).sum())
        for column in CATEGORICAL
    }
    coefficient_rows = [
        {"feature": str(name), "frequency_log_coefficient": float(f), "severity_log_coefficient": float(s)}
        for name, f, s in zip(preprocessor.get_feature_names_out(), frequency.coef_, severity.coef_)
    ]
    report = {
        **provenance(),
        "source_sha256": SOURCE_HASHES,
        "status": "Baseline fitted on training policies; development-only metrics. No final-test prediction or metric produced.",
        "split_counts": {name: int((assignments == name).sum()) for name in ("train", "development", "test")},
        "split_sha256": split_digest(frame.IDpol, assignments),
        "design_columns": design_train.shape[1],
        "development_unknown_category_counts": unknown,
        "solver": "lbfgs",
        "convergence_warnings": 0,
        "frequency_iterations": int(frequency.n_iter_),
        "severity_iterations": int(severity.n_iter_),
        "constant_training_frequency": constant_frequency,
        "constant_training_severity_source_units": constant_severity,
        "development_constant_tariff": constant_metrics,
        "development_uncalibrated_glm": model_metrics,
        "development_loss_calibration_multiplier": calibration,
        "calibration_caveat": "Estimated on development. O/P=1 there after scaling is an identity, not validation evidence.",
        "intercepts": {"frequency": float(frequency.intercept_), "severity": float(severity.intercept_)},
        "coefficients": coefficient_rows,
        "exposure_above_one_preserved": int((frame.Exposure > 1).sum()),
        "no_claim_loss_clipping": True,
    }
    private = ROOT / "artifacts"
    private.mkdir(exist_ok=True)
    joblib.dump({"preprocessor": preprocessor, "frequency": frequency, "severity": severity,
                 "pure_premium_calibration": calibration, **provenance()}, private / "pricing_glm.joblib")
    np.savez_compressed(private / "pricing_development_predictions.npz",
                        policy_id=development.IDpol.to_numpy(dtype=str),
                        frequency=predicted_frequency, severity=predicted_severity)
    save_json(ROOT / "reports/pricing_baseline.json", report)
    print("Pricing: development metrics and private fitted artifacts saved", flush=True)
    return report
