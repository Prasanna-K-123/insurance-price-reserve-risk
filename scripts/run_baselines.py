"""Fit the frozen actuarial baselines; leave final-test outcomes unscored."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insurance_risk.pricing import run_pricing_baseline
from insurance_risk.reserving import run_reserve_baseline


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["both", "pricing", "reserving"], default="both")
    args = parser.parse_args()
    if args.case in ("both", "pricing"):
        run_pricing_baseline()
    if args.case in ("both", "reserving"):
        run_reserve_baseline()
