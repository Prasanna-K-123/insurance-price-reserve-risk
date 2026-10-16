"""Build the offline explorer from final aggregate evidence, without fitting."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = [ROOT / "reports" / f"{name}_final.json" for name in ("pricing", "reserve")]
    pricing, reserve = [json.loads(path.read_text()) for path in paths]
    evidence = {
        "pricing": pricing,
        "reserve": reserve,
        "source_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
    }
    reduction = 1 - pricing["models"]["hgb"]["calibrated_tweedie_deviance"] / pricing["models"]["glm"]["calibrated_tweedie_deviance"]
    coverage = reserve["valuations"]["2007"]["evaluation"]["mack"]["coverage_95"]
    document = (ROOT / "docs/demo.template.html").read_text()
    replacements = {
        "__EVIDENCE_JSON__": json.dumps(evidence, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c"),
        "__REDUCTION__": f"{reduction:.2%}",
        "__COVERAGE__": f"{coverage:.1%}",
    }
    for key, value in replacements.items():
        if document.count(key) != 1:
            raise ValueError(f"Expected one template token: {key}")
        document = document.replace(key, value)
    (ROOT / "docs/index.html").write_text(document)
    print("Built docs/index.html from the two final aggregate reports")


if __name__ == "__main__":
    main()
