from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Category(str, Enum):
    FINANCE = "finance"
    FINANCE_OPERATIONS = "finance_operations"
    STUDENT_ADMIN = "student_admin"
    DIGITAL_LEARNING = "digital_learning"
    STUDENT_SUPPORT = "student_support"
    UNSUPPORTED = "unsupported"
    UNCLEAR = "unclear"


class TriageAction(str, Enum):
    DRAFT_RESPONSE = "draft_response"
    REQUEST_CLARIFICATION = "request_clarification"
    SPECIALIST_REFERRAL = "specialist_referral"
    MANUAL_REVIEW = "manual_review"


class RouteTo(str, Enum):
    NONE = "none"
    FINANCE_INFORMATION = "finance_information"
    FINANCE_TEAM = "finance_team"
    STUDENT_INFORMATION_SERVICE = "student_information_service"
    IT_SERVICE_DESK = "it_service_desk"
    ONLINE_LEARNING_SUPPORT = "online_learning_support"
    HARASSMENT_AND_MISCONDUCT = "harassment_and_misconduct"
    STUDENT_COUNSELLING_AND_WELLBEING = "student_counselling_and_wellbeing"
    SECURITY_OR_EMERGENCY = "security_or_emergency"
    MANUAL_TRIAGE = "manual_triage"


class EnquiryClassification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = Field(min_length=1, max_length=500)
    category: Category
    subcategory: str = Field(min_length=1, max_length=80)
    is_sensitive: bool
    action: TriageAction
    route_to: RouteTo
    missing_info: tuple[str, ...] = Field(default_factory=tuple, max_length=10)


class TriageDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    classification: EnquiryClassification
    action: TriageAction
    route_to: RouteTo
    allow_generation: bool
    reason: str
    rule_flags: tuple[str, ...] = ()


class TriageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enquiry_id: str
    created_at_utc: str
    enquiry: str
    decision: TriageDecision
    answer_status: str | None = None
    draft_response: str | None = None
    citation_ids: tuple[str, ...] = ()
    review_status: str = "pending"
