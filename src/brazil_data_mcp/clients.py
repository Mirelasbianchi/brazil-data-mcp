"""HTTP clients for the public data sources used by the server."""

from datetime import date

import httpx

BRASILAPI_URL = "https://brasilapi.com.br/api"
BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados/ultimos/{n}"
BCB_PTAX_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoDolarDia(dataCotacao=@dataCotacao)"
)

TIMEOUT = httpx.Timeout(10.0)


async def _get(url: str, params: dict | None = None) -> dict | list:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def brasilapi(path: str) -> dict | list:
    """GET a BrasilAPI endpoint, e.g. brasilapi("/cep/v2/01310100")."""
    return await _get(f"{BRASILAPI_URL}{path}")


async def bcb_series(series: int, last: int = 1) -> list[dict]:
    """Last `last` values of a Banco Central SGS time series."""
    url = BCB_SGS_URL.format(series=series, n=last)
    return await _get(url, params={"formato": "json"})


async def bcb_ptax(day: date) -> list[dict]:
    """Official PTAX USD/BRL quotes for a given day (empty on weekends and holidays)."""
    params = {"@dataCotacao": f"'{day.strftime('%m-%d-%Y')}'", "$format": "json"}
    data = await _get(BCB_PTAX_URL, params=params)
    return data.get("value", [])
