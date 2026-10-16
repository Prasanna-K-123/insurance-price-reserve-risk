import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insurance_risk.challengers import run_pricing_challenger
from insurance_risk.evaluation import run_reserve_challenger, freeze_models

if __name__ == "__main__":
    run_pricing_challenger()
    run_reserve_challenger()
    freeze_models()
