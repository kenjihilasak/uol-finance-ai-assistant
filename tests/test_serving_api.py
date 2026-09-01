from __future__ import annotations

import unittest
from datetime import date

from api.catalog import PublicDocument, load_document_catalog
from api.main import answer_response, configured_origins
from api.rate_limit import FixedWindowRateLimiter
from scripts.stage_05_retrieval.generate_grounded_answer import (
    Evidence,
    GroundedAnswer,
)


class ServingApiTests(unittest.TestCase):
    def test_catalog_contains_official_https_pdf(self) -> None:
        catalog = load_document_catalog()
        self.assertEqual(len(catalog), 1)
        document = next(iter(catalog.values()))
        self.assertTrue(document.source_url.startswith("https://www.leeds.ac.uk/"))
        self.assertTrue(document.source_url.endswith(".pdf"))
        self.assertEqual(document.page_url(83), f"{document.source_url}#page=83")

    def test_answer_contract_exposes_only_cited_evidence(self) -> None:
        document = PublicDocument(
            document_id="document-1",
            title="Report",
            institution="Institution",
            document_date=date(2025, 7, 31),
            source_url="https://example.com/report.pdf",
            status="current",
            suggested_questions=("Question?",),
        )
        evidence = [
            Evidence("S1", "chunk-1", "Report", 10, "Source", "Used evidence"),
            Evidence("S2", "chunk-2", "Report", 11, "Source", "Unused evidence"),
        ]
        response = answer_response(
            GroundedAnswer("answered", "Grounded answer", ("S1",)),
            evidence,
            document,
        )
        self.assertEqual(len(response.citations), 1)
        self.assertEqual(response.citations[0].chunk_id, "chunk-1")
        self.assertEqual(
            response.citations[0].page_url,
            "https://example.com/report.pdf#page=10",
        )

    def test_rate_limiter_recovers_after_window(self) -> None:
        now = [0.0]
        limiter = FixedWindowRateLimiter(2, window_seconds=60, clock=lambda: now[0])
        self.assertTrue(limiter.allow("visitor")[0])
        self.assertTrue(limiter.allow("visitor")[0])
        self.assertFalse(limiter.allow("visitor")[0])
        now[0] = 61.0
        self.assertTrue(limiter.allow("visitor")[0])

    def test_default_cors_origins_exclude_wildcard(self) -> None:
        origins = configured_origins()
        self.assertIn("https://kenjihilasak.github.io", origins)
        self.assertNotIn("*", origins)


if __name__ == "__main__":
    unittest.main()
