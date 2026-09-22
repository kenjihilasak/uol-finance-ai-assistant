import unittest
import json
from tempfile import TemporaryDirectory
from pathlib import Path

from scripts.stage_06_triage.evaluate_triage import load_cases, score
from scripts.stage_06_triage.schemas import Category


class TriageEvaluationTests(unittest.TestCase):
    def test_v2_dataset_is_valid_and_expanded(self):
        cases = load_cases(Path("evaluation/datasets/triage_cases_v2.json"))
        self.assertEqual(len(cases), 21)
        self.assertEqual(sum(bool(case["is_sensitive"]) for case in cases), 6)
        self.assertEqual(
            {category.value for category in Category},
            {"finance", "finance_operations", "student_admin", "digital_learning", "unsupported"},
        )
        self.assertNotIn("student_support", {case["category"] for case in cases})
        self.assertNotIn("unclear", {case["category"] for case in cases})

    def test_dataset_rejects_removed_category(self):
        payload = {
            "schema_version": "1.0.0",
            "cases": [{
                "id": "legacy-category",
                "enquiry": "Synthetic enquiry",
                "category": "student_support",
                "is_sensitive": True,
                "action": "specialist_referral",
                "route_to": "harassment_and_misconduct",
            }],
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Invalid controlled value"):
                load_cases(path)

    def test_sensitivity_metrics_penalise_false_positives(self):
        cases = [
            {"category":"unsupported", "action":"specialist_referral", "route_to":"harassment_and_misconduct", "is_sensitive":True},
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
