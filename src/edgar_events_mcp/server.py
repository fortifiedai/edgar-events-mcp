"""EDGAR Events MCP server.

Gives an AI agent structured SEC filing events: resolved SC 13D activist
stakes (holder, target, percent of class, shares) and typed 8-K / S-1 / merger
filings, pulled from the EDGAR Events API at https://edgarevents.com.

One tool is free and needs no key: ``get_recent_activist_stakes`` returns a
live sample of the latest resolved 13D filings. The filtered feeds need an API
key (env ``EDGAR_EVENTS_API_KEY``); without one those tools answer with a short
note on how to get a key rather than failing.
"""

from __future__ import annotations

import json
import os

from mcp.server.fastmcp import FastMCP

from .client import AuthRequiredError, Client, EdgarEventsError, RateLimitedError

BASE_URL = os.environ.get("EDGAR_EVENTS_BASE_URL", "https://api.edgarevents.com")
SUBSCRIBE_URL = "https://edgarevents.com/subscribe"

mcp = FastMCP("edgar-events")


def _client() -> Client:
    return Client(base_url=BASE_URL, api_key=os.environ.get("EDGAR_EVENTS_API_KEY"))


def _upgrade_note(feed: str) -> str:
    return (
        f"This feed needs an EDGAR Events API key. Set the EDGAR_EVENTS_API_KEY "
        f"environment variable for this MCP server, then call {feed} again. "
        f"Get a key at {SUBSCRIBE_URL}. For a free preview with no key, use "
        f"get_recent_activist_stakes."
    )


def _dump(obj: dict) -> str:
    return json.dumps(obj, indent=2, default=str)


@mcp.tool()
def get_recent_activist_stakes() -> str:
    """Latest resolved SC 13D activist stakes from SEC EDGAR. Free, no API key.

    Returns the most recent few 13D / 13D-A filings with the activist holder,
    the target company and ticker, the percent of class acquired, and the share
    count, parsed from each filing's structured cover page. Use this to answer
    "who just took an activist stake in what" or to preview the data before
    subscribing to the full feed.
    """
    try:
        data = _client().try_activist_stakes()
    except RateLimitedError:
        return (
            "The free sample is rate limited right now. Try again shortly, or "
            f"use an API key for the full feed: {SUBSCRIBE_URL}."
        )
    except EdgarEventsError as e:
        return f"EDGAR Events request failed: {e}"
    return _dump(data)


@mcp.tool()
def get_activist_stakes(
    startdt: str | None = None,
    enddt: str | None = None,
    ticker: str | None = None,
    min_percent: float | None = None,
    include_amendments: bool = True,
    limit: int = 50,
) -> str:
    """Filtered SC 13D activist-stake feed (API key required).

    The full version of get_recent_activist_stakes: filter by date range
    (startdt / enddt as YYYY-MM-DD), by target ticker, and by minimum percent
    of class. Set include_amendments=False to drop 13D/A follow-ups. Returns
    holder, target, percent of class and shares for each filing.
    """
    try:
        data = _client().activist_stakes(
            startdt=startdt,
            enddt=enddt,
            ticker=ticker,
            min_percent=min_percent,
            include_amendments=include_amendments,
            limit=limit,
        )
    except AuthRequiredError:
        return _upgrade_note("get_activist_stakes")
    except EdgarEventsError as e:
        return f"EDGAR Events request failed: {e}"
    return _dump(data)


@mcp.tool()
def get_filings(
    ticker: str | None = None,
    type: str | None = None,
    item: str | None = None,
    material: bool | None = None,
    since: str | None = None,
    hours: int = 48,
    limit: int = 100,
) -> str:
    """Typed filing events across the tickers you name (API key required).

    Polls SEC EDGAR for the tickers in ``ticker`` (comma-separated, e.g.
    "AAPL,MSFT"). Filter by form ``type`` (e.g. "8-K"), by 8-K ``item`` code
    (e.g. "2.02" for results of operations), by ``material`` events only, and
    by a ``since`` ISO datetime or an ``hours`` lookback window. Use this for
    "what did these companies just file" and 8-K event monitoring.
    """
    try:
        data = _client().filings(
            ticker=ticker,
            type=type,
            item=item,
            material=material,
            since=since,
            hours=hours,
            limit=limit,
        )
    except AuthRequiredError:
        return _upgrade_note("get_filings")
    except EdgarEventsError as e:
        return f"EDGAR Events request failed: {e}"
    return _dump(data)


@mcp.tool()
def get_ticker_filings(
    ticker: str,
    type: str | None = None,
    item: str | None = None,
    material: bool | None = None,
    hours: int = 72,
    limit: int = 100,
) -> str:
    """Typed filing events for a single ticker (API key required).

    Same data as get_filings, scoped to one company. Pass a ticker symbol and
    optionally a form ``type``, an 8-K ``item`` code, ``material`` only, and an
    ``hours`` lookback. Use this for "show me <TICKER>'s recent 8-Ks".
    """
    try:
        data = _client().ticker_filings(
            ticker=ticker,
            type=type,
            item=item,
            material=material,
            hours=hours,
            limit=limit,
        )
    except AuthRequiredError:
        return _upgrade_note("get_ticker_filings")
    except EdgarEventsError as e:
        return f"EDGAR Events request failed: {e}"
    return _dump(data)
