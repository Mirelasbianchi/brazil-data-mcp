"""MCP server exposing Brazilian public data as tools."""

import argparse
import math
from datetime import date, datetime, timedelta
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from brazil_data_mcp import __version__, clients, validation

mcp = MCPServer(
    "brazil-data",
    version=__version__,
    instructions=(
        "Brazilian public data: addresses by CEP, companies by CNPJ, banks, holidays, area "
        "codes, municipalities, Selic, IPCA and the official PTAX dollar rate. Values come "
        "from BrasilAPI and Banco Central; cite the source and date when you answer."
    ),
)

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=True, idempotent_hint=True)
SELIC_TARGET_SERIES = 432
IPCA_MONTHLY_SERIES = 433


def _today() -> date:
    return date.today()


async def _call(coro):
    """Run a client call, turning data-source failures into messages for the model."""
    try:
        return await coro
    except clients.NotFoundError as exc:
        raise ToolError(f"Not found: {exc}") from exc
    except clients.UpstreamError as exc:
        raise ToolError(str(exc)) from exc


def _validated(fn, value):
    try:
        return fn(value)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def _parse_bcb_date(text: str) -> date:
    return datetime.strptime(text, "%d/%m/%Y").date()


@mcp.tool(annotations=READ_ONLY)
async def get_address_by_cep(cep: str) -> dict[str, Any]:
    """Return the address (street, neighborhood, city, state, coordinates) for a Brazilian CEP.

    Args:
        cep: Postal code with 8 digits, with or without the dash (e.g. "01310-100").
    """
    number = _validated(validation.cep, cep)
    return await _call(clients.brasilapi(f"/cep/v2/{number}"))


@mcp.tool(annotations=READ_ONLY)
async def get_company_by_cnpj(cnpj: str) -> dict[str, Any]:
    """Return public registration data for a Brazilian company: legal name, trade name, status,
    main activity (CNAE), address and opening date, from the Receita Federal registry.

    Args:
        cnpj: Company tax id with 14 digits, punctuation optional (e.g. "33.000.167/0001-01").
    """
    number = _validated(validation.cnpj, cnpj)
    data = await _call(clients.brasilapi(f"/cnpj/v1/{number}"))
    keep = [
        "cnpj", "razao_social", "nome_fantasia", "descricao_situacao_cadastral",
        "data_inicio_atividade", "cnae_fiscal", "cnae_fiscal_descricao", "natureza_juridica",
        "porte", "logradouro", "numero", "bairro", "municipio", "uf", "cep", "capital_social",
    ]
    return {key: data.get(key) for key in keep if key in data}


@mcp.tool(annotations=READ_ONLY)
async def list_national_holidays(year: int) -> dict[str, Any]:
    """List Brazilian national holidays for a year, with date, name and weekday.

    Args:
        year: Year between 1900 and 2199.
    """
    if not 1900 <= year <= 2199:
        raise ToolError("year must be between 1900 and 2199")
    holidays = await _call(clients.brasilapi(f"/feriados/v1/{year}"))
    return {"year": year, "count": len(holidays), "holidays": holidays}


@mcp.tool(annotations=READ_ONLY)
async def get_bank(code: int) -> dict[str, Any]:
    """Return details of a Brazilian bank by its COMPE code (e.g. 260 for Nubank, 1 for Banco do
    Brasil, 341 for Itaú).

    Args:
        code: Bank code.
    """
    return await _call(clients.brasilapi(f"/banks/v1/{code}"))


@mcp.tool(annotations=READ_ONLY)
async def get_ddd(ddd: str) -> dict[str, Any]:
    """Return the state and the cities served by a Brazilian telephone area code (DDD).

    Args:
        ddd: Two-digit area code, e.g. "11" (São Paulo) or "21" (Rio de Janeiro).
    """
    code = _validated(validation.ddd, ddd)
    data = await _call(clients.brasilapi(f"/ddd/v1/{code}"))
    cities = sorted(data.get("cities", []))
    return {"ddd": code, "state": data.get("state"), "city_count": len(cities), "cities": cities}


