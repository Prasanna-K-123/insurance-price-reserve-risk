import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import GammaRegressor, PoissonRegressor
from threadpoolctl import threadpool_limits

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insurance_risk.pricing import aggregate_claims, features, make_preprocessor
from insurance_risk.reserving import interval_score, mack


def raa_triangle():
    # Numerical reference: RAA example in the authors' ChainLadder vignette.
    # https://mages.github.io/ChainLadder/articles/ChainLadder.html
    rows = [
        [5012, 8269, 10907, 11805, 13539, 16181, 18009, 18608, 18662, 18834],
        [106, 4285, 5396, 10666, 13782, 15599, 15496, 16169, 16704],
        [3410, 8992, 13873, 16141, 18735, 22214, 22863, 23466],
        [5655, 11555, 15766, 21266, 23425, 26083, 27067],
        [1092, 9565, 15836, 22169, 25955, 26180],
        [1513, 6445, 11702, 12935, 15852],
        [557, 4020, 10946, 12314], [1351, 6947, 13112], [3133, 5395], [2063],
    ]
    return np.array([row + [np.nan] * (10 - len(row)) for row in rows])


class BaselineTests(unittest.TestCase):
    def test_mack_matches_published_numerical_reference(self):
        fit = mack(raa_triangle())
        self.assertAlmostEqual(fit["total_remaining_paid"], 52135.23, delta=0.005)
        self.assertAlmostEqual(fit["total_standard_error"], 26909.01, delta=0.005)
        # Treating origin-year parameter errors as independent understates risk.
        independent = fit["process_variance_by_origin"].sum() + np.trace(fit["parameter_covariance"])
        self.assertGreater(fit["total_standard_error"]**2, independent)

    def test_currency_scaling_preserves_normalized_results(self):
        first, scaled = mack(raa_triangle()), mack(raa_triangle() * 1000)
        np.testing.assert_allclose(first["factors"], scaled["factors"], rtol=1e-13)
        self.assertAlmostEqual(scaled["total_standard_error"] / first["total_standard_error"], 1000, places=8)
        self.assertAlmostEqual(scaled["total_remaining_paid"] / first["total_remaining_paid"], 1000, places=8)
        score = interval_score(12, 7, 10, 0.05)
        self.assertAlmostEqual(interval_score(12000, 7000, 10000, 0.05) / 1000, score)

    def test_frequency_exposure_weighting_recovers_analytic_rate(self):
        exposure, count = np.array([0.1, 0.5, 1, 2.0]), np.array([0, 1, 1, 3])
        with threadpool_limits(limits=1):
            fit = PoissonRegressor(alpha=0, max_iter=1000, tol=1e-10).fit(
                np.zeros((4, 1)), count / exposure, sample_weight=exposure)
        np.testing.assert_allclose(fit.predict(np.zeros((4, 1))), count.sum() / exposure.sum(), rtol=1e-8)

    def test_count_weighted_severity_equals_individual_claim_likelihood(self):
        x, count = np.array([[0.0], [1.0], [2.0]]), np.array([2, 1, 3])
        individual = np.array([1, 3, 4, 5, 7, 9], dtype=float)
        with threadpool_limits(limits=1):
            grouped = GammaRegressor(alpha=0.01, max_iter=1000, tol=1e-10).fit(x, [2, 4, 7], sample_weight=count)
            expanded = GammaRegressor(alpha=0.01, max_iter=1000, tol=1e-10).fit(np.repeat(x, count, axis=0), individual)
        np.testing.assert_allclose(grouped.predict(x), expanded.predict(x), rtol=1e-8)

    def test_claim_links_preserve_zero_loss_and_reject_unmatched_claim(self):
        freq = pd.DataFrame({"IDpol": ["001", "002"], "ClaimNb": [2, 0], "Exposure": [0.5, 2.01]})
        sev = pd.DataFrame({"IDpol": ["001", "001"], "ClaimAmount": [10.0, 30.0]})
        data = aggregate_claims(freq, sev)
        np.testing.assert_equal(data.Loss.to_numpy(), [40, 0])
        self.assertEqual(data.IDpol.tolist(), ["001", "002"])
        self.assertEqual(data.Exposure.iloc[1], 2.01)
        self.assertEqual(data.MeanSeverity.iloc[0], 20)
        self.assertTrue(np.isnan(data.MeanSeverity.iloc[1]))
        sev.loc[0, "IDpol"] = "003"
        with self.assertRaisesRegex(ValueError, "Unmatched"):
            aggregate_claims(freq, sev)

    def test_pricing_features_exclude_targets_and_exposure(self):
        data = pd.DataFrame({"VehPower": [4], "VehBrand": ["B1"], "VehGas": ["Diesel"],
            "Area": ["A"], "Region": ["R1"], "BonusMalus": [50], "DrivAge": [20],
            "VehAge": [1], "Density": [100], "Loss": [10], "ClaimNb": [1], "Exposure": [2.01]})
        data.columns = pd.Index([np.str_(column) for column in data.columns], dtype=object)
        original = features(data)
        self.assertTrue(all(type(column) is str for column in original.columns))
        make_preprocessor().fit_transform(original)
        data["Loss"], data["ClaimNb"], data["Exposure"] = 1e12, 500, 0.0001
        pd.testing.assert_frame_equal(original, features(data))


if __name__ == "__main__":
    unittest.main()
