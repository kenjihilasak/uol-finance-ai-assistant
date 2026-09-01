# Portfolio UI decision

## Decision

Use the existing Astro portfolio on GitHub Pages for both the case study and a
small interactive chat. Host the Python API on the existing Railway Hobby
account. Keep Azure AI Search and Microsoft Foundry as the managed AI services.

```text
Astro portfolio on GitHub Pages
  -> HTTPS request to Railway FastAPI
  -> Entra ID application credential
  -> Azure AI Search + Microsoft Foundry
```

Frontend hosting is not the main engineering evidence. Retrieval evaluation,
grounding, citations, abstention, API design, identity, and cost controls are.

## Why not the other UI options?

| Option | Decision | Reason |
| --- | --- | --- |
| Existing Astro portfolio | Use | One public site and minimal client code |
| Railway FastAPI | Use | Existing account and standard Python API skills |
| Azure Static Web Apps | Skip | Duplicates the existing static site |
| Azure Functions | Defer | Managed identity is useful, but not required for this scale |
| Power Apps | Skip | Better suited to an internal low-code application |
| Copilot Studio | Skip | Adds an agent abstraction without improving this evaluated RAG |

## Public experience

The portfolio page exposes:

- the documents currently available to the RAG system;
- an official link to each PDF;
- suggested and free-text questions;
- answered or abstained status;
- cited page, excerpt, and direct `#page=N` PDF link;
- measured retrieval and abstention results.

The browser never receives an Azure credential. The API validates the question,
restricts the document ID to a public catalog, applies a request limit, and can
disable all live model calls with `API_LIVE_ENABLED=false`.

## CORS is not authentication

Cross-Origin Resource Sharing (CORS) is a browser policy. The API allows browser
requests only from the portfolio origin and local Astro development. This
prevents an unrelated webpage from calling the API through a visitor's browser,
but it does not stop scripts or direct HTTP clients. Rate limits, input
validation, cost budgets, and the live kill switch are still required.

## Future ingestion

The current public UI is read-only. A later authenticated operator interface may
accept either a local PDF upload or an HTTPS URL. It must remain separate from
the public chat and add:

- Entra ID operator authentication and authorization;
- size, content-type, PDF signature, and hash checks;
- explicit rights and public-source metadata;
- URL redirect and DNS/IP validation to prevent server-side request forgery;
- malware scanning, immutable Blob storage, and asynchronous processing;
- index versioning and a review step before publication.

Until that stage exists, add public document links manually to
`config/public_documents.json`.
