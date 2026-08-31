"""Evaluate cited generation over the reviewed positive question set."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from azure.identity import get_bearer_token_provider
from azure.search.documents import SearchClient
from openai import OpenAI

from scripts.shared.azure_auth import build_user_credential
from scripts.stage_05_retrieval.evaluate_retrieval import (
    DEFAULT_DATASET,
    EvaluationCase,
    EvaluationDataset,
    load_dataset,
    write_results,
)
from scripts.stage_05_retrieval.generate_grounded_answer import (
    Evidence,
    GenerationConfig,
    GroundedAnswer,
    TokenUsage,
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
    validate_limits,
)


DEFAULT_OUTPUT = Path("data/evaluation/generation_positive_v1.results.json")


def score_generation_case(
    case: EvaluationCase,
    answer: GroundedAnswer,
    evidence: list[Evidence],
) -> dict[str, Any]:
    evidence_by_id = {item.source_id: item for item in evidence}
    evidence_chunk_ids = [item.chunk_id for item in evidence]
    cited_chunk_ids = [
        evidence_by_id[source_id].chunk_id for source_id in answer.citation_ids
    ]
    relevant_citations = [
        chunk_id
        for chunk_id in cited_chunk_ids
        if chunk_id in case.relevant_chunk_ids
    ]
    answered = answer.status == "answered"
    context_hit = any(
        chunk_id in case.relevant_chunk_ids for chunk_id in evidence_chunk_ids
    )
    citation_hit = answered and bool(relevant_citations)
    citation_precision = (
        len(relevant_citations) / len(cited_chunk_ids) if cited_chunk_ids else 0.0
    )
    return {
        "answered": float(answered),
        "unexpected_abstention": float(not answered),
        "context_relevance_hit": float(context_hit),
        "citation_relevance_hit": float(citation_hit),
        "citation_precision": citation_precision,
        "evidence_chunk_ids": evidence_chunk_ids,
        "cited_chunk_ids": cited_chunk_ids,
        "relevant_cited_chunk_ids": relevant_citations,
    }


def aggregate_generation_scores(
    question_results: list[dict[str, Any]],
) -> dict[str, float]:
    if not question_results:
        raise ValueError("question_results must not be empty")
    metric_names = (
        "answered",
        "unexpected_abstention",
        "context_relevance_hit",
        "citation_relevance_hit",
        "citation_precision",
    )
    count = len(question_results)
    return {
        f"{name}_rate" if name != "citation_precision" else name: sum(
            float(result[name]) for result in question_results
        )
        / count
        for name in metric_names
    }


def usage_payload(usage: TokenUsage) -> dict[str, int | None]:
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
    }


def aggregate_usage(question_results: list[dict[str, Any]]) -> dict[str, int | None]:
    names = ("input_tokens", "output_tokens", "total_tokens")
    aggregate: dict[str, int | None] = {}
    for name in names:
        values = [result["usage"][name] for result in question_results]
        aggregate[name] = (
            sum(int(value) for value in values)
            if all(value is not None for value in values)
            else None
        )
    return aggregate


def run_generation_evaluation(
    dataset: EvaluationDataset,
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
            print(f"Generating {position}/{len(dataset.cases)}: {case.case_id}")
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
            scores = score_generation_case(case, answer, evidence)
            question_results.append(
                {
                    "id": case.case_id,
                    "question": case.question,
                    "answer_reference": case.answer_reference,
                    "status": answer.status,
                    "answer": answer.answer,
                    "citation_ids": list(answer.citation_ids),
                    **scores,
                    "usage": usage_payload(usage),
                    "manual_answer_review_required": True,
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
        "aggregate": aggregate_generation_scores(question_results),
        "usage": aggregate_usage(question_results),
        "questions": question_results,
    }


def print_summary(payload: dict[str, Any]) -> None:
    print("\nPositive generation evaluation")
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
        print(
            f"- {result['id']}: status={result['status']}, "
            f"citation_hit={bool(result['citation_relevance_hit'])}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate generation on the 10 reviewed positive questions."
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate dataset and configuration without contacting Azure.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = load_dataset(args.dataset)
    config = load_config()
    validate_limits(args.top, args.vector_candidates)

    if args.dry_run:
        print("Generation evaluation dry run passed")
        print(f"Dataset: {dataset.dataset_id}")
        print(f"Positive questions: {len(dataset.cases)}")
        print(f"Index: {config.retrieval.search_index_name}")
        print(f"Chat deployment: {config.chat_deployment}")
        print(
            "Planned model calls: 1 embedding batch + "
            f"{len(dataset.cases)} chat responses"
        )
        print("Azure authentication, retrieval, and generation: not performed")
        return

    payload = run_generation_evaluation(
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
