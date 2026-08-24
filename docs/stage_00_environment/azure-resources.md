# Azure resources

Concrete values belong in the ignored `.env` file.

| Resource | Purpose | Environment variable |
| --- | --- | --- |
| Region | Align initial resources | `AZURE_LOCATION` |
| Subscription | Billing and management boundary | `AZURE_SUBSCRIPTION_ID` |
| Resource group | Group project resources | `AZURE_RESOURCE_GROUP` |
| Storage account | Store source, processed, and evaluation data | `AZURE_STORAGE_ACCOUNT_NAME` |
| `source-documents` | Preserve approved source PDFs | `AZURE_STORAGE_SOURCE_CONTAINER` |
| `processed-documents` | Store processed artifacts | `AZURE_STORAGE_PROCESSED_CONTAINER` |
| `evaluation-data` | Store evaluation inputs and results | `AZURE_STORAGE_EVALUATION_CONTAINER` |
| Azure AI Search | Store text, metadata, and vectors | `AZURE_SEARCH_ENDPOINT` |
| Search index | Version the retrieval schema | `AZURE_SEARCH_INDEX_NAME` |
| Foundry project | Group model deployments | `FOUNDRY_PROJECT_ENDPOINT` |
| Chat deployment | Generate grounded answers | `AZURE_CHAT_DEPLOYMENT` |
| Embedding deployment | Generate vectors | `AZURE_EMBEDDING_DEPLOYMENT` |

## Security rules

- Use Entra ID with `InteractiveBrowserCredential` for local development.
- Use managed identity for deployed workloads.
- Keep tenant Security Defaults enabled.
- Never commit keys, connection strings, SAS tokens, access tokens, or secrets.
- Keep Azure containers private and grant least-privilege RBAC roles.
- If a secret is exposed, rotate it and remove it from Git history.

## Content rules

- Keep PDFs and generated artifacts outside Git.
- Treat source URLs as optional provenance, not proof of permission.
- Record usage or retention restrictions in the source metadata sidecar.
