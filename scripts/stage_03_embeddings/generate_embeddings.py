from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from scripts.shared.document_utils import (
    PROJECT_ROOT,
    processed_path,
    sha256_file,
    sha256_text,
)


BATCH_SIZE = 16
OPENAI_SCOPE = "https://ai.azure.com/.default"


@dataclass(frozen=True)
class EmbeddingConfig:
    tenant_id: str
    endpoint: str
    deployment: str
    dimensions: int


def batches(
    values: list[dict[str, object]], batch_size: int = BATCH_SIZE
) -> Iterator[list[dict[str, object]]]:
    for start in range(0, len(values), batch_size):
        yield values[start : start + batch_size]


def load_chunks(path: Path) -> tuple[str, list[dict[str, object]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Chunk file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Chunk JSON must be an object")

    document_id = payload.get("document_id")
    chunks = payload.get("chunks")
    if not isinstance(document_id, str):
        raise RuntimeError("Chunk file must contain document_id")
    if not isinstance(chunks, list) or not chunks:
        raise RuntimeError("Chunk file must contain a non-empty chunks list")

    chunk_ids: set[str] = set()
    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise RuntimeError("Every chunk must be an object")
        if chunk.get("document_id") != document_id:
            raise RuntimeError("Every chunk must match the payload document_id")
        chunk_id = chunk.get("chunk_id")
        text = chunk.get("text")
        if not isinstance(chunk_id, str) or not isinstance(text, str) or not text:
            raise RuntimeError("Every chunk must have a non-empty chunk_id and text")
        vector_text = chunk.get("embedding_text", text)
        if not isinstance(vector_text, str) or not vector_text:
            raise RuntimeError("embedding_text must be a non-empty string when present")
        if chunk_id in chunk_ids:
            raise RuntimeError(f"Duplicate chunk_id: {chunk_id}")
        chunk_ids.add(chunk_id)

    return document_id, chunks


def embedding_input(chunk: dict[str, object]) -> str:
    return str(chunk.get("embedding_text", chunk["text"]))


def load_config() -> EmbeddingConfig:
    load_dotenv(PROJECT_ROOT / ".env")
    required_names = (
        "AZURE_TENANT_ID",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_EMBEDDING_DEPLOYMENT",
        "AZURE_EMBEDDING_DIMENSIONS",
    )
    missing = [
        name
        for name in required_names
        if not os.getenv(name) or str(os.getenv(name)).startswith("<")
    ]
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


def embed_chunks(
    chunks: list[dict[str, object]], config: EmbeddingConfig
) -> list[dict[str, object]]:
    from azure.identity import (
        InteractiveBrowserCredential,
        get_bearer_token_provider,
    )
    from openai import OpenAI

    credential = InteractiveBrowserCredential(tenant_id=config.tenant_id)
    token_provider = get_bearer_token_provider(credential, OPENAI_SCOPE)
    client = OpenAI(
        base_url=openai_base_url(config.endpoint),
        api_key=token_provider,
    )
    records: list[dict[str, object]] = []

    try:
        for batch in batches(chunks):
            texts = [embedding_input(chunk) for chunk in batch]
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
                        f"Unexpected vector size for {chunk['chunk_id']}: {len(vector)}"
                    )
                records.append({**chunk, "content_vector": vector})
    finally:
        client.close()
        credential.close()

    return records


def write_embeddings(
    document_id: str,
    records: list[dict[str, object]],
    config: EmbeddingConfig,
    source_chunks_sha256: str,
    output_path: Path,
    overwrite: bool,
) -> str:
    payload = {
        "schema_version": "1.0.0",
        "document_id": document_id,
        "source_chunks_sha256": source_chunks_sha256,
        "embedding_deployment": config.deployment,
        "embedding_dimensions": config.dimensions,
        "records": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialised = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    mode = "w" if overwrite else "x"
    try:
        with output_path.open(mode, encoding="utf-8", newline="\n") as output:
            output.write(serialised)
    except FileExistsError as error:
        raise RuntimeError(
            f"Embedding file already exists and will not be overwritten: {output_path}"
        ) from error

    return sha256_text(serialised)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Azure embeddings for a document chunk file."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to a <document-id>.chunks.json file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate chunks without authenticating or calling Azure.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly overwrite the generated embeddings JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    document_id, chunks = load_chunks(args.input)

    if args.dry_run:
        print("Embedding dry run passed")
        print(f"Document ID: {document_id}")
        print(f"Chunks ready: {len(chunks)}")
        print(
            f"Batches at {BATCH_SIZE} chunks: "
            f"{(len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE}"
        )
        print("Azure authentication and embedding requests: not performed")
        return

    config = load_config()
    records = embed_chunks(chunks, config)
    output_path = processed_path(document_id, "embeddings")
    output_sha256 = write_embeddings(
        document_id,
        records,
        config,
        sha256_file(args.input),
        output_path,
        args.overwrite,
    )

    print("Local embedding generation completed")
    print(f"Records: {len(records)}")
    print(f"Output: {output_path}")
    print(f"Output SHA-256: {output_sha256}")
    print("Azure AI Search upload: not performed")


if __name__ == "__main__":
    main()
