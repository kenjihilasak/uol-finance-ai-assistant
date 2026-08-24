# Source ingestion guide

This workflow starts with a PDF already supplied to the project. It never
downloads from a URL.

Commands assume the virtual environment is active and the current directory is
the repository root.

## 1. Place the PDF locally

Copy the file into the ignored source directory:

```text
data/sources/example-annual-report-2025.pdf
```

Only process documents you are authorised to use. Do not commit the file.

## 2. Register and validate it

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

If an official page is useful for provenance, add:

```bash
--source-url "https://example.org/reports/annual-report-2025"
```

The URL is optional and is stored only as metadata. Registration verifies that
the path stays under `data/sources/`, rejects symlinks, enforces the size limit,
checks the `%PDF-` format header, computes SHA-256, detects duplicate content,
and writes an ignored `*.metadata.json` sidecar. The header check confirms file
format; it is not a cryptographic PDF signature.

The `usage_basis` and `rights_note` fields record an operator decision. They are
not an automated legal determination.

## 3. Upload the immutable source

```bash
python -m scripts.stage_01_ingestion.upload_source_blob \
  --file data/sources/example-annual-report-2025.pdf
```

The command revalidates the sidecar, uploads with Entra ID, prevents overwrite,
and downloads the blob to verify size and SHA-256. Re-running the command is
safe when the existing remote bytes are identical.

## 4. Extract page-level text

```bash
python -m scripts.stage_02_processing.extract_pdf_text \
  --file data/sources/example-annual-report-2025.pdf
```

The command prints the generated path:

```text
data/processed/<document-id>.processed.json
```

By default at least 80% of pages must contain extractable text. A lower result
usually means the PDF needs an OCR path, which is intentionally not hidden in
this baseline.

## 5. Create deterministic chunks

Use the actual `<document-id>` printed during registration:

```bash
python -m scripts.stage_02_processing.chunk_extracted_text \
  --input data/processed/<document-id>.processed.json
```

Defaults are 1,800 characters with 200 characters of overlap, and chunks never
cross a physical PDF page.

## 6. Validate or generate embeddings

Validate locally without signing in or calling Azure:

```bash
python -m scripts.stage_03_embeddings.generate_embeddings \
  --input data/processed/<document-id>.chunks.json \
  --dry-run
```

Generate embeddings after the dry run passes:

```bash
python -m scripts.stage_03_embeddings.generate_embeddings \
  --input data/processed/<document-id>.chunks.json
```

Generated artifacts remain ignored by Git. The next project stage uploads the
embedding records to a versioned Azure AI Search index.

## Overwrite behavior

Local processing commands do not overwrite artifacts by default. Use
`--overwrite` only when deliberately regenerating processed JSON, chunks, or
embeddings. Registration uses the more explicit `--overwrite-metadata`; it
never modifies the PDF. Azure source blobs are never overwritten by this flow.
