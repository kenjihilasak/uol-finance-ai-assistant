from __future__ import annotations

import json
import os
from io import BytesIO
from threading import Lock
from typing import Any

from openpyxl import Workbook


FIELDS = (
    "enquiry_id", "created_at_utc", "enquiry", "summary", "category",
    "subcategory", "is_sensitive", "action", "route_to", "missing_info",
    "answer_status", "draft_response", "citation_ids", "review_status",
)


class EnquiryRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self._records: list[dict[str, Any]] = []
        self._lock = Lock()

    def _connect(self):
        import psycopg
        return psycopg.connect(self.database_url)

    def _ensure_table(self, connection: Any) -> None:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS triage_enquiries (
                enquiry_id TEXT PRIMARY KEY, created_at_utc TIMESTAMPTZ NOT NULL,
                enquiry TEXT NOT NULL, summary TEXT NOT NULL, category TEXT NOT NULL,
                subcategory TEXT NOT NULL, is_sensitive BOOLEAN NOT NULL,
                action TEXT NOT NULL, route_to TEXT NOT NULL, missing_info JSONB NOT NULL,
                answer_status TEXT, draft_response TEXT, citation_ids JSONB NOT NULL,
                review_status TEXT NOT NULL
            )
        """)

    def save(self, record: dict[str, Any]) -> None:
        stored = dict(record)
        if stored["is_sensitive"]:
            stored["enquiry"] = "[Sensitive enquiry redacted]"
        if not self.database_url:
            with self._lock:
                self._records.insert(0, stored)
            return
        with self._connect() as connection:
            self._ensure_table(connection)
            connection.execute(
                """INSERT INTO triage_enquiries
                (enquiry_id,created_at_utc,enquiry,summary,category,subcategory,
                 is_sensitive,action,route_to,missing_info,answer_status,
                 draft_response,citation_ids,review_status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s::jsonb,%s)
                ON CONFLICT (enquiry_id) DO NOTHING""",
                tuple(
                    json.dumps(stored[name]) if name in {"missing_info", "citation_ids"}
                    else stored[name]
                    for name in FIELDS
                ),
            )

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.database_url:
            with self._lock:
                return [dict(item) for item in self._records[:limit]]
        with self._connect() as connection:
            self._ensure_table(connection)
            rows = connection.execute(
                f"SELECT {','.join(FIELDS)} FROM triage_enquiries ORDER BY created_at_utc DESC LIMIT %s",
                (limit,),
            ).fetchall()
        return [dict(zip(FIELDS, row, strict=True)) for row in rows]

    def export_xlsx(self) -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Enquiries"
        sheet.append(list(FIELDS))
        for record in self.list(limit=10_000):
            sheet.append([
                json.dumps(record.get(name), ensure_ascii=False)
                if isinstance(record.get(name), (list, tuple, dict))
                else record.get(name)
                for name in FIELDS
            ])
        sheet.freeze_panes = "A2"
        stream = BytesIO()
        workbook.save(stream)
        return stream.getvalue()

    def update_review(self, enquiry_id: str, review_status: str) -> bool:
        if not self.database_url:
            with self._lock:
                for record in self._records:
                    if record["enquiry_id"] == enquiry_id:
                        record["review_status"] = review_status
                        return True
            return False
        with self._connect() as connection:
            self._ensure_table(connection)
            result = connection.execute(
                "UPDATE triage_enquiries SET review_status=%s WHERE enquiry_id=%s",
                (review_status, enquiry_id),
            )
            return result.rowcount == 1
