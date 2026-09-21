import tempfile
import unittest
from pathlib import Path

from scripts.stage_05_retrieval.evaluate_retrieval import (
    EvaluationCase,
    EvaluationDataset,
    load_dataset,
    score_rankings,
    validate_k_values,
)


class RetrievalEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.dataset = EvaluationDataset(
            dataset_id="test-v1",
            document_id="doc",
            review={"status": "source_verified"},
            cases=(
                EvaluationCase(
                    case_id="q1",
                    question="Question one?",
                    answer_reference="Answer one.",
                    expected_pages=(1,),
                    relevant_chunk_ids=frozenset({"doc-p0001-c001"}),
                ),
                EvaluationCase(
                    case_id="q2",
                    question="Question two?",
                    answer_reference="Answer two.",
                    expected_pages=(2,),
                    relevant_chunk_ids=frozenset({"doc-p0002-c001"}),
                ),
            ),
        )

    def test_scores_question_level_recall_and_mrr(self):
        scores = score_rankings(
            self.dataset,
            {
                "q1": ["doc-p0001-c001", "other"],
                "q2": ["other", "doc-p0002-c001"],
            },
            (1, 2),
        )
        self.assertEqual(scores["aggregate"]["recall@1"], 0.5)
        self.assertEqual(scores["aggregate"]["recall@2"], 1.0)
        self.assertEqual(scores["aggregate"]["mrr@2"], 0.75)

    def test_missing_relevant_chunk_scores_zero(self):
        scores = score_rankings(
            self.dataset,
            {"q1": ["other"], "q2": ["another"]},
            (1,),
        )
        self.assertEqual(scores["aggregate"]["recall@1"], 0.0)
        self.assertEqual(scores["aggregate"]["mrr@1"], 0.0)

    def test_k_values_are_sorted_deduplicated_and_bounded(self):
        self.assertEqual(validate_k_values((5, 1, 3, 3)), (1, 3, 5))
        with self.assertRaisesRegex(ValueError, "between"):
            validate_k_values((0, 1))

    def test_tracked_dataset_is_valid_and_source_verified(self):
        dataset = load_dataset(
            Path("evaluation/datasets/retrieval_questions_v1.json")
        )
        self.assertEqual(dataset.dataset_id, "uol-finance-retrieval-v1")
        self.assertEqual(dataset.review["status"], "source_verified")
        self.assertEqual(len(dataset.cases), 10)

    def test_student_admin_dataset_is_valid_and_source_verified(self):
        dataset = load_dataset(
            Path(
                "evaluation/datasets/"
                "student_admin_retrieval_questions_v1.json"
            )
        )
        self.assertEqual(dataset.dataset_id, "uol-student-admin-retrieval-v1")
        self.assertEqual(dataset.review["status"], "source_verified")
        self.assertEqual(len(dataset.cases), 10)

    def test_category_datasets_are_valid_and_source_verified(self):
        expected = {
            "finance_operations_retrieval_questions_v1.json": (
                "finance_operations", 12, 4
            ),
            "digital_learning_retrieval_questions_v1.json": (
                "digital_learning", 12, 2
            ),
        }
        for filename, (category, questions, documents) in expected.items():
            with self.subTest(filename=filename):
                dataset = load_dataset(Path("evaluation/datasets") / filename)
                self.assertEqual(dataset.category, category)
                self.assertEqual(len(dataset.cases), questions)
                self.assertEqual(len(dataset.document_ids), documents)
                self.assertEqual(dataset.review["status"], "source_verified")

    def test_category_scoped_dataset_accepts_multiple_documents(self):
        payload = """{
          "schema_version": "1.1.0",
          "dataset_id": "category-test",
          "scope": {
            "category": "digital_learning",
            "document_ids": ["doc-one", "doc-two"]
          },
          "review": {"status": "source_verified"},
          "questions": [{
            "id": "q1",
            "question": "Where do I get help?",
            "answer_reference": "Contact support.",
            "expected_pages": [1],
            "relevant_chunk_ids": ["doc-two-p0001-c001"]
          }]
        }"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.json"
            path.write_text(payload, encoding="utf-8")
            dataset = load_dataset(path)
        self.assertIsNone(dataset.document_id)
        self.assertEqual(dataset.category, "digital_learning")
        self.assertEqual(dataset.document_ids, ("doc-one", "doc-two"))

    def test_category_scoped_dataset_rejects_out_of_scope_chunk(self):
        payload = """{
          "schema_version": "1.1.0",
          "dataset_id": "category-test",
          "scope": {"category": "finance", "document_ids": ["allowed"]},
          "review": {"status": "source_verified"},
          "questions": [{
            "id": "q1", "question": "What is reported?",
            "answer_reference": "A fact.", "expected_pages": [1],
            "relevant_chunk_ids": ["other-p0001-c001"]
          }]
        }"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.json"
            path.write_text(payload, encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "outside its scope"):
                load_dataset(path)

    def test_dataset_rejects_unverified_review(self):
        payload = """{
          "schema_version": "1.0.0",
          "dataset_id": "test",
          "document_id": "doc",
          "review": {"status": "draft"},
          "questions": []
        }"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.json"
            path.write_text(payload, encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "source_verified"):
                load_dataset(path)


if __name__ == "__main__":
    unittest.main()
