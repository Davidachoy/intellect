"""Strip PII field names from document metadata before storage."""

from __future__ import annotations

from typing import Any

_PII_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "email",
        "e_mail",
        "mail",
        "name",
        "first_name",
        "last_name",
        "full_name",
        "customer_name",
        "user_name",
        "display_name",
        "phone",
        "phone_number",
        "mobile",
        "tel",
        "telephone",
    }
)


def _normalize_key(key: str) -> str:
    return key.lower().replace("-", "_").replace(" ", "_")


def is_pii_metadata_key(key: str) -> bool:
    """Return True when the metadata key should be removed (PII)."""
    normalized = _normalize_key(key)
    if normalized in _PII_METADATA_KEYS:
        return True
    for pii_key in _PII_METADATA_KEYS:
        if normalized.endswith(f"_{pii_key}") or normalized.startswith(f"{pii_key}_"):
            return True
    return False


def strip_pii_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of metadata with PII keys removed (recursive for nested dicts)."""
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if is_pii_metadata_key(key):
            continue
        if isinstance(value, dict):
            cleaned[key] = strip_pii_from_metadata(value)
        elif isinstance(value, list):
            cleaned[key] = [
                strip_pii_from_metadata(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned
