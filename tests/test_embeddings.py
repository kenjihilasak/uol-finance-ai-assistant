from __future__ import annotations

import unittest

from scripts.stage_03_embeddings.generate_embeddings import embedding_input


class EmbeddingInputTests(unittest.TestCase):
    def test_prefers_contextual_embedding_text(self) -> None:
        chunk = {
            "text": "Revenue increased.",
            "embedding_text": "Example Report\nPage 7\n\nRevenue increased.",
        }

        self.assertEqual(
            embedding_input(chunk),
            "Example Report\nPage 7\n\nRevenue increased.",
        )

    def test_supports_version_one_chunks(self) -> None:
        self.assertEqual(
            embedding_input({"text": "Revenue increased."}),
            "Revenue increased.",
        )


if __name__ == "__main__":
    unittest.main()
