from __future__ import annotations

import os
from typing import Any


SUPPORTED_AUTH_METHODS = {"device_code", "interactive_browser"}


def configured_auth_method() -> str:
    method = os.getenv("AZURE_AUTH_METHOD", "interactive_browser").strip().lower()
    if method not in SUPPORTED_AUTH_METHODS:
        supported = ", ".join(sorted(SUPPORTED_AUTH_METHODS))
        raise RuntimeError(
            f"Unsupported AZURE_AUTH_METHOD: {method}. Use one of: {supported}"
        )
    return method


def build_user_credential(tenant_id: str) -> Any:
    """Build a user credential suitable for local or remote development."""
    from azure.identity import DeviceCodeCredential, InteractiveBrowserCredential

    if configured_auth_method() == "interactive_browser":
        return InteractiveBrowserCredential(tenant_id=tenant_id)
    return DeviceCodeCredential(tenant_id=tenant_id)
