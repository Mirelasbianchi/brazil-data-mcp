"""HTTP clients for the public data sources used by the server.

Every call goes through `_get`, which retries transient failures (timeouts, 429, 5xx) with
exponential backoff and turns everything else into `UpstreamError` / `NotFoundError`
with a message an LLM can relay to the user.
"""

import asyncio
from datetime import date

import httpx

from brazil_data_mcp.cache import ttl_cache

BRASILAPI_URL = "https://brasilapi.com.br/api"
BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados"
BCB_PTAX_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoDolarDia(dataCotacao=@dataCotacao)"
)

TIMEOUT = httpx.Timeout(10.0)
RETRIES = 2
BACKOFF_S = 0.5
HOUR = 3600
DAY = 24 * HOUR


class UpstreamError(Exception):
    """A data source failed or answered with something unusable."""


class NotFoundError(UpstreamError):
    """The data source has no record for the requested key."""


async def _get(url: str, params: dict | None = None, source: str = "data source"):
    last_error: Exception | None = None
    for attempt in range(RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(url, params=params)
        except httpx.TransportError as exc:  # timeouts, DNS, connection resets
            last_error = exc
        else:
            if response.status_code == 404:
                raise NotFoundError(f"{source} has no record for this request")
            if response.status_code == 429 or response.status_code >= 500:
                last_error = UpstreamError(f"{source} answered HTTP {response.status_code}")
            elif response.status_code >= 400:
                raise UpstreamError(f"{source} rejected the request (HTTP {response.status_code})")
            else:
                return response.json()
        if attempt < RETRIES:
            await asyncio.sleep(BACKOFF_S * 2**attempt)
    raise UpstreamError(f"{source} is unavailable right now ({last_error}). Try again later.")


@ttl_cache(DAY)
async def brasilapi(path: str) -> dict | list:
    """GET a BrasilAPI endpoint, e.g. brasilapi("/cep/v2/01310100"). Cached for a day."""
    return await _get(f"{BRASILAPI_URL}{path}", source="BrasilAPI")


@ttl_cache(HOUR)
async def bcb_series(series: int, start: date, end: date) -> list[dict]:
    """Values of a Banco Central SGS series between two dates (inclusive). Cached for an hour.

    Uses the date-range endpoint rather than `ultimos/N`: some series (e.g. Selic target,
    432) publish values dated up to the next Copom meeting, so "last N" returns the future.
    """
    params = {
        "formato": "json",
        "dataInicial": start.strftime("%d/%m/%Y"),
        "dataFinal": end.strftime("%d/%m/%Y"),
    }
    return await _get(BCB_SGS_URL.format(series=series), params=params, source="Banco Central SGS")


@ttl_cache(HOUR)
async def bcb_ptax(day: date) -> list[dict]:
    """Official PTAX USD/BRL quotes for a given day (empty on weekends and holidays)."""
    params = {"@dataCotacao": f"'{day.strftime('%m-%d-%Y')}'", "$format": "json"}
    data = await _get(BCB_PTAX_URL, params=params, source="Banco Central PTAX")
    return data.get("value", [])
