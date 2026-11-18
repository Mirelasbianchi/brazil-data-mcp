"""Walk through the tools the way an agent would, and print what comes back.

    uv run --group demo python examples/demo.py                    # live APIs, in-process server
    uv run --group demo python examples/demo.py --url http://localhost:8000/mcp   # remote server
    uv run --group demo python examples/demo.py --replay           # recorded responses, offline

--replay serves the responses recorded from the live APIs on 2026-11-18
(tests/fixtures) and pins "today" to that date, so the output is reproducible.
"""

import argparse
import asyncio
import json
import logging
from contextlib import ExitStack

from mcp import Client
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.terminal_theme import MONOKAI

console = Console(width=104, record=True)

STEPS = [
    ("Qual é o endereço do CEP 01310-100?", "get_address_by_cep", {"cep": "01310-100"}),
    ("Quanto está a Selic hoje?", "get_selic_rate", {"days": 1}),
    ("Qual foi a inflação (IPCA) nos últimos 12 meses?", "get_ipca", {"months": 12}),
    ("Quanto o dólar PTAX fechou hoje?", "get_ptax_rate", {"day": "2026-11-18"}),
    ("Quais são os próximos feriados nacionais?", "list_national_holidays", {"year": 2026}),
    ("De que banco é o código 260?", "get_bank", {"code": 260}),
    ("Pode consultar o CNPJ 33.000.167/0001-00?", "get_company_by_cnpj",
     {"cnpj": "33.000.167/0001-00"}),
]


def summarize(name: str, data) -> str:
    if name == "get_address_by_cep":
        return f"{data['street']}, {data['neighborhood']}, {data['city']}-{data['state']}"
    if name == "get_selic_rate":
        return f"Selic {data['rate_percent_per_year']}% a.a. (as of {data['as_of']})"
    if name == "get_ipca":
        return (f"IPCA {data['from']}..{data['to']}: {data['accumulated_percent']}% accumulated, "
                f"last month {data['monthly'][-1]['percent']}%")
    if name == "get_ptax_rate":
        return (f"USD/BRL buy {data['buy']} / sell {data['sell']} "
                f"(quote from {data['quote_date']}, requested {data['requested_date']})")
    if name == "list_national_holidays":
        upcoming = [h for h in data["holidays"] if h["date"] >= "2026-11-18"]
        return "; ".join(f"{h['date']} {h['name']} ({h['weekday']})" for h in upcoming)
    if name == "get_bank":
        return f"{data['code']}: {data['fullName']}"
    return json.dumps(data, ensure_ascii=False)[:200]


async def run(target) -> None:
    async with Client(target) as client:
        tools = (await client.list_tools()).tools
        table = Table(title=f"{len(tools)} tools", title_justify="left", box=None, pad_edge=False)
        table.add_column("tool", style="bold cyan")
        table.add_column("description")
        for tool in tools:
            summary = " ".join((tool.description or "").split("\n\n")[0].split())
            table.add_row(tool.name, summary)
        console.print(table)
        console.print()
        for question, name, args in STEPS:
            console.print(f"[bold]> {question}[/bold]")
            call = json.dumps(args, ensure_ascii=False).replace("[", r"\[")
            console.print(f"  [dim]tool call[/dim] [cyan]{name}[/cyan]({call})")
            result = await client.call_tool(name, args)
            text = result.content[0].text if result.content else ""
            if result.is_error:
                console.print(Panel(text, border_style="red", title="tool error", title_align="left"))
            else:
                data = result.structured_content or json.loads(text)
                console.print(Panel(summarize(name, data), border_style="green"))
            console.print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Streamable HTTP endpoint of a running server")
    parser.add_argument("--replay", action="store_true", help="use recorded responses")
    parser.add_argument("--html", help="also save the transcript as HTML")
    args = parser.parse_args()
    for noisy in ("httpx", "mcp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    from brazil_data_mcp.server import mcp

    with ExitStack() as stack:
        if args.replay:
            from replay import recorded_apis

            stack.enter_context(recorded_apis())
        asyncio.run(run(args.url or mcp))
    if args.html:
        console.save_html(args.html, inline_styles=True, theme=MONOKAI)


if __name__ == "__main__":
    main()
