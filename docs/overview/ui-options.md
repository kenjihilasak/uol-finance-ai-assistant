# UI and hosting decision

## Current choice

Use the existing Astro portfolio on GitHub Pages and host FastAPI plus
PostgreSQL on Railway. Keep Microsoft Foundry, Azure AI Search, Blob Storage and
Entra ID as the managed Microsoft services.

This avoids duplicating the portfolio on another static host while keeping the
AI engineering, identity and evaluation visible.

## User modes

| Mode | Behaviour |
| --- | --- |
| Public demo | Synthetic enquiry, live result, no persistence |
| Entra-authenticated staff | Persist result, review queue, status updates and XLSX export |

The browser receives no Azure service credential. CORS restricts browser
origins but is not authentication; the API also applies validation, throttling
and a live-generation switch.

## Alternatives

| Option | Current decision |
| --- | --- |
| Azure Static Web Apps | Not needed while GitHub Pages hosts the portfolio |
| Azure Container Apps | Sensible future replacement for Railway FastAPI |
| Power Apps / Teams | Useful future internal staff experience |
| Copilot Studio | Optional channel, not the authoritative AI pipeline |

See [API and portfolio](../stage_07_serving/api-and-portfolio.md) and
[staff authentication](../stage_07_serving/staff-authentication.md).
