import unittest
from pathlib import Path

from scripts.stage_05_retrieval.evaluate_abstention import (
    aggregate_abstention_scores,
    load_abstention_dataset,
    score_abstention,
)
from scripts.stage_05_retrieval.generate_grounded_answer import GroundedAnswer


class AbstentionEvaluationTests(unittest.TestCase):
    def test_abstention_scores_as_correct_and_citation_free(self):
        scores = score_abstention(
            GroundedAnswer("abstained", "Not enough evidence.", ())
        )
        self.assertEqual(scores["correct_abstention"], 1.0)
        self.assertEqual(scores["false_answer"], 0.0)
        self.assertEqual(scores["citation_free_abstention"], 1.0)

    def test_answer_on_negative_question_scores_as_false_answer(self):
        scores = score_abstention(
            GroundedAnswer("answered", "Unsupported answer.", ("S1",))
        )
        self.assertEqual(scores["correct_abstention"], 0.0)
        self.assertEqual(scores["false_answer"], 1.0)

    def test_aggregate_rates_are_macro_averages(self):
        aggregate = aggregate_abstention_scores(
            [
                {
                    "correct_abstention": 1.0,
                    "false_answer": 0.0,
                    "citation_free_abstention": 1.0,
                },
                {
                    "correct_abstention": 0.0,
                    "false_answer": 1.0,
                    "citation_free_abstention": 0.0,
                },
            ]
        )
        self.assertEqual(aggregate["correct_abstention_rate"], 0.5)
        self.assertEqual(aggregate["false_answer_rate"], 0.5)

    def test_tracked_dataset_contains_ten_scope_verified_questions(self):
        dataset = load_abstention_dataset(
            Path("evaluation/datasets/abstention_questions_v1.json")
        )
        self.assertEqual(dataset.review["status"], "scope_verified")
        self.assertEqual(len(dataset.cases), 10)


if __name__ == "__main__":
    unittest.main()
