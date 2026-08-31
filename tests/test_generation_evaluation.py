import unittest

from scripts.stage_05_retrieval.evaluate_generation import (
    aggregate_generation_scores,
    score_generation_case,
)
from scripts.stage_05_retrieval.evaluate_retrieval import EvaluationCase
from scripts.stage_05_retrieval.generate_grounded_answer import (
    Evidence,
    GroundedAnswer,
)


class GenerationEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.case = EvaluationCase(
            case_id="q1",
            question="What is the value?",
            answer_reference="£1m.",
            expected_pages=(1,),
            relevant_chunk_ids=frozenset({"doc-p0001-c001"}),
        )
        self.evidence = [
            Evidence(
                source_id="S1",
                chunk_id="doc-p0001-c001",
                title="Report",
                page_number=1,
                source_reference="Report",
                text="The value is £1m.",
            ),
            Evidence(
                source_id="S2",
                chunk_id="doc-p0002-c001",
                title="Report",
                page_number=2,
                source_reference="Report",
                text="Other evidence.",
            ),
        ]

    def test_relevant_citation_scores_hit_and_full_precision(self):
        scores = score_generation_case(
            self.case,
            GroundedAnswer("answered", "£1m.", ("S1",)),
            self.evidence,
        )
        self.assertEqual(scores["answered"], 1.0)
        self.assertEqual(scores["context_relevance_hit"], 1.0)
        self.assertEqual(scores["citation_relevance_hit"], 1.0)
        self.assertEqual(scores["citation_precision"], 1.0)

    def test_extra_irrelevant_citation_reduces_precision(self):
        scores = score_generation_case(
            self.case,
            GroundedAnswer("answered", "£1m.", ("S1", "S2")),
            self.evidence,
        )
        self.assertEqual(scores["citation_relevance_hit"], 1.0)
        self.assertEqual(scores["citation_precision"], 0.5)

    def test_positive_abstention_is_scored_as_unexpected(self):
        scores = score_generation_case(
            self.case,
            GroundedAnswer("abstained", "Not enough evidence.", ()),
            self.evidence,
        )
        self.assertEqual(scores["answered"], 0.0)
        self.assertEqual(scores["unexpected_abstention"], 1.0)
        self.assertEqual(scores["citation_relevance_hit"], 0.0)

    def test_aggregate_scores_are_macro_averages(self):
        aggregate = aggregate_generation_scores(
            [
                {
                    "answered": 1.0,
                    "unexpected_abstention": 0.0,
                    "context_relevance_hit": 1.0,
                    "citation_relevance_hit": 1.0,
                    "citation_precision": 1.0,
                },
                {
                    "answered": 0.0,
                    "unexpected_abstention": 1.0,
                    "context_relevance_hit": 1.0,
                    "citation_relevance_hit": 0.0,
                    "citation_precision": 0.0,
                },
            ]
        )
        self.assertEqual(aggregate["answered_rate"], 0.5)
        self.assertEqual(aggregate["citation_relevance_hit_rate"], 0.5)
        self.assertEqual(aggregate["citation_precision"], 0.5)


if __name__ == "__main__":
    unittest.main()
