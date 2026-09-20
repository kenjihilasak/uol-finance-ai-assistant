# Serving API and portfolio

## Implemented boundary

`api/main.py` exposes the public demo and protected staff routes:

| Route | Purpose | Contacts Azure |
| --- | --- | --- |
| `GET /health` | Railway health check | No |
| `GET /v1/documents` | Public PDFs and suggested questions | No |
| `POST /v1/answer` | Hybrid retrieval and grounded generation | Yes |
| `POST /v1/triage` | Classification, safe routing, and optional cited draft | Yes |
| `GET /v1/enquiries` | Persisted staff review queue | No |
| `PATCH /v1/enquiries/{id}` | Update review state | No |
| `GET /v1/enquiries/export.xlsx` | Download an Excel-compatible workbook | No |

The three enquiry-management routes require `X-Admin-Token`. A triage request
with `persist=true` requires the same header. The public portfolio sends
`persist=false`, preventing anonymous visitors from writing to the staff queue.

Run locally:

```bash
uvicorn api.main:app --reload --port 8000
```

Live calls are disabled by default. Set `API_LIVE_ENABLED=true` only when the
Azure configuration is ready.

## Railway configuration

Railway uses `railway.toml`. Configure these private variables:

```text
AZURE_AUTH_METHOD=service_principal
AZURE_TENANT_ID
AZURE_CLIENT_ID
AZURE_CLIENT_SECRET
AZURE_OPENAI_ENDPOINT
AZURE_CHAT_DEPLOYMENT
AZURE_EMBEDDING_DEPLOYMENT
AZURE_EMBEDDING_DIMENSIONS
AZURE_SEARCH_ENDPOINT
AZURE_SEARCH_INDEX_NAME
API_ALLOWED_ORIGINS=https://kenjihilasak.github.io
API_MAX_REQUESTS_PER_MINUTE=5
API_LIVE_ENABLED=true
API_ADMIN_TOKEN=<long-random-value>
DATABASE_URL=<injected-by-railway-postgres>
```

The Entra application needs only data-plane access required to read the search
index and invoke the model deployments. It does not need subscription Owner or
Contributor. Rotate the client secret and never put it in GitHub Pages.

Deployment checklist:

1. Create a Railway project from this GitHub repository.
2. Add a PostgreSQL service; Railway supplies `DATABASE_URL` to the API service.
3. Add the private variables above to the API service.
4. Deploy and confirm `https://<service>.up.railway.app/health` returns
   `{"status":"ok"}`.
5. In the portfolio GitHub repository, create the repository variable
   `PUBLIC_AGENTIC_SUPPORT_API_URL` with that origin (no trailing slash).
6. Run the portfolio Pages workflow or merge its feature branch into `master`.

The backend repository contains no Railway or Azure secrets. `railway.toml`
defines only the build, start, health-check, and restart behavior.

## Portfolio configuration

Set this build-time variable in the portfolio deployment:

```text
PUBLIC_AGENTIC_SUPPORT_API_URL=https://your-service.up.railway.app
```

Without it, the case study and official PDF link still work; the UI clearly
reports that the live API is not deployed.

## Persistence and Excel

Railway PostgreSQL is the system of record. Sensitive enquiry text is replaced
with a redaction marker before storage. The protected export endpoint generates
an `.xlsx` file that staff can open or upload to Excel Online.

Writing directly into an Excel Online table through Microsoft Graph is not the
default because the workbook row API requires delegated work-or-school access;
it does not support the service-principal application permission used by the
Railway backend. PostgreSQL plus explicit export keeps the demo reliable and
does not misrepresent that limitation.

## What Azure Functions would change

Azure Functions runs short HTTP or event-triggered functions without managing a
server. For this project it could replace Railway and provide native Managed
Identity: Azure creates the workload identity and no client secret is stored.
It also offers scale-to-zero and direct Azure monitoring.

Those are real production advantages, but the RAG logic and evaluation do not
improve merely because the Python endpoint is hosted there. Railway plus an
Entra service principal still demonstrates OAuth tokens and Azure RBAC.

Microsoft currently includes monthly free execution grants for Consumption and
Flex Consumption plans on eligible pay-as-you-go subscriptions. A small
portfolio API would normally remain within the execution allowance; storage,
networking, Search, and model tokens are separate charges. Always confirm the
active offer in the Azure pricing calculator before deployment.

## Cost shape

For the current small demo:

| Component | Expected shape |
| --- | --- |
| GitHub Pages | Existing free portfolio hosting |
| Railway API | Existing Hobby account allowance |
| Azure AI Search | Existing Free tier; no hourly Search charge |
| Blob Storage | A few GB or less; small variable storage charge |
| Query embeddings | Variable per question |
| `gpt-5-mini` | Variable by input and output tokens |
| Azure Functions alternative | Usually within the free execution grant at demo traffic |

The model calls, not the HTTP function, are the main variable cost. Keep the
public rate limit, Azure budget alerts, and `API_LIVE_ENABLED` kill switch.

Official references:

- [Azure Functions pricing](https://azure.microsoft.com/pricing/details/functions/)
- [Azure AI Search pricing](https://azure.microsoft.com/pricing/details/search/)
- [Azure free account and service allowances](https://azure.microsoft.com/pricing/purchase-options/azure-account)
