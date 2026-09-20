# Staff authentication

The public route `POST /v1/triage` never persists. The protected route
`POST /v1/staff/triage` requires an Entra access token and always persists the
result in PostgreSQL. The server, not a browser-controlled flag, decides this
boundary.

Use separate single-tenant app registrations:

- `agentic-support-staff-api`: exposes delegated scope `Staff.Access`.
- `agentic-support-staff-web`: SPA client allowed to request that scope.

FastAPI validates the token signature, issuer, audience, tenant, delegated
scope, and a fail-closed allowlist of staff Object IDs. Stored records include
the staff Object ID and display name; access tokens are never stored.

Backend variables:

```text
STAFF_AUTH_TENANT_ID
STAFF_AUTH_API_CLIENT_ID
STAFF_AUTH_REQUIRED_SCOPE=Staff.Access
STAFF_AUTH_ALLOWED_OBJECT_IDS
```

GitHub Pages repository variables:

```text
PUBLIC_STAFF_AUTH_TENANT_ID
PUBLIC_STAFF_AUTH_WEB_CLIENT_ID
PUBLIC_STAFF_AUTH_API_SCOPE=api://<api-client-id>/Staff.Access
```

The production SPA redirect URI is:

```text
https://kenjihilasak.github.io/work/agentic-support-intelligence/
```
