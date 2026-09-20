from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from scripts.stage_06_triage.schemas import EnquiryClassification


SYSTEM_INSTRUCTIONS = """You classify unstructured enquiries for university staff.
Return a concise operational summary and one category:
- finance: corporate annual-report information.
- finance_operations: expenses, receipts, travel, subsistence, accommodation, cars or taxis.
- student_admin: personal details and address updates.
- digital_learning: Minerva, Coursera, online submissions or online-course support.
- student_support: wellbeing, mental health, harassment, discrimination, abuse or safety.
- unclear: insufficient or conflicting intent.
Sensitive personal difficulty always takes precedence over other topics.
Use specialist_referral for sensitive cases, request_clarification when essential
information is missing, draft_response for supported operational questions, and
manual_review when no safe route is clear. Never invent personal details."""


CLASSIFICATION_TEXT_CONFIG: dict[str, object] = {
    "format": {
        "type": "json_schema",
        "name": "university_enquiry_classification",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "category": {"type": "string", "enum": [
                    "finance", "finance_operations", "student_admin",
                    "digital_learning", "student_support", "unclear",
                ]},
                "subcategory": {"type": "string"},
                "is_sensitive": {"type": "boolean"},
                "action": {"type": "string", "enum": [
                    "draft_response", "request_clarification",
                    "specialist_referral", "manual_review",
                ]},
                "route_to": {"type": "string", "enum": [
                    "none", "finance_information", "finance_team",
                    "student_information_service", "it_service_desk",
                    "online_learning_support", "harassment_and_misconduct",
                    "student_counselling_and_wellbeing", "security_or_emergency",
                    "manual_triage",
                ]},
                "missing_info": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary", "category", "subcategory", "is_sensitive", "action", "route_to", "missing_info"],
            "additionalProperties": False,
        },
    }
}


def validate_enquiry(value: str) -> str:
    enquiry = value.strip()
    if len(enquiry) < 3:
        raise ValueError("enquiry must contain at least 3 characters")
    if len(enquiry) > 4_000:
        raise ValueError("enquiry must not exceed 4,000 characters")
    return enquiry


def classify_enquiry(client: OpenAI, deployment: str, enquiry: str) -> EnquiryClassification:
    response = client.responses.create(
        model=deployment,
        instructions=SYSTEM_INSTRUCTIONS,
        input=validate_enquiry(enquiry),
        max_output_tokens=600,
        reasoning={"effort": "low"},
        text=CLASSIFICATION_TEXT_CONFIG,
        store=False,
    )
    if not response.output_text:
        raise RuntimeError("Classifier returned no structured output")
    try:
        payload: Any = json.loads(response.output_text)
        return EnquiryClassification.model_validate(payload)
    except (json.JSONDecodeError, ValueError) as error:
        raise RuntimeError("Classifier returned an invalid contract") from error
