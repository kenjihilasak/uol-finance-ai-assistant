# Portfolio UI options

## Decision

Use the existing Astro site at `kenjihilasak.github.io` as the project entry
point. Add this project to its typed case-study data and use the existing
`demo` link to open a small React and Fluent UI application hosted on Azure
Static Web Apps.

Keep the demo code in this repository because it belongs to the AI product.
Keep the portfolio repository focused on presenting the case study. Power Apps
can be a second, internal-style demonstration; it should not replace the public
experience.

| Option | Best use | Portfolio limitation |
| --- | --- | --- |
| Foundry playground | Configure and test models or agents | Development surface, not the public product UI |
| Power Apps canvas app | Rapid internal business application | Sharing and connectors depend on Power Platform licensing |
| Copilot Studio | Managed conversational agent | Licensing and less visibility into this custom RAG pipeline |
| Static Web Apps + Functions | Public code-first portfolio | Requires building a small API and frontend |

Microsoft documents the Power Apps Developer Plan as a free development and
test environment. It is useful for learning Power Fx and connectors, but does
not remove production sharing and licensing considerations.

## Recommended low-cost shape

```text
kenjihilasak.github.io (Astro case study)
  -> Open demo link
  -> React + Fluent UI on Azure Static Web Apps Free
  -> Azure Functions consumption API
  -> managed identity
  -> Azure AI Search Free + Microsoft Foundry
```

This keeps one public portfolio and gives each repository a clear
responsibility:

- `kenjihilasak.github.io`: project story, architecture, metrics, limitations,
  repository link, and demo link.
- `uol-finance-ai-assistant`: ingestion, retrieval, evaluation, API, and demo
  application.

Do not embed the demo in an iframe. A normal link is easier to use on mobile,
keeps browser history and accessibility intact, and makes the Azure deployment
boundary visible to reviewers.

The public site should have two modes:

- Recorded demo mode: sanitized example responses, no Azure model call.
- Rate-limited live mode: explicit user action, a few curated questions, and a
  server-side kill switch.

Never call Search or Foundry directly from browser code. The Function should
hold the managed identity, validate input, enforce limits, and return only the
answer and citation metadata.

## Portfolio integration checklist

When the API and UI are ready:

1. Add `uol-finance-ai-assistant` to `src/data/site.ts` in the portfolio.
2. Add its evidence-led narrative to `src/data/caseStudies.ts`.
3. Include measured retrieval and abstention results, not estimated metrics.
4. Set `github` to this repository and `demo` to the Static Web Apps URL.
5. Add the project slug to the selected-work ordering.
6. Test both links and the mobile layout before publishing.

If Azure credit is unavailable, the case study and a recorded-response mode
remain public while live generation is disabled. This prevents an expired
subscription from leaving a broken portfolio page.

## References

- [Microsoft Foundry Agent Service](https://learn.microsoft.com/azure/foundry/agents/overview)
- [Power Apps Developer Plan](https://learn.microsoft.com/power-platform/developer/plan)
- [Power Platform licensing overview](https://learn.microsoft.com/power-platform/admin/pricing-billing-skus)
- [Azure Static Web Apps pricing](https://azure.microsoft.com/pricing/details/app-service/static/)
- [Azure Functions pricing](https://azure.microsoft.com/pricing/details/functions/)
