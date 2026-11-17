"""MCP server exposing Brazilian public data as tools."""

import re
from datetime import date

from mcp.server.mcpserver import MCPServer

from brazil_data_mcp import clients

mcp = MCPServer("brazil-data")

SELIC_TARGET_SERIES = 432
IPCA_MONTHLY_SERIES = 433


@mcp.tool()
async def get_address_by_cep(cep: str) -> dict:
    """Return the address (street, neighborhood, city, state) for a Brazilian CEP.

    Args:
        cep: Postal code with 8 digits, with or without the dash (e.g. "01310-100").
    """
    digits = re.sub(r"\D", "", cep)
    if len(digits) != 8:
        raise ValueError("CEP must have exactly 8 digits")
    return await clients.brasilapi(f"/cep/v2/{digits}")


@mcp.tool()
async def list_national_holidays(year: int) -> list:
    """List Brazilian national holidays for a year.

    Args:
        year: Year between 1900 and 2199.
    """
    return await clients.brasilapi(f"/feriados/v1/{year}")


@mcp.tool()
async def get_bank(code: int) -> dict:
    """Return details of a Brazilian bank by its COMPE code (e.g. 260 for Nubank).

    Args:
        code: Bank code.
    """
    return await clients.brasilapi(f"/banks/v1/{code}")


@mcp.tool()
async def get_selic_rate(last: int = 1) -> list:
    """Return the latest Selic target rate values (% per year) from Banco Central.

    Args:
        last: How many of the most recent values to return (1 to 20).
    """
    return await clients.bcb_series(SELIC_TARGET_SERIES, min(max(last, 1), 20))


@mcp.tool()
async def get_ipca(last: int = 12) -> list:
    """Return the latest monthly IPCA inflation values (% per month) from Banco Central.

    Args:
        last: How many months to return (1 to 24).
    """
    return await clients.bcb_series(IPCA_MONTHLY_SERIES, min(max(last, 1), 24))


@mcp.tool()
async def get_ptax_rate(day: str | None = None) -> dict:
    """Return the official PTAX USD/BRL buy and sell rates for a day.

    Args:
        day: Date in YYYY-MM-DD format. Defaults to today. Weekends and holidays have no quote.
    """
    target = date.fromisoformat(day) if day else date.today()
    quotes = await clients.bcb_ptax(target)
    if not quotes:
        return {"date": target.isoformat(), "message": "No PTAX quote for this date"}
    return {"date": target.isoformat(), **quotes[-1]}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
