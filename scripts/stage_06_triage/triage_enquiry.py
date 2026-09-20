from __future__ import annotations

from dataclasses import dataclass

from azure.identity import get_bearer_token_provider
from openai import OpenAI

from scripts.shared.azure_auth import build_user_credential
from scripts.stage_05_retrieval.generate_grounded_answer import (
    Evidence,
    GroundedAnswer,
    GenerationConfig,
    load_config,
    openai_base_url,
    run_grounded_answer,
)
from scripts.stage_05_retrieval.hybrid_search import OPENAI_SCOPE
from scripts.stage_06_triage.classify_enquiry import classify_enquiry, validate_enquiry
from scripts.stage_06_triage.routing_policy import apply_routing_policy
from scripts.stage_06_triage.schemas import TriageDecision
from scripts.stage_06_triage.sensitive_rules import detect_sensitive_terms


@dataclass(frozen=True)
class TriageOutcome:
    decision: TriageDecision
    answer: GroundedAnswer | None
    evidence: list[Evidence]


def run_triage(config: GenerationConfig, enquiry: str) -> TriageOutcome:
    enquiry = validate_enquiry(enquiry)
    flags = detect_sensitive_terms(enquiry)
    credential = build_user_credential(config.retrieval.tenant_id)
    token_provider = get_bearer_token_provider(credential, OPENAI_SCOPE)
    client = OpenAI(
        base_url=openai_base_url(config.retrieval.openai_endpoint),
        api_key=token_provider,
        max_retries=8,
    )
    try:
        classification = classify_enquiry(client, config.chat_deployment, enquiry)
    finally:
        client.close()
        credential.close()
    decision = apply_routing_policy(classification, flags)
    if not decision.allow_generation:
        return TriageOutcome(decision, None, [])
    answer, evidence = run_grounded_answer(
        config,
        enquiry,
        top=5,
        vector_candidates=50,
        document_id=None,
        category=classification.category.value,
    )
    return TriageOutcome(decision, answer, evidence)


def run_default_triage(enquiry: str) -> TriageOutcome:
    return run_triage(load_config(), enquiry)
