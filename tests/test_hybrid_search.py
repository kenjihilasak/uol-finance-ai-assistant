import unittest

from scripts.stage_05_retrieval.hybrid_search import (
    SELECT_FIELDS,
    escape_odata_string,
    hybrid_search,
    validated_query,
    validated_vector,
    validate_limits,
)


class FakeSearchClient:
    def __init__(self, results):
        self.results = results
        self.search_args = None

    def search(self, **kwargs):
        self.search_args = kwargs
        return self.results


class HybridSearchTests(unittest.TestCase):
    def test_query_is_trimmed_and_empty_query_is_rejected(self):
        self.assertEqual(validated_query("  total income  "), "total income")
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            validated_query("   ")

    def test_retrieval_limits_are_validated(self):
        validate_limits(5, 50)
        with self.assertRaisesRegex(ValueError, "top must be"):
            validate_limits(0, 50)
        with self.assertRaisesRegex(ValueError, "at least top"):
            validate_limits(10, 5)

    def test_embedding_shape_and_values_are_validated(self):
        self.assertEqual(validated_vector([1, 2.5], 2), [1.0, 2.5])
        with self.assertRaisesRegex(RuntimeError, "exactly 2"):
            validated_vector([1.0], 2)
        with self.assertRaisesRegex(RuntimeError, "finite"):
            validated_vector([1.0, float("nan")], 2)

    def test_hybrid_query_combines_text_and_vector_without_returning_vector(self):
        client = FakeSearchClient(
            [
                {
                    "@search.score": 0.0325,
                    "chunk_id": "doc-p010-c01",
                    "document_id": "doc",
                    "text": "Total income was reported.",
                    "source_title": "Annual report",
                    "institution": "University",
                    "page_number": 10,
                    "document_date": "2025-07-31T00:00:00Z",
                    "source_reference": "Annual report, p. 10",
                    "source_url": None,
                    "status": "approved",
                    "content_vector": [0.1, 0.2],
                }
            ]
        )

        results = hybrid_search(
            client,
            "What was total income?",
            [0.1, 0.2],
            top=1,
            vector_candidates=10,
            document_id="annual'report",
        )

        self.assertEqual(client.search_args["search_text"], "What was total income?")
        self.assertEqual(len(client.search_args["vector_queries"]), 1)
        self.assertEqual(
            client.search_args["filter"], "document_id eq 'annual''report'"
        )
        self.assertNotIn("content_vector", SELECT_FIELDS)
        self.assertNotIn("content_vector", results[0])
        self.assertEqual(results[0]["rank"], 1)
        self.assertEqual(results[0]["score"], 0.0325)

    def test_odata_single_quote_is_escaped(self):
        self.assertEqual(escape_odata_string("a'b"), "a''b")


if __name__ == "__main__":
    unittest.main()