@mcp.tool(annotations=READ_ONLY)
async def list_municipalities(uf: str) -> dict[str, Any]:
    """List the municipalities of a Brazilian state with their IBGE codes.

    Args:
        uf: Two-letter state code, e.g. "SP", "MG", "RR".
    """
    code = _validated(validation.uf, uf)
    data = await _call(clients.brasilapi(f"/ibge/municipios/v1/{code}"))
    items = sorted(data, key=lambda m: m["nome"])
    return {"uf": code, "count": len(items), "municipalities": items}


@mcp.tool(annotations=READ_ONLY)
async def get_selic_rate(days: int = 1) -> dict[str, Any]:
    """Return the Selic target rate (% per year) set by Copom, as of today, from Banco Central.

    Args:
        days: How many of the most recent daily values to include in `history` (1 to 30).
    """
    days = min(max(days, 1), 30)
    today = _today()
    values = await _call(clients.bcb_series(SELIC_TARGET_SERIES, today - timedelta(days=45), today))
    # the series is published ahead up to the next Copom meeting; never report future dates
    past = [v for v in values if _parse_bcb_date(v["data"]) <= today]
    if not past:
        raise ToolError("Banco Central returned no Selic values up to today")
    history = [
        {"date": _parse_bcb_date(v["data"]).isoformat(), "rate": float(v["valor"])}
        for v in past[-days:]
    ]
    return {"rate_percent_per_year": history[-1]["rate"], "as_of": history[-1]["date"],
            "source": "Banco Central SGS 432", "history": history}


@mcp.tool(annotations=READ_ONLY)
async def get_ipca(months: int = 12) -> dict[str, Any]:
    """Return monthly IPCA inflation (% per month) and the accumulated rate over those months.

    Args:
        months: How many of the most recent months to return (1 to 24).
    """
    months = min(max(months, 1), 24)
    today = _today()
    start = (today.replace(day=1) - timedelta(days=31 * (months + 2))).replace(day=1)
    values = await _call(clients.bcb_series(IPCA_MONTHLY_SERIES, start, today))
    recent = values[-months:]
    if not recent:
        raise ToolError("Banco Central returned no IPCA values for this period")
    monthly = [
        {"month": _parse_bcb_date(v["data"]).strftime("%Y-%m"), "percent": float(v["valor"])}
        for v in recent
    ]
    accumulated = (math.prod(1 + m["percent"] / 100 for m in monthly) - 1) * 100
    return {
        "months": len(monthly),
        "from": monthly[0]["month"],
        "to": monthly[-1]["month"],
        "accumulated_percent": round(accumulated, 2),
        "monthly": monthly,
        "source": "Banco Central SGS 433",
    }


@mcp.tool(annotations=READ_ONLY)
async def get_ptax_rate(day: str | None = None) -> dict[str, Any]:
    """Return the official PTAX USD/BRL buy and sell rates for a day.

    On weekends and holidays there is no PTAX; the most recent previous quote is returned and
    `quote_date` says which day it is from.

    Args:
        day: Date in YYYY-MM-DD format. Defaults to today. Future dates are rejected.
    """
    try:
        target = date.fromisoformat(day) if day else _today()
    except ValueError as exc:
        raise ToolError(f"day must be in YYYY-MM-DD format, got '{day}'") from exc
    if target > _today():
        raise ToolError(f"{target.isoformat()} is in the future; PTAX only exists for past days")

    for back in range(8):
        candidate = target - timedelta(days=back)
        quotes = await _call(clients.bcb_ptax(candidate))
        if quotes:
            last = quotes[-1]
            return {
                "requested_date": target.isoformat(),
                "quote_date": candidate.isoformat(),
                "buy": last["cotacaoCompra"],
                "sell": last["cotacaoVenda"],
                "published_at": last["dataHoraCotacao"],
                "source": "Banco Central PTAX",
            }
    raise ToolError(f"No PTAX quote in the 7 days before {target.isoformat()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Brazil Data MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run()
        return

    import uvicorn

    from brazil_data_mcp.http import create_app

    uvicorn.run(create_app(host=args.host), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
