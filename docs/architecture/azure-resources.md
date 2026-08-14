# Azure resource inventory

This document records the resource types and responsibilities used by the project. Concrete environment values are kept in the local `.env` file and are not committed.

| Resource | Purpose | Local environment variable |
| --- | --- | --- |
| Azure region | Keeps the initial resources geographically aligned | `AZURE_LOCATION` |
| Azure subscription | Identifies the billing and management boundary | `AZURE_SUBSCRIPTION_ID` |
| Resource group | Groups the project's Azure resources for management | `AZURE_RESOURCE_GROUP` |
| Storage account | Stores original, processed, and evaluation documents | `AZURE_STORAGE_ACCOUNT_NAME` |
| `source-documents` container | Immutable copies of original public documents | `AZURE_STORAGE_SOURCE_CONTAINER` |
| `processed-documents` container | Extracted and cleaned document representations | `AZURE_STORAGE_PROCESSED_CONTAINER` |
| `evaluation-data` container | Evaluation questions, expected evidence, and results | `AZURE_STORAGE_EVALUATION_CONTAINER` |
| Azure AI Search | Stores searchable text, metadata, and embedding vectors | `AZURE_SEARCH_ENDPOINT` |
| Search index | Versioned schema used by the retrieval pipeline | `AZURE_SEARCH_INDEX_NAME` |
| Microsoft Foundry project | Provides access to deployed AI models | `FOUNDRY_PROJECT_ENDPOINT` |
| Chat deployment | Produces grounded answers from retrieved evidence | `AZURE_CHAT_DEPLOYMENT` |
| Embedding deployment | Converts text and questions into vectors | `AZURE_EMBEDDING_DEPLOYMENT` |

## Secret-handling policy

- Never commit admin keys, API keys, storage connection strings, SAS tokens, access tokens, or client secrets.
- Local development authenticates through Microsoft Entra ID using
  `InteractiveBrowserCredential` with `AZURE_TENANT_ID`.
- Keep Microsoft Entra Security Defaults enabled. This project does not use the
  device code flow because it is blocked by the tenant's security policy.
- Deployed workloads should authenticate through a managed identity.
- If a secret is ever committed, deleting it from the latest file is insufficient: rotate the credential immediately and remove it from Git history.
