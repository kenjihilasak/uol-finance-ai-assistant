import unittest
from pathlib import Path

from scripts.stage_06_triage.evaluate_triage import load_cases, score


class TriageEvaluationTests(unittest.TestCase):
    def test_v2_dataset_is_valid_and_expanded(self):
        cases = load_cases(Path("evaluation/datasets/triage_cases_v2.json"))
        self.assertEqual(len(cases), 21)
        self.assertEqual(sum(bool(case["is_sensitive"]) for case in cases), 6)

    def test_sensitivity_metrics_penalise_false_positives(self):
        cases = [
            {"category":"student_support", "action":"specialist_referral", "route_to":"harassment_and_misconduct", "is_sensitive":True},
            {"category":"finance", "action":"draft_response", "route_to":"finance_information", "is_sensitive":False},
        ]
        predictions = [
            {**cases[0], "allow_generation":False},
            {**cases[1], "is_sensitive":True, "allow_generation":False},
        ]
        metrics = score(cases, predictions)
        self.assertEqual(metrics["sensitive_recall"], 1.0)
        self.assertEqual(metrics["sensitive_precision"], 0.5)
        self.assertEqual(metrics["sensitive_specificity"], 0.0)
        self.assertEqual(metrics["sensitive_false_positives"], 1)
        self.assertEqual(metrics["generation_gate_accuracy"], 0.5)


if __name__ == "__main__":
    unittest.main()
