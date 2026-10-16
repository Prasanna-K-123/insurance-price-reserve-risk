import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.metrics import mean_tweedie_deviance

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from insurance_risk.challengers import fit_tree_design, lognormal_parameters, simulate_remaining_paid, tree_design
from insurance_risk.common import configuration, split_name
from insurance_risk.evaluation import paired_bootstrap, reserve_forecasts, tweedie_deviance_rows, verify_freeze


class ChallengerTests(unittest.TestCase):
    def test_lognormal_conversion_preserves_specified_moments(self):
        mean, variance = np.array([1.1, 25, 1000]), np.array([0, 50, 10000])
        mu, sd = lognormal_parameters(mean, variance)
        np.testing.assert_allclose(np.exp(mu+sd*sd/2), mean, rtol=1e-13)
        np.testing.assert_allclose(np.expm1(sd*sd)*np.exp(2*mu+sd*sd), variance, rtol=1e-13)

    def test_simulation_shared_factor_matches_total_variance_and_keeps_net_recoveries(self):
        fit = {"latest": np.array([100., 200.]), "latest_ages": np.array([0,0]),
            "factors": np.array([1.1]), "variance": np.array([2.]), "denominators": np.array([100.])}
        sample = simulate_remaining_paid(fit, 100000, 17)
        # Law of total variance: process 2*(100+200), shared factor .02*(100+200)^2.
        self.assertAlmostEqual(sample.mean(), 30, delta=1.0)
        self.assertAlmostEqual(sample.var(ddof=1), 2400, delta=100)
        self.assertTrue((sample < 0).any())
        scaled = {**fit, "latest": fit["latest"]*1000,
            "variance": fit["variance"]*1000, "denominators": fit["denominators"]*1000}
        np.testing.assert_allclose(simulate_remaining_paid(scaled, 100000, 17)/1000, sample, atol=1e-9)

    def test_zero_variance_transition_is_deterministic(self):
        fit = {"latest": np.array([100., 200.]), "latest_ages": np.array([0,1]),
            "factors": np.array([1.2]), "variance": np.array([0.]), "denominators": np.array([100.])}
        np.testing.assert_allclose(simulate_remaining_paid(fit, 100, 1), 20, atol=1e-12)

    def test_training_vocabulary_is_unchanged_by_unknown_category_or_outcome(self):
        train = pd.DataFrame({"VehPower":[4,5],"VehBrand":["A","B"],"VehGas":["D","G"],
            "Area":["A","B"],"Region":["R1","R2"],"DrivAge":[22,40],"VehAge":[1,5],
            "BonusMalus":[50,100],"Density":[100,500]})
        encoder, original = fit_tree_design(train)
        vocabulary = [values.copy() for values in encoder.categories_]
        other = train.copy(); other.loc[0,"VehBrand"] = "UNKNOWN"; other["Loss"] = 1e15
        transformed = tree_design(other, encoder)
        self.assertTrue(np.isnan(transformed[0,1]))
        for before, after in zip(vocabulary, encoder.categories_):
            np.testing.assert_array_equal(before,after)
        np.testing.assert_array_equal(tree_design(train, encoder), original)

    def test_tweedie_weighted_metric_matches_reference_and_pairing_cancels(self):
        actual = np.array([0., .5, 10, 1000]); predicted = np.array([.2, 1, 20, 600]); exposure = np.array([.01, .2, 1, 2.01])
        rows = tweedie_deviance_rows(actual,predicted)
        self.assertAlmostEqual(np.average(rows,weights=exposure), mean_tweedie_deviance(actual,predicted,power=1.5,sample_weight=exposure), places=10)
        paired = paired_bootstrap(rows-rows, exposure, 100, 3)
        self.assertEqual(paired["estimate"],0)
        self.assertEqual(paired["ci95_percentile"],[0,0])

    def test_predictions_invariant_to_changed_or_removed_future_loss_cells(self):
        config = copy.deepcopy(configuration())
        config["reserving"].update(first_accident_year=2000,last_accident_year=2003,maximum_development_lag=4,challenger_simulations=128)
        values = [[10,15,20,25],[8,14,19],[12,18],[9]]
        rows = [{"GRCODE":"A","AccidentYear":2000+i,"DevelopmentLag":j+1,
                 "DevelopmentYear":2000+i+j,"CumPaidLoss":value} for i,origin in enumerate(values) for j,value in enumerate(origin)]
        group = split_name("A","reserving",config["seed"],.5)
        expected = reserve_forecasts(rows,2003,config,group)
        future = [{"GRCODE":"A","AccidentYear":2001,"DevelopmentLag":4,"DevelopmentYear":2004,"CumPaidLoss":"UNSEEN"},
                  {"GRCODE":"FUTURE ONLY","DevelopmentYear":2004}]
        self.assertEqual(expected,reserve_forecasts(rows+future,2003,config,group))

    def test_final_evaluation_rejects_changed_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'reports').mkdir();(root/'artifacts').mkdir()
            model=root/'artifacts/model.bin';model.write_bytes(b'original model')
            manifest={"config_sha256":"config","protocol_sha256":"protocol","computational_hashes":{"code":"hash"},
                "artifacts_sha256":{"model.bin":hashlib.sha256(model.read_bytes()).hexdigest()}}
            (root/'reports/model_freeze.json').write_text(json.dumps(manifest))
            with patch('insurance_risk.evaluation.ROOT',root), patch('insurance_risk.evaluation.provenance',return_value=manifest), patch('insurance_risk.evaluation.computational_hashes',return_value={"code":"hash"}):
                verify_freeze()
                model.write_bytes(b'changed model')
                with self.assertRaisesRegex(ValueError,"Frozen artifact changed"):
                    verify_freeze()


if __name__ == '__main__':
    unittest.main()
