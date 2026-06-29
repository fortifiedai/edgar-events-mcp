<!-- mcp-name: io.github.reedox/edgar-events-mcp -->

# EDGAR Events MCP server

Give an AI agent live SEC filing events: resolved SC 13D activist stakes
(holder, target, percent of class, shares) and typed 8-K, S-1 and merger
filings. It wraps the [EDGAR Events](https://edgarevents.com) API.

One tool works with no API key, so you can wire it up and test it in under a
minute:

- `get_recent_activist_stakes` returns the latest resolved 13D / 13D-A filings,
  parsed from each filing's cover-page XML into holder, target ticker, percent
  of class and share count. No key, no signup.

The filtered feeds need a key (a free tool is the preview; the key is the
upgrade):

- `get_activist_stakes` — the full 13D feed with date-range, ticker and
  minimum-percent filters.
- `get_filings` — typed filing events across the tickers you name, filterable
  by form type, 8-K item code, materiality and lookback window.
- `get_ticker_filings` — the same, scoped to one ticker.

Without a key, the filtered tools reply with a short note on how to get one
instead of erroring, so an agent degrades gracefully to the free preview.

## Why activist 13D data

Most SEC APIs hand back a filing's metadata and a link, leaving you to fetch
and parse the document. EDGAR Events reads the SC 13D cover page and returns
the numbers an agent actually needs: who filed, against which ticker, the
percent of class, and the share count. `get_recent_activist_stakes` shows real
resolved rows, not pointers.

## Install

The server runs over stdio and installs from PyPI. With
[uv](https://docs.astral.sh/uv/) you do not install anything ahead of time:

```bash
uvx edgar-events-mcp
```

Or with pip:

```bash
pip install edgar-events-mcp
edgar-events-mcp
```

To run the latest from source before the next release:

```bash
pip install git+https://github.com/reedox/edgar-events-mcp
```

## Claude Desktop

Add this to `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "edgar-events": {
      "command": "uvx",
      "args": ["edgar-events-mcp"],
      "env": {
        "EDGAR_EVENTS_API_KEY": "your-key-or-omit-for-the-free-tool"
      }
    }
  }
}
```

Drop the `env` block to run with only the free `get_recent_activist_stakes`
tool. Restart Claude Desktop after editing. The same `command`/`args`/`env`
shape works in any MCP client (Cursor, Cline, Continue, and others).

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `EDGAR_EVENTS_API_KEY` | unset | Your key. Required for the filtered feeds. Get one at https://edgarevents.com/subscribe |
| `EDGAR_EVENTS_BASE_URL` | `https://api.edgarevents.com` | Override the API host. |

The key is read from the environment and sent as the `X-API-Key` header. It is
never logged.

## Example prompts

Once connected, ask:

- "Who just took an activist stake in a public company?" → `get_recent_activist_stakes`
- "Show me 13D filings above 10% of class since June 1." → `get_activist_stakes`
- "Did AAPL or MSFT file any material 8-Ks in the last day?" → `get_filings`
- "List NVDA's recent 8-K item 2.02 filings." → `get_ticker_filings`

## Tools

| Tool | Key needed | Returns |
| --- | --- | --- |
| `get_recent_activist_stakes` | no | Latest few resolved 13D stakes |
| `get_activist_stakes` | yes | Full 13D feed, filtered |
| `get_filings` | yes | Typed filings across named tickers |
| `get_ticker_filings` | yes | Typed filings for one ticker |

## Development

```bash
pip install -e .
EDGAR_EVENTS_LIVE=1 pytest        # the live test hits the public API
```

The HTTP client (`client.py`) uses only the standard library; the server adds
the MCP SDK. Data comes from SEC EDGAR via the EDGAR Events API.

## License

MIT
