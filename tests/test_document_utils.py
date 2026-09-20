from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from scripts.shared import document_utils
from scripts.stage_01_ingestion import register_source_pdf
from scripts.stage_02_processing.extract_html_text import extract_sections


class DocumentUtilsTests(unittest.TestCase):
    def test_validate_pdf_file_returns_size_hash_and_content_type(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "report.pdf"
            pdf_path.write_bytes(b"%PDF-1.7\nminimal-test-content")

            details = document_utils.validate_pdf_file(pdf_path)

            self.assertEqual(details["size_bytes"], pdf_path.stat().st_size)
            self.assertEqual(details["sha256"], document_utils.sha256_file(pdf_path))
            self.assertEqual(details["content_type"], "application/pdf")

    def test_validate_pdf_file_rejects_extension_only_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "not-really.pdf"
            pdf_path.write_bytes(b"plain text")

            with self.assertRaisesRegex(ValueError, "PDF format signature"):
                document_utils.validate_pdf_file(pdf_path)

    def test_validate_and_extract_html_main_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            html_path = Path(temporary_directory) / "guide.html"
            html_path.write_text(
                "<!doctype html><html><body><nav>Ignore me</nav><main>"
                "<h1>Support guide</h1><p>Use the official support route for help.</p>"
                "<h2>Next steps</h2><ul><li>Record the error message.</li>"
                "<li>Contact the service desk.</li></ul></main></body></html>",
                encoding="utf-8",
            )
            details = document_utils.validate_html_file(html_path)
            sections = extract_sections(html_path.read_text(encoding="utf-8"))
            self.assertEqual(details["content_type"], "text/html")
            self.assertEqual(len(sections), 2)
            self.assertNotIn("Ignore me", str(sections))

    def test_resolve_source_pdf_restricts_input_to_source_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_directory = root / "sources"
            source_directory.mkdir()
            inside = source_directory / "inside.pdf"
            outside = root / "outside.pdf"
            inside.write_bytes(b"%PDF-1.7\ninside")
            outside.write_bytes(b"%PDF-1.7\noutside")

            with patch.object(document_utils, "SOURCE_DIRECTORY", source_directory):
                self.assertEqual(document_utils.resolve_source_pdf(inside), inside)
                with self.assertRaisesRegex(ValueError, "must be inside"):
                    document_utils.resolve_source_pdf(outside)

    def test_load_and_verify_source_detects_changed_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "report.pdf"
            pdf_path.write_bytes(b"%PDF-1.7\noriginal")
            details = document_utils.validate_pdf_file(pdf_path)
            metadata = {
                "schema_version": document_utils.SOURCE_METADATA_SCHEMA_VERSION,
                "document_id": "example-report-123",
                "title": "Example Report",
                "institution": "Example Institution",
                "category": "finance",
                "document_date": "2025-07-31",
                "registered_at_utc": "2026-08-24T10:00:00Z",
                **details,
                "status": "current",
                "local_filename": pdf_path.name,
                "blob_name": "example/2025/example-report-123/report.pdf",
                "source_reference": "Document owner",
                "source_url": None,
                "usage_basis": "Approved analysis",
                "rights_note": None,
            }
            document_utils.metadata_path_for(pdf_path).write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            pdf_path.write_bytes(b"%PDF-1.7\nchanged")

            with self.assertRaisesRegex(RuntimeError, "does not match"):
                document_utils.load_and_verify_source(pdf_path)

    def test_slug_and_identifier_validation(self) -> None:
        self.assertEqual(
            document_utils.slugify("Université — Annual Report 2025"),
            "universite-annual-report-2025",
        )
        self.assertEqual(
            document_utils.validate_document_id("annual-report-2025"),
            "annual-report-2025",
        )
        with self.assertRaises(ValueError):
            document_utils.validate_document_id("Has Spaces")

    def test_optional_source_url_is_validated_without_fetching(self) -> None:
        self.assertIsNone(document_utils.validate_optional_source_url(None))
        self.assertEqual(
            document_utils.validate_optional_source_url(
                "https://example.org/reports/2025"
            ),
            "https://example.org/reports/2025",
        )
        with self.assertRaises(ValueError):
            document_utils.validate_optional_source_url("file:///tmp/report.pdf")

    def test_registration_metadata_is_generic_and_content_addressed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "Annual Report.pdf"
            pdf_path.write_bytes(b"%PDF-1.7\nregistered-content")
            args = Namespace(
                title="Example Annual Report",
                institution="Example Institution",
                category="finance",
                document_date="2025-07-31",
                status="current",
                source_reference="Document owner",
                source_url=None,
                usage_basis="Approved portfolio analysis",
                rights_note="Do not redistribute",
                document_id=None,
            )

            metadata = register_source_pdf.build_metadata(args, pdf_path)

            self.assertTrue(
                str(metadata["document_id"]).startswith("example-annual-report-")
            )
            self.assertEqual(metadata["institution"], "Example Institution")
            self.assertEqual(metadata["category"], "finance")
            self.assertIsNone(metadata["source_url"])
            self.assertTrue(str(metadata["blob_name"]).endswith("annual-report.pdf"))

    def test_registration_metadata_preserves_html_content_type(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            html_path = Path(temporary_directory) / "guide.html"
            html_path.write_text(
                "<!doctype html><html><main><h1>Guide</h1></main></html>",
                encoding="utf-8",
            )
            args = Namespace(
                title="Example Guide",
                institution="Example Institution",
                category="digital_learning",
                document_date="2025-08-05",
                status="current",
                source_reference="Official website",
                source_url="https://example.org/guide",
                usage_basis="Portfolio evaluation",
                rights_note="Do not redistribute",
                document_id=None,
            )
            metadata = register_source_pdf.build_metadata(args, html_path)
            self.assertEqual(metadata["content_type"], "text/html")
            self.assertTrue(str(metadata["blob_name"]).endswith("guide.html"))

    def test_category_uses_stable_machine_readable_format(self) -> None:
        self.assertEqual(document_utils.validate_category("student_admin"), "student_admin")
        with self.assertRaises(ValueError):
            document_utils.validate_category("Student Admin")


if __name__ == "__main__":
    unittest.main()
