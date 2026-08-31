"""Evaluate abstention over reviewed unanswerable questions."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from azure.identity import get_bearer_token_provider
from azure.search.documents import SearchClient
from openai import OpenAI

from scripts.shared.azure_auth import build_user_credential
from scripts.stage_05_retrieval.evaluate_generation import (
    aggregate_usage,
    usage_payload,
)
from scripts.stage_05_retrieval.evaluate_retrieval import (
    required_string,
    write_results,
)
from scripts.stage_05_retrieval.generate_grounded_answer import (
    GenerationConfig,
    GroundedAnswer,
    evidence_from_results,
    generate_answer_with_usage,
    load_config,
)
from scripts.stage_05_retrieval.hybrid_search import (
    DEFAULT_TOP,
    DEFAULT_VECTOR_CANDIDATES,
    OPENAI_SCOPE,
    embed_queries,
    hybrid_search,
    openai_base_url,
    validated_query,
    validate_limits,
)


DEFAULT_DATASET = Path("evaluation/datasets/abstention_questions_v1.json")
DEFAULT_OUTPUT = Path("data/evaluation/abstention_v1.results.json")


@dataclass(frozen=True)
class AbstentionCase:
    case_id: str
    question: str
    category: str
    reason: str


@dataclass(frozen=True)
class AbstentionDataset:
    dataset_id: str
    document_id: str
    review: dict[str, Any]
    cases: tuple[AbstentionCase, ...]


def load_abstention_dataset(path: Path) -> AbstentionDataset:
    if not path.is_file():
        raise FileNotFoundError(f"Abstention dataset not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Abstention dataset must be a JSON object")
    if payload.get("schema_version") != "1.0.0":
        raise RuntimeError("Unsupported abstention dataset schema_version")

    dataset_id = required_string(payload.get("dataset_id"), "dataset_id")
    document_id = required_string(payload.get("document_id"), "document_id")
    review = payload.get("review")
    if not isinstance(review, dict) or review.get("status") != "scope_verified":
        raise RuntimeError("review.status must be scope_verified")
    questions = payload.get("questions")
    if not isinstance(questions, list) or not questions:
        raise RuntimeError("questions must be a non-empty list")

    cases: list[AbstentionCase] = []
    seen_ids: set[str] = set()
    for position, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Question {position} must be an object")
        case_id = required_string(item.get("id"), f"questions[{position}].id")
        if case_id in seen_ids:
            raise RuntimeError(f"Duplicate question id: {case_id}")
        seen_ids.add(case_id)
        cases.append(
            AbstentionCase(
                case_id=case_id,
                question=validated_query(
                    required_string(
                        item.get("question"),
                        f"questions[{position}].question",
                    )
                ),
                category=required_string(
                    item.get("category"),
                    f"questions[{position}].category",
                ),
                reason=required_string(
                    item.get("reason"),
                    f"questions[{position}].reason",
                ),
            )
        )

    return AbstentionDataset(
        dataset_id=dataset_id,
        document_id=document_id,
        review=review,
        cases=tuple(cases),
    )


def score_abstention(answer: GroundedAnswer) -> dict[str, float]:
    abstained = answer.status == "abstained"
    return {
        "correct_abstention": float(abstained),
        "false_answer": float(not abstained),
        "citation_free_abstention": float(abstained and not answer.citation_ids),
    }


def aggregate_abstention_scores(
    question_results: list[dict[str, Any]],
) -> dict[str, float]:
    if not question_results:
        raise ValueError("question_results must not be empty")
    count = len(question_results)
    return {
        "correct_abstention_rate": sum(
            float(result["correct_abstention"]) for result in question_results
        )
        / count,
        "false_answer_rate": sum(
            float(result["false_answer"]) for result in question_results
        )
        / count,
        "citation_free_abstention_rate": sum(
            float(result["citation_free_abstention"])
            for result in question_results
        )
        / count,
    }


def run_abstention_evaluation(
    dataset: AbstentionDataset,
    config: GenerationConfig,
    *,
    top: int,
    vector_candidates: int,
) -> dict[str, Any]:
    validate_limits(top, vector_candidates)
    credential = build_user_credential(config.retrieval.tenant_id)
    token_provider = get_bearer_token_provider(credential, OPENAI_SCOPE)
    model_client = OpenAI(
        base_url=openai_base_url(config.retrieval.openai_endpoint),
        api_key=token_provider,
        max_retries=8,
    )
    search_client = SearchClient(
        endpoint=config.retrieval.search_endpoint,
        index_name=config.retrieval.search_index_name,
        credential=credential,
    )
    question_results: list[dict[str, Any]] = []
    try:
        vectors = embed_queries(
            model_client,
            [case.question for case in dataset.cases],
            config.retrieval.embedding_deployment,
            config.retrieval.embedding_dimensions,
        )
        for position, (case, vector) in enumerate(
            zip(dataset.cases, vectors, strict=True), start=1
        ):
            print(f"Testing {position}/{len(dataset.cases)}: {case.case_id}")
            results = hybrid_search(
                search_client,
                case.question,
                vector,
                top=top,
                vector_candidates=vector_candidates,
                document_id=dataset.document_id,
            )
            evidence = evidence_from_results(results)
            answer, usage = generate_answer_with_usage(
                model_client,
                config.chat_deployment,
                case.question,
                evidence,
            )
            evidence_by_id = {item.source_id: item for item in evidence}
            question_results.append(
                {
                    "id": case.case_id,
                    "question": case.question,
                    "category": case.category,
                    "unanswerable_reason": case.reason,
                    "status": answer.status,
                    "answer": answer.answer,
                    "citation_ids": list(answer.citation_ids),
                    "evidence_chunk_ids": [item.chunk_id for item in evidence],
                    "cited_chunk_ids": [
                        evidence_by_id[source_id].chunk_id
                        for source_id in answer.citation_ids
                    ],
                    **score_abstention(answer),
                    "usage": usage_payload(usage),
                }
            )
    finally:
        search_client.close()
        model_client.close()
        credential.close()

    return {
        "schema_version": "1.0.0",
        "dataset_id": dataset.dataset_id,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "index_name": config.retrieval.search_index_name,
        "embedding_deployment": config.retrieval.embedding_deployment,
        "chat_deployment": config.chat_deployment,
        "retrieval": {
            "type": "hybrid_bm25_vector",
            "top": top,
            "vector_candidates": vector_candidates,
        },
        "aggregate": aggregate_abstention_scores(question_results),
        "usage": aggregate_usage(question_results),
        "questions": question_results,
    }


def print_summary(payload: dict[str, Any]) -> None:
    print("\nAbstention evaluation")
    print(f"Dataset: {payload['dataset_id']}")
    print(f"Questions: {len(payload['questions'])}")
    for metric, value in payload["aggregate"].items():
        print(f"{metric}: {value:.3f}")
    usage = payload["usage"]
    print(
        "Token usage: "
        f"input={usage['input_tokens']}, "
        f"output={usage['output_tokens']}, "
        f"total={usage['total_tokens']}"
    )
    print("\nPer question")
    for result in payload["questions"]:
        print(f"- {result['id']}: {result['status']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate abstention on reviewed unanswerable questions."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--top", type=int, default=DEFAULT_TOP)
    parser.add_argument(
        "--vector-candidates",
        type=int,
        default=DEFAULT_VECTOR_CANDIDATES,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = load_abstention_dataset(args.dataset)
    config = load_config()
    validate_limits(args.top, args.vector_candidates)

    if args.dry_run:
        print("Abstention evaluation dry run passed")
        print(f"Dataset: {dataset.dataset_id}")
        print(f"Unanswerable questions: {len(dataset.cases)}")
        print(f"Chat deployment: {config.chat_deployment}")
        print(
            "Planned model calls: 1 embedding batch + "
            f"{len(dataset.cases)} chat responses"
        )
        print("Azure authentication, retrieval, and generation: not performed")
        return

    payload = run_abstention_evaluation(
        dataset,
        config,
        top=args.top,
        vector_candidates=args.vector_candidates,
    )
    write_results(payload, args.output, args.overwrite)
    print_summary(payload)
    print(f"\nDetailed results written to ignored file: {args.output}")


if __name__ == "__main__":
    main()
