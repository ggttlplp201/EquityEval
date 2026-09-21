"""Contact configuration is validated without consulting application settings."""

import pytest

from scripts.bootstrap_crcl import contact_from_settings


@pytest.mark.parametrize(
    "value",
    ["", "no email", "test@example.com", "test@example.invalid", "one@sample.net two@sample.net"],
)
def test_missing_or_placeholder_contact_is_not_invented(monkeypatch, value):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    with pytest.raises(ValueError):
        contact_from_settings({"SEC_USER_AGENT": value})


def test_existing_single_contact_is_used_verbatim(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    assert (
        contact_from_settings({"SEC_USER_AGENT": "EquityEval person@sample.net"})
        == "person@sample.net"
    )
