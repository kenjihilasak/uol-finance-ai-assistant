from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request


@dataclass(frozen=True)
class StaffIdentity:
    object_id: str
    display_name: str
    username: str | None


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise HTTPException(503, "Staff authentication is not configured")
    return value


def verify_staff_token(token: str) -> StaffIdentity:
    tenant_id = _required("STAFF_AUTH_TENANT_ID")
    audience = _required("STAFF_AUTH_API_CLIENT_ID")
    required_scope = os.getenv("STAFF_AUTH_REQUIRED_SCOPE", "Staff.Access").strip()
    allowed_ids = {
        value.strip()
        for value in _required("STAFF_AUTH_ALLOWED_OBJECT_IDS").split(",")
        if value.strip()
    }
    try:
        token_version = str(jwt.decode(token, options={"verify_signature": False}).get("ver", "2.0"))
        if token_version == "1.0":
            issuer = f"https://sts.windows.net/{tenant_id}/"
            valid_audiences = [audience, f"api://{audience}"]
        else:
            issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
            valid_audiences = [audience]
        signing_key = jwt.PyJWKClient(
            f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
            cache_keys=True,
        ).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=valid_audiences,
            issuer=issuer,
        )
    except jwt.PyJWTError as error:
        raise HTTPException(401, "Invalid or expired staff access token") from error
    if claims.get("tid") != tenant_id:
        raise HTTPException(403, "Staff tenant is not allowed")
    object_id = str(claims.get("oid", ""))
    if not object_id or object_id not in allowed_ids:
        raise HTTPException(403, "Staff user is not allowed")
    scopes = set(str(claims.get("scp", "")).split())
    if required_scope not in scopes:
        raise HTTPException(403, "Required staff scope is missing")
    return StaffIdentity(
        object_id=object_id,
        display_name=str(claims.get("name") or claims.get("preferred_username") or object_id),
        username=claims.get("preferred_username"),
    )


def require_staff(request: Request) -> StaffIdentity:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Bearer access token required")
    return verify_staff_token(token)
