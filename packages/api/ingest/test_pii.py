"""Unit tests for metadata PII stripping."""

from ingest.pii import is_pii_metadata_key, strip_pii_from_metadata


def test_strips_email_name_phone_keys() -> None:
    metadata = {
        "region": "Italy",
        "segment": "enterprise",
        "email": "user@example.com",
        "name": "Jane Doe",
        "phone": "+1-555-0100",
    }
    cleaned = strip_pii_from_metadata(metadata)
    assert cleaned == {"region": "Italy", "segment": "enterprise"}


def test_strips_normalized_key_variants() -> None:
    metadata = {
        "customer-email": "a@b.co",
        "First Name": "Jane",
        "phone_number": "555",
        "status": "active",
    }
    cleaned = strip_pii_from_metadata(metadata)
    assert cleaned == {"status": "active"}


def test_strips_nested_pii_keys() -> None:
    metadata = {
        "filters": {
            "region": "Italy",
            "contact": {"email": "x@y.com", "tier": "gold"},
        },
    }
    cleaned = strip_pii_from_metadata(metadata)
    assert cleaned == {"filters": {"region": "Italy", "contact": {"tier": "gold"}}}


def test_is_pii_metadata_key_suffix_prefix() -> None:
    assert is_pii_metadata_key("user_email")
    assert is_pii_metadata_key("phone_mobile")
    assert not is_pii_metadata_key("region")
