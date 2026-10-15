"""Download checksum-pinned research inputs and write aggregate audit evidence.

Raw files stay local. This script does not fit models or select on test outcomes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd
import rdata

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    {
        "name": "freMTPL2freq.rda",
        "url": "https://raw.githubusercontent.com/dutangc/CASdatasets/master/data/freMTPL2freq.rda",
        "sha256": "82c8598513d9fa78226b6c7d271a9940eca4b8083e9e32320a75d377bdfe15a3",
        "git_blob_sha": "d4c7003833347aaf67e68c50b86a565614616a97",
    },
    {
        "name": "freMTPL2sev.rda",
        "url": "https://raw.githubusercontent.com/dutangc/CASdatasets/master/data/freMTPL2sev.rda",
        "sha256": "78e6e5016ae046603b37e88ff8ad8ca327f5d59f827c1f75d140388de09b14b3",
        "git_blob_sha": "811e8c1d3180615ddc78414947b20f2c110f2a67",
    },
    {
        "name": "ppauto_pos98_07.csv",
        "url": "https://www.casact.org/sites/default/files/2026-03/ppauto_pos98-07%20%281%29.csv",
        "sha256": "6e838f1e44c67218133ef1c8e28ca2b34b9f21ba4ee94de408c412638f798d96",
    },
]


def acquire() -> list[dict]:
    raw = ROOT / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest = []
    for source in SOURCES:
        path = raw / source["name"]
        if not path.exists():
            with urlopen(source["url"], timeout=45) as response:
                content = response.read()
            if hashlib.sha256(content).hexdigest() != source["sha256"]:
                raise ValueError(f"Upstream checksum changed: {source['name']}")
            path.write_bytes(content)
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != source["sha256"]:
            raise ValueError(f"Local checksum mismatch: {source['name']}")
        if "git_blob_sha" in source:
            header = b"blob " + str(len(content)).encode() + b"\0"
            if hashlib.sha1(header + content).hexdigest() != source["git_blob_sha"]:
                raise ValueError(f"Git object mismatch: {source['name']}")
        manifest.append({**source, "bytes": len(content)})
    return manifest


def frame_audit(frame: pd.DataFrame) -> dict:
    return {
        "rows": len(frame), "columns": list(frame.columns),
        "missing": {str(k): int(v) for k, v in frame.isna().sum().items()},
    }


def pricing_audit(frequency: pd.DataFrame, severity: pd.DataFrame) -> dict:
    if frequency.IDpol.isna().any() or frequency.IDpol.duplicated().any():
        raise ValueError("Policy IDs must be present and unique before joining claims")
    counts = severity.groupby("IDpol", dropna=False, observed=True).size().rename("severity_rows")
    linked = frequency.set_index("IDpol")["ClaimNb"].to_frame().join(counts)
    linked["severity_rows"] = linked["severity_rows"].fillna(0).astype(int)
    table = linked.groupby(["ClaimNb", "severity_rows"], dropna=False).size()
    return {
        "frequency": frame_audit(frequency), "severity": frame_audit(severity),
        "policy_id_duplicates": int(frequency.IDpol.duplicated().sum()),
        "unmatched_severity_rows": int((~severity.IDpol.isin(frequency.IDpol)).sum()),
        "exposure_min": float(frequency.Exposure.min()),
        "exposure_max": float(frequency.Exposure.max()),
        "exposure_nonpositive": int((frequency.Exposure <= 0).sum()),
        "exposure_above_one": int((frequency.Exposure > 1).sum()),
        "nonpositive_claim_amounts": int((severity.ClaimAmount <= 0).sum()),
        "claim_count_total": float(frequency.ClaimNb.sum()),
        "count_mismatch_policies": int((linked.ClaimNb != linked.severity_rows).sum()),
        "count_reconciliation": [
            {"reported_claims": float(k[0]), "linked_severity_rows": int(k[1]), "policies": int(v)}
            for k, v in table.items()
        ],
        "noninteger_claim_counts": int((frequency.ClaimNb % 1 != 0).sum()),
        "nonfinite_numeric_values": {
            str(c): int((~np.isfinite(frequency[c].to_numpy(dtype=float))).sum())
            for c in frequency.select_dtypes(include="number")
        },
    }


def reserve_audit(frame: pd.DataFrame) -> dict:
    keys = ["GRCODE", "AccidentYear", "DevelopmentLag"]
    if frame.duplicated(keys).any():
        raise ValueError("Duplicate insurer/accident-year/development keys")
    ordered = frame.sort_values(keys)
    increments = ordered.groupby(["GRCODE", "AccidentYear"]).CumPaidLoss.diff()
    increments = increments.fillna(ordered.CumPaidLoss)
    sizes = frame.groupby("GRCODE").size()
    return {
        **frame_audit(frame),
        "entities": int(frame.GRCODE.nunique()),
        "entity_row_count_distribution": {str(k): int(v) for k, v in sizes.value_counts().sort_index().items()},
        "complete_100_cell_entities": int((sizes == 100).sum()),
        "duplicate_keys": int(frame.duplicated(keys).sum()),
        "calendar_identity_errors": int((frame.DevelopmentYear != frame.AccidentYear + frame.DevelopmentLag - 1).sum()),
        "accident_years": sorted(int(x) for x in frame.AccidentYear.unique()),
        "development_lags": sorted(int(x) for x in frame.DevelopmentLag.unique()),
        "negative_cumulative_paid_rows": int((frame.CumPaidLoss < 0).sum()),
        "negative_incremental_paid_rows": int((increments < 0).sum()),
        "zero_net_premium_rows": int((frame.EarnedPremNet == 0).sum()),
        "negative_net_premium_rows": int((frame.EarnedPremNet < 0).sum()),
        "premium_variation_within_accident_year": int((frame.groupby(["GRCODE", "AccidentYear"]).EarnedPremNet.nunique() > 1).sum()),
        "limitation": "Complete-panel availability is retrospective; it must not be described as a prospective eligibility filter. Negative net paid increments may reflect recoveries/corrections and are not silently clipped.",
    }


def main() -> None:
    manifest = acquire()
    raw = ROOT / "data" / "raw"
    print("Parsing frequency data", flush=True)
    frequency = rdata.read_rda(raw / "freMTPL2freq.rda")["freMTPL2freq"]
    print("Parsing severity data", flush=True)
    severity = rdata.read_rda(raw / "freMTPL2sev.rda")["freMTPL2sev"]
    reserve = pd.read_csv(raw / "ppauto_pos98_07.csv")
    result = {"sources": manifest, "pricing": pricing_audit(frequency, severity), "reserving": reserve_audit(reserve)}
    destination = ROOT / "reports" / "data_audit.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(destination, flush=True)


if __name__ == "__main__":
    main()
