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
- unsupported: a clear enquiry outside the approved categories, including
  facilities, maintenance, room or equipment faults, operational incidents,
  sensitive-support-only enquiries, or intent that cannot be mapped safely.
Sensitive personal difficulty always takes precedence over other topics.
For a mixed sensitive enquiry, retain its supported knowledge category when one
applies; otherwise use unsupported. Sensitivity is not a category.
Physical hazards or equipment faults are unsupported, not sensitive, unless the
enquiry also reports an immediate threat, injury or sensitive personal matter.
Use specialist_referral for sensitive cases, request_clarification when essential
information is missing from an otherwise supported enquiry, draft_response for
supported complete questions, and manual_review for non-sensitive unsupported
enquiries. Never invent personal details. For non-sensitive unsupported
enquiries, return manual_review, manual_triage and an empty missing_info array;
do not request contact details. Always propose one controlled route; never use
an empty route."""


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
                    "digital_learning", "unsupported",
                ]},
                "subcategory": {"type": "string", "minLength": 1, "maxLength": 80},
                "is_sensitive": {"type": "boolean"},
                "action": {"type": "string", "enum": [
                    "draft_response", "request_clarification",
                    "specialist_referral", "manual_review",
                ]},
                "route_to": {"type": "string", "enum": [
                    "finance_information", "finance_team",
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
