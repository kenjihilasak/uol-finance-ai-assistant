# Serving API and portfolio

## Implemented boundary

`api/main.py` exposes three routes:

| Route | Purpose | Contacts Azure |
| --- | --- | --- |
| `GET /health` | Railway health check | No |
| `GET /v1/documents` | Public PDFs and suggested questions | No |
| `POST /v1/answer` | Hybrid retrieval and grounded generation | Yes |

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
```

The Entra application needs only data-plane access required to read the search
index and invoke the model deployments. It does not need subscription Owner or
Contributor. Rotate the client secret and never put it in GitHub Pages.

## Portfolio configuration

Set this build-time variable in the portfolio deployment:

```text
PUBLIC_UOL_FINANCE_API_URL=https://your-service.up.railway.app
```

Without it, the case study and official PDF link still work; the UI clearly
reports that the live API is not deployed.

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
