"""HTTP client for the EDGAR Events API.

Standard library only (urllib), so the package installs with one dependency
(the MCP SDK) and the data path can be tested without a network stack beyond
what ships with Python.

The API key is read by the caller from the environment and passed in; this
module never reads or logs it. Auth is an ``X-API-Key`` header.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://api.edgarevents.com"
USER_AGENT = "edgar-events-mcp/0.1 (+https://edgarevents.com)"


class EdgarEventsError(RuntimeError):
    """Any non-auth failure talking to the API (network, 5xx, bad JSON)."""


class AuthRequiredError(EdgarEventsError):
    """A paid endpoint was called without a valid API key (HTTP 401).

    Carried separately so the server can answer the agent with a short
    upgrade message instead of a stack trace.
    """


class RateLimitedError(EdgarEventsError):
    """The free sample hit its per-IP rate cap (HTTP 429)."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow redirects, so the X-API-Key header is never forwarded to a
    different host. A 3xx from the API then surfaces as a clear error."""

    def redirect_request(self, *args, **kwargs):  # noqa: D102
        return None


class Client:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        scheme = urllib.parse.urlsplit(self.base_url).scheme
        if scheme not in ("http", "https"):
            raise EdgarEventsError(
                f"base_url must be http or https, got {scheme or 'none'!r}"
            )
        self.api_key = api_key or None
        self.timeout = timeout
        self._opener = urllib.request.build_opener(_NoRedirect)

    def _get(self, path: str, params: dict | None = None, auth: bool = False) -> dict:
        query = ""
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                query = "?" + urllib.parse.urlencode(clean)
        url = f"{self.base_url}{path}{query}"
        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        if auth:
            if not self.api_key:
                raise AuthRequiredError("no API key configured")
            headers["X-API-Key"] = self.api_key
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:  # noqa: PERF203
            if e.code in (401, 403):
                raise AuthRequiredError("API key missing or invalid") from None
            if e.code == 429:
                raise RateLimitedError("rate limit reached") from None
            detail = _safe_detail(e)
            raise EdgarEventsError(f"HTTP {e.code} from {path}: {detail}") from None
        except urllib.error.URLError as e:
            raise EdgarEventsError(f"could not reach {self.base_url}: {e.reason}") from None
        except OSError as e:
            # read timeout / connection reset: socket.timeout, TimeoutError and
            # ConnectionResetError subclass OSError, not URLError
            raise EdgarEventsError(f"could not reach {self.base_url}: {e}") from None
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise EdgarEventsError(f"invalid JSON from {path}: {e}") from None

    # ---- endpoints ---------------------------------------------------------

    def try_activist_stakes(self) -> dict:
        """Free, no-key sample: the latest few resolved SC 13D stakes."""
        return self._get("/try/activist-stakes", auth=False)

    def activist_stakes(
        self,
        startdt: str | None = None,
        enddt: str | None = None,
        ticker: str | None = None,
        min_percent: float | None = None,
        include_amendments: bool = True,
        limit: int = 50,
    ) -> dict:
        """Full SC 13D activist-stake feed with filters (API key required)."""
        return self._get(
            "/activist-stakes",
            {
                "startdt": startdt,
                "enddt": enddt,
                "ticker": ticker,
                "min_percent": min_percent,
                "include_amendments": str(include_amendments).lower(),
                "limit": limit,
            },
            auth=True,
        )

    def filings(
        self,
        ticker: str | None = None,
        type: str | None = None,
        item: str | None = None,
        material: bool | None = None,
        since: str | None = None,
        hours: int = 48,
        limit: int = 100,
    ) -> dict:
        """Typed filing events across the tickers you name (API key required)."""
        return self._get(
            "/filings",
            {
                "ticker": ticker,
                "type": type,
                "item": item,
                "material": None if material is None else str(material).lower(),
                "since": since,
                "hours": hours,
                "limit": limit,
            },
            auth=True,
        )

    def ticker_filings(
        self,
        ticker: str,
        type: str | None = None,
        item: str | None = None,
        material: bool | None = None,
        hours: int = 72,
        limit: int = 100,
    ) -> dict:
        """Typed filing events for one ticker (API key required)."""
        sym = ticker.strip()
        if not sym:
            raise EdgarEventsError("ticker must not be empty")
        return self._get(
            # safe='' so a slash in an agent-supplied ticker can't traverse the path
            f"/filings/{urllib.parse.quote(sym, safe='')}",
            {
                "type": type,
                "item": item,
                "material": None if material is None else str(material).lower(),
                "hours": hours,
                "limit": limit,
            },
            auth=True,
        )


def _safe_detail(e: urllib.error.HTTPError) -> str:
    try:
        return e.read().decode("utf-8")[:300]
    except Exception:  # noqa: BLE001
        return e.reason or "error"
