"""Financial data-boundary tests: leakage, missing history and net-loss signs."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reserve_valuation import FIELDS, valuation_view


def row(entity, year, lag, paid):
    return {"GRCODE": entity, "AccidentYear": year, "DevelopmentYear": year + lag - 1,
            "DevelopmentLag": lag, "CumPaidLoss": paid, "PostedReserves2007": 999999}


class ValuationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.history = [row("A", 2000, 1, 10), row("A", 2000, 2, 15), row("A", 2001, 1, 8)]

    def view(self, rows):
        return valuation_view(rows, valuation_year=2001, first_accident_year=2000, max_lag=2)

    def test_future_values_absence_and_future_only_entities_cannot_change_view(self):
        expected = self.view(self.history)
        # Even an unusable future loss must not be inspected by the boundary.
        future = [row("A", 2001, 2, "UNSEEN"), row("B", 2001, 2, -1e12)]
        self.assertEqual(expected, self.view(self.history + future))
        altered = copy.deepcopy(self.history)
        for record in altered:
            record["PostedReserves2007"] = "FUTURE ESTIMATE"
        self.assertEqual(expected, self.view(altered + list(reversed(future))))
        self.assertEqual(set(expected[0][0]), set(FIELDS))

    def test_missing_historical_cell_cannot_be_replaced_by_future_followup(self):
        future = [row("A", 2001, 2, 20)]
        _, ledger = self.view(self.history[:-1] + future)
        self.assertFalse(ledger[0]["eligible_observed_triangle"])
        self.assertEqual(ledger[0]["missing_cells"], 1)
        self.assertIsNone(ledger[0]["nonnegative_increments"])

    def test_negative_net_losses_are_preserved_and_flagged_without_future_filter(self):
        history = [row("A", 2000, 1, 10), row("A", 2000, 2, 7), row("A", 2001, 1, -2)]
        records, ledger = self.view(history)
        self.assertEqual([record["CumPaidLoss"] for record in records], [10, 7, -2])
        self.assertTrue(ledger[0]["eligible_observed_triangle"])
        self.assertEqual(ledger[0]["negative_increment_cells"], 2)
        self.assertEqual(ledger[0]["negative_cumulative_cells"], 1)
        self.assertFalse(ledger[0]["nonnegative_increments"])

    def test_duplicate_or_misdated_observation_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.view(self.history + [self.history[0]])
        wrong = copy.deepcopy(self.history)
        wrong[0]["DevelopmentYear"] = 1999
        with self.assertRaisesRegex(ValueError, "calendar identity"):
            self.view(wrong)

    def test_gap_does_not_invent_increment_from_zero(self):
        _, ledger = self.view([row("A", 2000, 2, 15), row("A", 2001, 1, 8)])
        self.assertEqual(ledger[0]["known_increment_cells"], 1)
        self.assertFalse(ledger[0]["eligible_observed_triangle"])


if __name__ == "__main__":
    unittest.main()
