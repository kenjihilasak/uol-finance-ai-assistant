from __future__ import annotations

from scripts.stage_06_triage.schemas import (
    Category,
    EnquiryClassification,
    RouteTo,
    TriageAction,
    TriageDecision,
)


ANSWERABLE_CATEGORIES = {
    Category.FINANCE,
    Category.FINANCE_OPERATIONS,
    Category.STUDENT_ADMIN,
    Category.DIGITAL_LEARNING,
}


def sensitive_route(flags: tuple[str, ...], classification: EnquiryClassification) -> RouteTo:
    if "emergency" in flags or classification.route_to == RouteTo.SECURITY_OR_EMERGENCY:
        return RouteTo.SECURITY_OR_EMERGENCY
    if "harassment_or_misconduct" in flags or classification.route_to == RouteTo.HARASSMENT_AND_MISCONDUCT:
        return RouteTo.HARASSMENT_AND_MISCONDUCT
    return RouteTo.STUDENT_COUNSELLING_AND_WELLBEING


def apply_routing_policy(
    classification: EnquiryClassification,
    rule_flags: tuple[str, ...] = (),
) -> TriageDecision:
    if rule_flags or classification.is_sensitive:
        return TriageDecision(
            classification=classification,
            action=TriageAction.SPECIALIST_REFERRAL,
            route_to=sensitive_route(rule_flags, classification),
            allow_generation=False,
            reason="Sensitive enquiries are routed without retrieval or generation.",
            rule_flags=rule_flags,
        )
    if classification.category == Category.UNSUPPORTED:
        return TriageDecision(
            classification=classification,
            action=TriageAction.MANUAL_REVIEW,
            route_to=RouteTo.MANUAL_TRIAGE,
            allow_generation=False,
            reason="The enquiry is outside the approved knowledge domains.",
            rule_flags=rule_flags,
        )
    if (
        classification.missing_info
        or classification.action == TriageAction.REQUEST_CLARIFICATION
    ):
        return TriageDecision(
            classification=classification,
            action=TriageAction.REQUEST_CLARIFICATION,
            route_to=classification.route_to,
            allow_generation=False,
            reason="The team needs more information before responding.",
            rule_flags=rule_flags,
        )
    if (
        classification.category not in ANSWERABLE_CATEGORIES
        or classification.action == TriageAction.MANUAL_REVIEW
    ):
        return TriageDecision(
            classification=classification,
            action=TriageAction.MANUAL_REVIEW,
            route_to=RouteTo.MANUAL_TRIAGE,
            allow_generation=False,
            reason="No approved answer corpus is available for this category.",
            rule_flags=rule_flags,
        )
    return TriageDecision(
        classification=classification,
        action=TriageAction.DRAFT_RESPONSE,
        route_to=classification.route_to,
        allow_generation=True,
        reason="Approved evidence may be retrieved for a staff-reviewed draft.",
        rule_flags=rule_flags,
    )
