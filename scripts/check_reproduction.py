"""Compare regenerated analysis outputs with the saved reference SHA256 values."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = json.loads((ROOT / "reports/reproduction_verification.json").read_text())
    failures = []
    for name, reference in evidence["output_comparisons"].items():
        path = ROOT / "reports" / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        matches = actual == reference["expected_sha256"]
        print(f"{'MATCH' if matches else 'MISMATCH'} {name}")
        if not matches:
            failures.append(name)
    if failures:
        print("Output mismatch: preserve the original evidence and investigate the environment/input difference.", file=sys.stderr)
        return 1
    print("All ten analysis outputs match the saved reference hashes. This compares files; it does not prove which commands were run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
