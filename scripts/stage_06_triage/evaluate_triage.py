from __future__ import annotations

import argparse
import json
from pathlib import Path

from azure.identity import get_bearer_token_provider
from openai import OpenAI

from scripts.shared.azure_auth import build_user_credential
from scripts.stage_05_retrieval.generate_grounded_answer import load_config, openai_base_url
from scripts.stage_05_retrieval.hybrid_search import OPENAI_SCOPE
from scripts.stage_06_triage.classify_enquiry import classify_enquiry
from scripts.stage_06_triage.routing_policy import apply_routing_policy
from scripts.stage_06_triage.sensitive_rules import detect_sensitive_terms


def load_cases(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if payload.get("schema_version") != "1.0.0" or not isinstance(cases, list):
        raise RuntimeError("Invalid triage evaluation dataset")
    required = {"id", "enquiry", "category", "is_sensitive", "action", "route_to"}
    seen_ids: set[str] = set()
    for position, case in enumerate(cases, 1):
        if not isinstance(case, dict) or not required.issubset(case):
            raise RuntimeError(f"Invalid triage case {position}")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in seen_ids:
            raise RuntimeError(f"Invalid or duplicate triage case id at {position}")
        seen_ids.add(case_id)
        if not isinstance(case.get("is_sensitive"), bool):
            raise RuntimeError(f"Invalid is_sensitive value for {case_id}")
    return cases


def score(cases: list[dict[str, object]], predictions: list[dict[str, object]]) -> dict[str, float | int]:
    if len(cases) != len(predictions):
        raise ValueError("Cases and predictions must have equal lengths")
    total = len(cases)
    fields = ("category", "action", "route_to")
    metrics: dict[str, float | int] = {f"{field}_accuracy": sum(c[field] == p[field] for c, p in zip(cases, predictions, strict=True)) / total for field in fields}
    pairs = list(zip(cases, predictions, strict=True))
    true_positive = sum(bool(c["is_sensitive"]) and bool(p["is_sensitive"]) for c, p in pairs)
    false_negative = sum(bool(c["is_sensitive"]) and not bool(p["is_sensitive"]) for c, p in pairs)
    false_positive = sum(not bool(c["is_sensitive"]) and bool(p["is_sensitive"]) for c, p in pairs)
    true_negative = sum(not bool(c["is_sensitive"]) and not bool(p["is_sensitive"]) for c, p in pairs)
    sensitive_count = true_positive + false_negative
    predicted_sensitive_count = true_positive + false_positive
    non_sensitive_count = true_negative + false_positive
    metrics["sensitive_recall"] = true_positive / sensitive_count if sensitive_count else 0.0
    metrics["sensitive_precision"] = true_positive / predicted_sensitive_count if predicted_sensitive_count else 0.0
    metrics["sensitive_specificity"] = true_negative / non_sensitive_count if non_sensitive_count else 0.0
    metrics["sensitive_false_positives"] = false_positive
    metrics["sensitive_generation_leaks"] = sum(
        bool(p.get("allow_generation")) for c, p in pairs if c["is_sensitive"]
    )
    metrics["generation_gate_accuracy"] = sum(
        bool(p.get("allow_generation")) == (c["action"] == "draft_response")
        for c, p in pairs
    ) / total
    metrics["cases"] = total
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate staff enquiry triage.")
    parser.add_argument("--dataset", type=Path, default=Path("evaluation/datasets/triage_cases_v1.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    cases = load_cases(args.dataset)
    if not args.live:
        print(f"Triage dataset validation passed: {len(cases)} cases")
        print("Use --live to call the classifier and measure routing.")
        return
    config = load_config()
    credential = build_user_credential(config.retrieval.tenant_id)
    token_provider = get_bearer_token_provider(credential, OPENAI_SCOPE)
    client = OpenAI(base_url=openai_base_url(config.retrieval.openai_endpoint), api_key=token_provider, max_retries=8)
    predictions = []
    try:
        for case in cases:
            enquiry = str(case["enquiry"])
            c = classify_enquiry(client, config.chat_deployment, enquiry)
            decision = apply_routing_policy(c, detect_sensitive_terms(enquiry))
            predictions.append({
                "id": case["id"], "category": c.category.value,
                "is_sensitive": c.is_sensitive or bool(decision.rule_flags),
                "action": decision.action.value, "route_to": decision.route_to.value,
                "allow_generation": decision.allow_generation,
            })
    finally:
        client.close()
        credential.close()
    result = {"dataset": str(args.dataset), "metrics": score(cases, predictions), "predictions": predictions}
    print(json.dumps(result["metrics"], indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
