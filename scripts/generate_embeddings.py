from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from azure.identity import InteractiveBrowserCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "university-of-leeds-annual-report-2024-25.chunks.json"
)
OUTPUT_PATH = INPUT_PATH.with_name(
    "university-of-leeds-annual-report-2024-25.embeddings.json"
)

BATCH_SIZE = 16
OPENAI_SCOPE = "https://ai.azure.com/.default"


@dataclass(frozen=True)
class EmbeddingConfig:
    tenant_id: str
    endpoint: str
    deployment: str
    dimensions: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def batches(values: list[dict[str, object]]) -> Iterator[list[dict[str, object]]]:
    for start in range(0, len(values), BATCH_SIZE):
        yield values[start : start + BATCH_SIZE]


def load_chunks(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        raise FileNotFoundError(f"Chunk file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    chunks = payload.get("chunks") if isinstance(payload, dict) else None
    if not isinstance(chunks, list) or not chunks:
        raise RuntimeError("The chunk file must contain a non-empty chunks list")

    chunk_ids: set[str] = set()
    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise RuntimeError("Every chunk must be an object")
        chunk_id = chunk.get("chunk_id")
        text = chunk.get("text")
        if not isinstance(chunk_id, str) or not isinstance(text, str) or not text:
            raise RuntimeError("Every chunk must have a non-empty chunk_id and text")
        if chunk_id in chunk_ids:
            raise RuntimeError(f"Duplicate chunk_id: {chunk_id}")
        chunk_ids.add(chunk_id)

    return chunks


def load_config() -> EmbeddingConfig:
    load_dotenv(PROJECT_ROOT / ".env")
    required_names = (
        "AZURE_TENANT_ID",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_EMBEDDING_DEPLOYMENT",
        "AZURE_EMBEDDING_DIMENSIONS",
    )
    missing = [name for name in required_names if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Missing required local configuration: " + ", ".join(missing)
        )

    try:
        dimensions = int(os.environ["AZURE_EMBEDDING_DIMENSIONS"])
    except ValueError as error:
        raise RuntimeError("AZURE_EMBEDDING_DIMENSIONS must be an integer") from error
    if dimensions <= 0:
        raise RuntimeError("AZURE_EMBEDDING_DIMENSIONS must be positive")

    return EmbeddingConfig(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/"),
        deployment=os.environ["AZURE_EMBEDDING_DEPLOYMENT"],
        dimensions=dimensions,
    )


def openai_base_url(endpoint: str) -> str:
    if endpoint.endswith("/openai/v1"):
        return f"{endpoint}/"
    return f"{endpoint}/openai/v1/"


def create_client(config: EmbeddingConfig) -> OpenAI:
    credential = InteractiveBrowserCredential(tenant_id=config.tenant_id)
    token_provider = get_bearer_token_provider(credential, OPENAI_SCOPE)
    return OpenAI(
        base_url=openai_base_url(config.endpoint),
        api_key=token_provider,
    )


def embed_chunks(
    chunks: list[dict[str, object]], config: EmbeddingConfig
) -> list[dict[str, object]]:
    client = create_client(config)
    records: list[dict[str, object]] = []

    for batch in batches(chunks):
        texts = [str(chunk["text"]) for chunk in batch]
        response = client.embeddings.create(
            model=config.deployment,
            input=texts,
            dimensions=config.dimensions,
        )
        embeddings = sorted(response.data, key=lambda item: item.index)
        if len(embeddings) != len(batch):
            raise RuntimeError("Embedding response size does not match the request")

        for chunk, item in zip(batch, embeddings, strict=True):
            vector = list(item.embedding)
            if len(vector) != config.dimensions:
                raise RuntimeError(
                    f"Unexpected embedding dimensions for {chunk['chunk_id']}: "
                    f"{len(vector)}"
                )
            records.append({**chunk, "content_vector": vector})

    return records


def write_embeddings(
    records: list[dict[str, object]],
    config: EmbeddingConfig,
    source_chunks_sha256: str,
    overwrite: bool,
) -> str:
    payload = {
        "schema_version": "1.0.0",
        "source_chunks_sha256": source_chunks_sha256,
        "embedding_deployment": config.deployment,
        "embedding_dimensions": config.dimensions,
        "records": records,
    }
    serialised = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    mode = "w" if overwrite else "x"
    try:
        with OUTPUT_PATH.open(mode, encoding="utf-8", newline="\n") as output:
            output.write(serialised)
    except FileExistsError as error:
        raise RuntimeError(
            f"Embedding file already exists and will not be overwritten: {OUTPUT_PATH}"
        ) from error

    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate local embeddings for deterministic document chunks."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the chunk input without authenticating or calling Azure.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly overwrite the local embeddings JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    chunks = load_chunks(INPUT_PATH)

    if args.dry_run:
        print("Embedding dry run passed")
        print(f"Chunks ready: {len(chunks)}")
        print(f"Batches at {BATCH_SIZE} chunks: {(len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE}")
        print("Azure authentication and embedding requests: not performed")
        return

    config = load_config()
    records = embed_chunks(chunks, config)
    output_sha256 = write_embeddings(
        records,
        config,
        sha256_file(INPUT_PATH),
        args.overwrite,
    )

    print("Local embedding generation completed")
    print(f"Records: {len(records)}")
    print(f"JSON: {OUTPUT_PATH}")
    print(f"SHA-256 JSON: {output_sha256}")
    print("Azure AI Search index and document upload: not performed")


if __name__ == "__main__":
    main()
