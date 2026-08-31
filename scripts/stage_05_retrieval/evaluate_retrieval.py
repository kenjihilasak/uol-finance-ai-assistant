"""Measure question-level Recall@k and MRR for retrieval modes."""

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
from scripts.stage_05_retrieval.hybrid_search import (
    MAX_RESULTS,
    OPENAI_SCOPE,
    RetrievalConfig,
    embed_queries,
    hybrid_search,
    load_config,
    openai_base_url,
    validated_query,
    validate_limits,
    vector_search,
)


DEFAULT_DATASET = Path("evaluation/datasets/retrieval_questions_v1.json")
DEFAULT_K_VALUES = (1, 3, 5)


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    question: str
    answer_reference: str
    expected_pages: tuple[int, ...]
    relevant_chunk_ids: frozenset[str]


@dataclass(frozen=True)
class EvaluationDataset:
    dataset_id: str
    document_id: str
    review: dict[str, Any]
    cases: tuple[EvaluationCase, ...]


def required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{field} must be a non-empty string")
    return value.strip()


def load_dataset(path: Path) -> EvaluationDataset:
    if not path.is_file():
        raise FileNotFoundError(f"Evaluation dataset not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Evaluation dataset must be a JSON object")
    if payload.get("schema_version") != "1.0.0":
        raise RuntimeError("Unsupported evaluation dataset schema_version")

    dataset_id = required_string(payload.get("dataset_id"), "dataset_id")
    document_id = required_string(payload.get("document_id"), "document_id")
    review = payload.get("review")
    if not isinstance(review, dict) or review.get("status") != "source_verified":
        raise RuntimeError("review.status must be source_verified")
    questions = payload.get("questions")
    if not isinstance(questions, list) or not questions:
        raise RuntimeError("questions must be a non-empty list")

    cases: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    for position, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Question {position} must be an object")
        case_id = required_string(item.get("id"), f"questions[{position}].id")
        if case_id in seen_ids:
            raise RuntimeError(f"Duplicate question id: {case_id}")
        seen_ids.add(case_id)

        question = validated_query(
            required_string(item.get("question"), f"questions[{position}].question")
        )
        answer_reference = required_string(
            item.get("answer_reference"),
            f"questions[{position}].answer_reference",
        )
        pages = item.get("expected_pages")
        if (
            not isinstance(pages, list)
            or not pages
            or any(
                not isinstance(page, int)
                or isinstance(page, bool)
                or page <= 0
                for page in pages
            )
        ):
            raise RuntimeError(f"Question {case_id} has invalid expected_pages")
        chunk_ids = item.get("relevant_chunk_ids")
        if (
            not isinstance(chunk_ids, list)
            or not chunk_ids
            or any(not isinstance(chunk_id, str) or not chunk_id for chunk_id in chunk_ids)
        ):
            raise RuntimeError(f"Question {case_id} has invalid relevant_chunk_ids")
        if any(not chunk_id.startswith(f"{document_id}-") for chunk_id in chunk_ids):
            raise RuntimeError(f"Question {case_id} references a different document")

        cases.append(
            EvaluationCase(
                case_id=case_id,
                question=question,
                answer_reference=answer_reference,
                expected_pages=tuple(pages),
                relevant_chunk_ids=frozenset(chunk_ids),
            )
        )

    return EvaluationDataset(
        dataset_id=dataset_id,
        document_id=document_id,
        review=review,
        cases=tuple(cases),
    )


def validate_k_values(k_values: tuple[int, ...]) -> tuple[int, ...]:
    if not k_values:
        raise ValueError("At least one k value is required")
    unique_values = tuple(sorted(set(k_values)))
    if unique_values[0] <= 0 or unique_values[-1] > MAX_RESULTS:
        raise ValueError(f"k values must be between 1 and {MAX_RESULTS}")
    return unique_values


def first_relevant_rank(
    retrieved_chunk_ids: list[str], relevant_chunk_ids: frozenset[str]
) -> int | None:
    for rank, chunk_id in enumerate(retrieved_chunk_ids, start=1):
        if chunk_id in relevant_chunk_ids:
            return rank
    return None


def score_rankings(
    dataset: EvaluationDataset,
    rankings: dict[str, list[str]],
    k_values: tuple[int, ...],
) -> dict[str, Any]:
    k_values = validate_k_values(k_values)
    maximum_k = max(k_values)
    per_question: list[dict[str, Any]] = []
    recall_hits = {k: 0 for k in k_values}
    reciprocal_rank_total = 0.0

    for case in dataset.cases:
        if case.case_id not in rankings:
            raise RuntimeError(f"Missing ranking for question: {case.case_id}")
        retrieved = rankings[case.case_id][:maximum_k]
        first_rank = first_relevant_rank(retrieved, case.relevant_chunk_ids)
        recalls: dict[str, float] = {}
        for k in k_values:
            hit = any(
                chunk_id in case.relevant_chunk_ids for chunk_id in retrieved[:k]
            )
            recalls[f"recall@{k}"] = float(hit)
            recall_hits[k] += int(hit)
        reciprocal_rank = 0.0 if first_rank is None else 1.0 / first_rank
        reciprocal_rank_total += reciprocal_rank
        per_question.append(
            {
                "id": case.case_id,
                "question": case.question,
                "first_relevant_rank": first_rank,
                "reciprocal_rank": reciprocal_rank,
                **recalls,
                "retrieved_chunk_ids": retrieved,
            }
        )

    count = len(dataset.cases)
    aggregate = {
        f"recall@{k}": recall_hits[k] / count for k in k_values
    }
    aggregate[f"mrr@{maximum_k}"] = reciprocal_rank_total / count
    return {"aggregate": aggregate, "questions": per_question}


