import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insurance_risk.evaluation import run_final_evaluation

if __name__ == "__main__":
    run_final_evaluation()
