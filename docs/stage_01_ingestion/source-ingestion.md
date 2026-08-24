# Source ingestion

Run commands from the repository root with the virtual environment active.
This workflow starts with a supplied PDF and never downloads from a URL.

## 1. Place the PDF

```text
data/sources/example-annual-report-2025.pdf
```

Only process approved documents. Do not commit the file.

## 2. Register it

```bash
python -m scripts.stage_01_ingestion.register_source_pdf \
  --file data/sources/example-annual-report-2025.pdf \
  --title "Example Annual Report 2025" \
  --institution "Example Institution" \
  --document-date 2025-07-31 \
  --status current \
  --source-reference "Provided by the document owner" \
  --usage-basis "Operator-confirmed portfolio analysis" \
  --rights-note "Do not redistribute the source document"
```

Optional provenance:

```bash
--source-url "https://example.org/reports/annual-report-2025"
```

Registration restricts paths to `data/sources/`, rejects symlinks, enforces the
size limit, checks the `%PDF-` header, computes SHA-256, detects duplicates, and
writes an ignored metadata sidecar. The header identifies the file format; it
is not a cryptographic signature. Usage fields record an operator decision, not
an automated legal determination.

## 3. Upload the source

```bash
python -m scripts.stage_01_ingestion.upload_source_blob \
  --file data/sources/example-annual-report-2025.pdf
```

The command uses Entra ID, prevents overwrite, and verifies the remote size and
SHA-256. Re-running it is safe when the existing blob is identical.

## 4. Extract text

```bash
python -m scripts.stage_02_processing.extract_pdf_text \
  --file data/sources/example-annual-report-2025.pdf
```

Output: `data/processed/<document-id>.processed.json`.

At least 80% of pages must contain extractable text by default. A lower result
requires review or a separate OCR path.

## 5. Create chunks

```bash
python -m scripts.stage_02_processing.chunk_extracted_text \
  --input data/processed/<document-id>.processed.json
```

Defaults: 1,800 characters, 200-character overlap, and no cross-page chunks.

## 6. Generate embeddings

Validate locally first:

```bash
python -m scripts.stage_03_embeddings.generate_embeddings \
  --input data/processed/<document-id>.chunks.json \
  --dry-run
```

Then call Azure:

```bash
python -m scripts.stage_03_embeddings.generate_embeddings \
  --input data/processed/<document-id>.chunks.json
```

Generated artifacts remain outside Git. Local commands require `--overwrite`
to replace outputs; registration uses `--overwrite-metadata`. Source blobs are
never overwritten.
