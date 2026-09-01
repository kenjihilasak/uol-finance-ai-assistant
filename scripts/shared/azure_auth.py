from __future__ import annotations

import os
from typing import Any


SUPPORTED_AUTH_METHODS = {
    "device_code",
    "interactive_browser",
    "service_principal",
}


def configured_auth_method() -> str:
    method = os.getenv("AZURE_AUTH_METHOD", "interactive_browser").strip().lower()
    if method not in SUPPORTED_AUTH_METHODS:
        supported = ", ".join(sorted(SUPPORTED_AUTH_METHODS))
        raise RuntimeError(
            f"Unsupported AZURE_AUTH_METHOD: {method}. Use one of: {supported}"
        )
    return method


def build_user_credential(tenant_id: str) -> Any:
    """Build an Entra ID credential for local or hosted execution."""
    from azure.identity import (
        ClientSecretCredential,
        DeviceCodeCredential,
        InteractiveBrowserCredential,
    )

    method = configured_auth_method()
    if method == "interactive_browser":
        return InteractiveBrowserCredential(tenant_id=tenant_id)
    if method == "device_code":
        return DeviceCodeCredential(tenant_id=tenant_id)

    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "service_principal authentication requires AZURE_CLIENT_ID and "
            "AZURE_CLIENT_SECRET"
        )
    return ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
