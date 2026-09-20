from __future__ import annotations

import re


SENSITIVE_PATTERNS: dict[str, tuple[str, ...]] = {
    "emergency": (
        r"\bimmediate danger\b", r"\bnot safe right now\b", r"\bcall 999\b",
        r"\bsuicid(?:e|al)\b", r"\bself[- ]?harm\b",
    ),
    "harassment_or_misconduct": (
        r"\bharass(?:ed|ment|ing)?\b", r"\bsexual (?:assault|misconduct|harassment)\b",
        r"\bbull(?:y|ied|ying)\b", r"\bdiscriminat(?:e|ed|ion)\b",
        r"\bstalk(?:ed|ing)?\b", r"\bfeel unsafe\b",
    ),
    "mental_health_or_wellbeing": (
        r"\bmental health\b", r"\bpanic attack\b", r"\bsevere anxiety\b",
        r"\bdepress(?:ed|ion)\b", r"\bcrisis\b",
    ),
}


def detect_sensitive_terms(enquiry: str) -> tuple[str, ...]:
    text = enquiry.casefold()
    return tuple(
        label
        for label, patterns in SENSITIVE_PATTERNS.items()
        if any(re.search(pattern, text) for pattern in patterns)
    )
