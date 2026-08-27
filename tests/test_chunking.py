from __future__ import annotations

import unittest

from scripts.stage_02_processing.chunk_extracted_text import (
    build_chunks,
    split_page_text,
)


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

    def test_split_rejects_minimum_larger_than_target(self) -> None:
        with self.assertRaises(ValueError):
            split_page_text(
                "content",
                min_chars=60,
                target_chars=50,
                max_chars=100,
            )

    def test_split_prefers_complete_sentences(self) -> None:
        text = (
            "Revenue increased during the year. "
            "Research income also grew. "
            "Costs remained controlled."
        )

        windows = split_page_text(
            text,
            target_chars=35,
            max_chars=55,
            overlap_chars=0,
        )

        self.assertEqual(
            [window[2] for window in windows],
            [
                "Revenue increased during the year.",
                "Research income also grew. Costs remained controlled.",
            ],
        )

    def test_overlap_reuses_a_complete_sentence(self) -> None:
        text = "First statement. Second statement. Third statement. Fourth statement."

        windows = split_page_text(
            text,
            target_chars=34,
            max_chars=50,
            overlap_chars=20,
        )

        self.assertGreater(len(windows), 1)
        self.assertTrue(windows[0][2].endswith("Second statement."))
        self.assertTrue(windows[1][2].startswith("Second statement."))

    def test_short_tail_is_merged_when_it_fits(self) -> None:
        text = (
            "First statement has useful context. "
            "Second statement completes the idea. "
            "Tail."
        )

        windows = split_page_text(
            text,
            min_chars=15,
            target_chars=45,
            max_chars=90,
            overlap_chars=0,
        )

        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0][2], text)

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
        self.assertIn("Document: Example Report", chunks[0]["embedding_text"])
        self.assertIn("Page: 7", chunks[0]["embedding_text"])
        self.assertEqual(
            chunks[0]["chunk_id"], "example-report-123-p0007-c001"
        )


if __name__ == "__main__":
    unittest.main()
