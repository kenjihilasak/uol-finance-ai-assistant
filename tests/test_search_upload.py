from __future__ import annotations

import unittest

from scripts.stage_04_search_index.create_index import (
    VECTOR_PROFILE_NAME,
    build_search_index,
)
from scripts.stage_04_search_index.upload_documents import search_document


def example_record() -> dict[str, object]:
    return {
        "schema_version": "2.0.0",
        "chunk_id": "report-p0008-c001",
        "document_id": "report",
        "text": "Revenue increased.",
        "embedding_text": "Document: Report\n\nRevenue increased.",
        "source_title": "Report",
        "institution": "Example University",
        "source_reference": "Provided by document owner",
        "source_url": None,
        "status": "current",
        "page_number": 8,
        "document_date": "2025-07-31",
        "source_sha256": "source-hash",
        "text_sha256": "text-hash",
        "embedding_text_sha256": "embedding-text-hash",
        "page_range": {"start": 8, "end": 8},
        "character_range": {"start": 0, "end": 18},
        "content_vector": [0.25, -0.5, 0],
    }


class SearchDocumentMappingTests(unittest.TestCase):
    def test_maps_only_index_fields_and_root_deployment(self) -> None:
        document = search_document(
            example_record(),
            embedding_deployment="text-embedding-3-small",
            vector_dimensions=3,
        )

        self.assertNotIn("schema_version", document)
        self.assertNotIn("source_url", document)
        self.assertEqual(
            document["embedding_deployment"], "text-embedding-3-small"
        )
        self.assertEqual(document["document_date"], "2025-07-31T00:00:00Z")
        self.assertEqual(document["page_range"], {"start": 8, "end": 8})
        self.assertEqual(document["content_vector"], [0.25, -0.5, 0.0])

    def test_preserves_non_null_source_url(self) -> None:
        record = example_record()
        record["source_url"] = "https://example.org/report"

        document = search_document(record, "embedding-model", 3)

        self.assertEqual(document["source_url"], "https://example.org/report")

    def test_rejects_wrong_vector_dimensions(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "exactly 4"):
            search_document(example_record(), "embedding-model", 4)

    def test_rejects_invalid_complex_range(self) -> None:
        record = example_record()
        record["character_range"] = {"start": 20, "end": 10}

        with self.assertRaisesRegex(RuntimeError, "character_range"):
            search_document(record, "embedding-model", 3)

    def test_rejects_non_finite_vector_value(self) -> None:
        record = example_record()
        record["content_vector"] = [0.25, float("nan"), 0.0]

        with self.assertRaisesRegex(RuntimeError, "finite"):
            search_document(record, "embedding-model", 3)


class SearchIndexSchemaTests(unittest.TestCase):
    def test_chunk_id_is_key_and_vector_has_profile(self) -> None:
        index = build_search_index("example-index", 1536)
        fields = {field.name: field for field in index.fields}

        self.assertTrue(fields["chunk_id"].key)
        self.assertFalse(fields["document_id"].key)
        self.assertEqual(fields["content_vector"].vector_search_dimensions, 1536)
        self.assertEqual(
            fields["content_vector"].vector_search_profile_name,
            VECTOR_PROFILE_NAME,
        )
        self.assertFalse(fields["content_vector"].retrievable)
        self.assertEqual(len(index.vector_search.algorithms), 1)
        self.assertEqual(len(index.vector_search.profiles), 1)

if __name__ == "__main__":
    unittest.main()
