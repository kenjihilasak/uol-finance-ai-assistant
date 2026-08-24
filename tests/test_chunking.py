from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from chunk_extracted_text import build_chunks, split_page_text  # noqa: E402


class ChunkingTests(unittest.TestCase):
    def test_split_is_bounded_and_deterministic(self) -> None:
        text = "one two three four five six seven eight nine ten eleven twelve"

        first = split_page_text(text, max_chars=20, overlap_chars=5)
        second = split_page_text(text, max_chars=20, overlap_chars=5)

        self.assertEqual(first, second)
        self.assertGreater(len(first), 1)
        self.assertTrue(all(len(chunk_text) <= 20 for _, _, chunk_text in first))
        self.assertTrue(all(text[start:end] == value for start, end, value in first))

    def test_split_rejects_invalid_overlap(self) -> None:
        with self.assertRaises(ValueError):
            split_page_text("content", max_chars=100, overlap_chars=100)

    def test_chunks_carry_generic_provenance(self) -> None:
        document = {
            "document_id": "example-report-123",
            "source": {
                "title": "Example Report",
                "institution": "Example Institution",
                "source_reference": "Document owner",
                "source_url": None,
                "document_date": "2025-07-31",
                "status": "current",
                "sha256": "abc123",
            },
            "pages": [{"page_number": 7, "text": "Revenue increased in 2025."}],
        }

        chunks = build_chunks(document, max_chars=100, overlap_chars=10)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["page_number"], 7)
        self.assertEqual(chunks[0]["institution"], "Example Institution")
        self.assertIsNone(chunks[0]["source_url"])
        self.assertEqual(
            chunks[0]["chunk_id"], "example-report-123-p0007-c001"
        )


if __name__ == "__main__":
    unittest.main()
