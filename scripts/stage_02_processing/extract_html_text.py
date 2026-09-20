"""Extract deterministic sections from a registered local HTML snapshot."""

from __future__ import annotations

import argparse
import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

from scripts.shared.document_utils import (
    load_and_verify_source,
    processed_path,
    resolve_source_document,
)
from scripts.stage_02_processing.extract_pdf_text import (
    build_processed_document,
    normalise_page_text,
    write_json,
)


SKIPPED_ELEMENTS = {"script", "style", "noscript", "svg", "nav", "footer", "header"}
BLOCK_ELEMENTS = {"p", "li", "dt", "dd", "tr", "blockquote"}


class MainContentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.main_depth = 0
        self.skip_depth = 0
        self.current_heading: list[str] | None = None
        self.current_block: list[str] | None = None
        self.sections: list[tuple[str, list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "main":
            self.main_depth += 1
            return
        if not self.main_depth:
            return
        if tag in SKIPPED_ELEMENTS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in {"h1", "h2"}:
            self.current_heading = []
        elif tag in BLOCK_ELEMENTS:
            self.current_block = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "main":
            self.main_depth = max(0, self.main_depth - 1)
            return
        if not self.main_depth:
            return
        if tag in SKIPPED_ELEMENTS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in {"h1", "h2"} and self.current_heading is not None:
            heading = clean_text(" ".join(self.current_heading))
            if heading:
                self.sections.append((heading, []))
            self.current_heading = None
        elif tag in BLOCK_ELEMENTS and self.current_block is not None:
            block = clean_text(" ".join(self.current_block))
            if block:
                if not self.sections:
                    self.sections.append(("Overview", []))
                self.sections[-1][1].append(block)
            self.current_block = None

    def handle_data(self, data: str) -> None:
        if not self.main_depth or self.skip_depth:
            return
        if self.current_heading is not None:
            self.current_heading.append(data)
        if self.current_block is not None:
            self.current_block.append(data)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_sections(html: str) -> list[dict[str, object]]:
    parser = MainContentParser()
    parser.feed(html)
    pages: list[dict[str, object]] = []
    for heading, blocks in parser.sections:
        text = normalise_page_text("\n\n".join([heading, *blocks]))
        if len(text.split()) < 5:
            continue
        pages.append(
            {
                "page_number": len(pages) + 1,
                "section_title": heading,
                "text": text,
                "character_count": len(text),
                "word_count": len(text.split()),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
    if not pages:
        raise RuntimeError("No usable sections were found inside the HTML main element")
    return pages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a registered local HTML snapshot to section-level JSON."
    )
    parser.add_argument("--file", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = resolve_source_document(args.file)
    if source_path.suffix.lower() not in {".html", ".htm"}:
        raise ValueError("The source file must have an .html or .htm extension")
    metadata = load_and_verify_source(source_path)
    html = source_path.read_text(encoding="utf-8")
    pages = extract_sections(html)
    document = build_processed_document(metadata, pages, "stdlib-html-parser-1", 1.0)
    processing = document["processing"]
    processing["extractor"] = {"name": "html.parser", "version": "stdlib"}
    processing["extraction_mode"] = "main_h1_h2_sections"
    processing["section_count"] = len(pages)
    output_path = processed_path(str(metadata["document_id"]), "processed")
    output_sha256 = write_json(document, output_path, args.overwrite)
    print("Local HTML extraction completed")
    print(f"Sections: {len(pages)}")
    print(f"Output: {output_path}")
    print(f"Output SHA-256: {output_sha256}")


if __name__ == "__main__":
    main()
