"""Tests for the EDGAR Events client.

Offline tests run with no network. The live test hits the public API and is
skipped unless EDGAR_EVENTS_LIVE=1 is set, so CI without egress stays green.
"""

import os

import pytest

from edgar_events_mcp.client import (
    AuthRequiredError,
    Client,
    DEFAULT_BASE_URL,
)


def test_base_url_normalised():
    assert Client(base_url="https://x.test/").base_url == "https://x.test"
    assert Client().base_url == DEFAULT_BASE_URL


def test_paid_call_without_key_raises_auth():
    c = Client(api_key=None)
    with pytest.raises(AuthRequiredError):
        c.activist_stakes(limit=1)
    with pytest.raises(AuthRequiredError):
        c.filings(ticker="AAPL")


@pytest.mark.skipif(
    os.environ.get("EDGAR_EVENTS_LIVE") != "1",
    reason="set EDGAR_EVENTS_LIVE=1 to hit the public API",
)
def test_try_activist_stakes_live():
    data = Client().try_activist_stakes()
    assert data["sample"] is True
    assert isinstance(data["events"], list)
    if data["events"]:
        ev = data["events"][0]
        assert "target" in ev and "holders" in ev