def run_evaluation(
    dataset: EvaluationDataset,
    config: RetrievalConfig,
    k_values: tuple[int, ...],
    vector_candidates: int,
    mode: str,
) -> dict[str, Any]:
    if mode not in {"hybrid", "vector"}:
        raise ValueError("mode must be hybrid or vector")
    top = max(k_values)
    validate_limits(top, vector_candidates)
    credential = build_user_credential(config.tenant_id)
    token_provider = get_bearer_token_provider(credential, OPENAI_SCOPE)
    embedding_client = OpenAI(
        base_url=openai_base_url(config.openai_endpoint),
        api_key=token_provider,
        max_retries=8,
    )
    search_client = SearchClient(
        endpoint=config.search_endpoint,
        index_name=config.search_index_name,
        credential=credential,
    )
    rankings: dict[str, list[str]] = {}
    try:
        vectors = embed_queries(
            embedding_client,
            [case.question for case in dataset.cases],
            config.embedding_deployment,
            config.embedding_dimensions,
        )
        for position, (case, vector) in enumerate(
            zip(dataset.cases, vectors, strict=True), start=1
        ):
            print(f"Retrieving {position}/{len(dataset.cases)}: {case.case_id}")
            if mode == "hybrid":
                results = hybrid_search(
                    search_client,
                    case.question,
                    vector,
                    top=top,
                    vector_candidates=vector_candidates,
                    document_id=dataset.document_id,
                )
            else:
                results = vector_search(
                    search_client,
                    vector,
                    top=top,
                    vector_candidates=vector_candidates,
                    document_id=dataset.document_id,
                )
            rankings[case.case_id] = [
                str(result["chunk_id"]) for result in results
            ]
    finally:
        search_client.close()
        embedding_client.close()
        credential.close()

    scores = score_rankings(dataset, rankings, k_values)
    return {
        "schema_version": "1.0.0",
        "dataset_id": dataset.dataset_id,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "index_name": config.search_index_name,
        "embedding_deployment": config.embedding_deployment,
        "retrieval": {
            "type": "hybrid_bm25_vector" if mode == "hybrid" else "vector_only",
            "top": top,
            "vector_candidates": vector_candidates,
        },
        **scores,
    }


def write_results(payload: dict[str, Any], output: Path, overwrite: bool) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "x"
    try:
        with output.open(mode, encoding="utf-8", newline="\n") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
    except FileExistsError as error:
        raise RuntimeError(
            f"Evaluation output exists and will not be overwritten: {output}"
        ) from error


def print_summary(payload: dict[str, Any]) -> None:
    print("\nRetrieval evaluation")
    print(f"Dataset: {payload['dataset_id']}")
    print(f"Index: {payload['index_name']}")
    print(f"Mode: {payload['retrieval']['type']}")
    for metric, value in payload["aggregate"].items():
        print(f"{metric}: {value:.3f}")
    print("\nPer question")
    for result in payload["questions"]:
        rank = result["first_relevant_rank"]
        print(f"- {result['id']}: first relevant rank = {rank or 'not found'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate hybrid retrieval with Recall@k and MRR."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--k", type=int, nargs="+", default=list(DEFAULT_K_VALUES))
    parser.add_argument("--vector-candidates", type=int, default=50)
    parser.add_argument(
        "--mode",
        choices=("hybrid", "vector"),
        default="hybrid",
        help="Hybrid combines BM25 and vectors; vector excludes keyword search.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Defaults to an ignored mode-specific file under data/evaluation/.",
    )
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
    k_values = validate_k_values(tuple(args.k))
    validate_limits(max(k_values), args.vector_candidates)
    config = load_config()

    if args.dry_run:
        print("Retrieval evaluation dry run passed")
        print(f"Dataset: {dataset.dataset_id}")
        print(f"Source-verified questions: {len(dataset.cases)}")
        print(f"Index: {config.search_index_name}")
        print(f"Retrieval mode: {args.mode}")
        recall_metrics = ", ".join(f"Recall@{k}" for k in k_values)
        print(f"Metrics: {recall_metrics}, MRR@{max(k_values)}")
        print("Azure authentication and retrieval: not performed")
        return

    payload = run_evaluation(
        dataset,
        config,
        k_values,
        args.vector_candidates,
        args.mode,
    )
    output = args.output or Path(
        f"data/evaluation/{args.mode}_retrieval_v1.results.json"
    )
    write_results(payload, output, args.overwrite)
    print_summary(payload)
    print(f"\nResults written to ignored local file: {output}")


if __name__ == "__main__":
    main()
