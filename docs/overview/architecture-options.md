# Architecture options

The evaluated classification, routing, retrieval and citation contracts remain
the same across hosting choices.

| Concern | Current portfolio | Azure-native | Azure + Power Platform |
| --- | --- | --- | --- |
| Frontend | GitHub Pages | Azure Static Web Apps | Power Apps or Teams tab |
| API | Railway FastAPI | Azure Container Apps | Container Apps behind a custom connector |
| Case store | Railway PostgreSQL | Azure PostgreSQL | Dataverse |
| Backend identity | Entra service principal | Managed Identity | Managed Identity + delegated connector |
| Ingestion | Local Python stages | Blob events + Azure Functions | Same Azure pipeline with Power Apps review |
| Operations | Railway logs | Application Insights | Azure Monitor + Power Platform analytics |
| Main benefit | Low cost and portfolio fit | Unified Azure operations | Microsoft 365 case workflow |
| Main trade-off | Split platforms | More cost and infrastructure | Licensing and low-code complexity |

## Recommendation

Keep the current architecture for the public portfolio. For an enterprise
extension:

1. move FastAPI to Azure Container Apps and replace the secret with Managed
   Identity;
2. add Application Insights and governed source ingestion; and
3. add Power Apps or a Teams tab only if staff workflow integration is needed.

Power Automate can provide notifications and approvals, while Dataverse can
hold operational cases. The protected FastAPI service should remain the single
implementation of triage and safety policy.

Copilot Studio may provide an optional conversational Teams channel, but it
should call the same API rather than create a second classification or
retrieval path.

See the [deployed architecture](project-architecture.md) and
[UI decision](ui-options.md).
