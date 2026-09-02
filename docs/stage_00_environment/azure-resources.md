# Azure resources

Concrete values belong in the ignored `.env` file.

## Current resource hierarchy

Inventory reviewed on 2 September 2026:

```text
Subscription: fee3971c-7410-4caf-8577-63579269a12b
└── Resource group: rg-uol-finance-ai-dev
    ├── Foundry resource: uol-finance-ai
    │   └── Foundry project: proj-uol-finance-ai
    ├── Foundry resource: luishilasaca-5075-resource
    │   └── Foundry project: luishilasaca-5075
    ├── Azure AI Search: uol-finance-search
    └── Storage account: stuolfinanceai
```

A Foundry project is a child resource of a Foundry account. Model deployments,
networking, and other settings can be shared through the parent resource; the
project is the workspace used for development and evaluation.

### Intended project hierarchy

`uol-finance-ai/proj-uol-finance-ai` is the hierarchy used by this repository.
It contains the `gpt-5-mini` and `text-embedding-3-small` deployments.

`uol-finance-search` contains the retrieval index and `stuolfinanceai` contains
the source, processed, and evaluation containers. Search and Storage are
separate resources, not children of the Foundry project.

### Additional hierarchy under review

`luishilasaca-5075-resource/luishilasaca-5075` is probably an automatically
generated resource and default project from an earlier Foundry quick-create
flow. This is an inference from its generated name, different region, and the
absence of model deployments observed in the portal; it is not yet proven.

Before deletion, verify the parent and child have no deployments, agents,
connections, data, indexes, evaluations, dependent resources, or recent cost.
Deletion is irreversible and requires explicit operator approval.

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

- Use Entra ID with `InteractiveBrowserCredential` on a local desktop. Set
  `AZURE_AUTH_METHOD=device_code` only for remote terminals where the tenant
  permits Device Code authentication.
- Use an Entra ID service principal with least-privilege RBAC on Railway.
- Prefer managed identity if the API is later moved to an Azure host.
- Keep tenant Security Defaults enabled.
- Never commit keys, connection strings, SAS tokens, access tokens, or secrets.
- Keep Azure containers private and grant least-privilege RBAC roles.
- If a secret is exposed, rotate it and remove it from Git history.

## Content rules

- Keep PDFs and generated artifacts outside Git.
- Treat source URLs as optional provenance, not proof of permission.
- Record usage or retention restrictions in the source metadata sidecar.
