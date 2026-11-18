"""Chart monthly IPCA through the MCP tool, as an agent would get it.

    uv run --group demo python examples/plot_ipca.py docs/assets/ipca.svg [--replay]
"""

import argparse
import asyncio
from contextlib import ExitStack

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mcp import Client

from brazil_data_mcp.server import mcp

UP, DOWN, INK, MUTED, GRID, SURFACE = "#2a78d6", "#eb6834", "#14213d", "#566070", "#e2e6e3", "#fcfcfb"
MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


async def fetch(months: int) -> dict:
    async with Client(mcp) as client:
        result = await client.call_tool("get_ipca", {"months": months})
        return result.structured_content


def plot(data: dict, out: str) -> None:
    labels = [f"{MONTHS_PT[int(m['month'][5:]) - 1]}/{m['month'][2:4]}" for m in data["monthly"]]
    values = [m["percent"] for m in data["monthly"]]
    fig, ax = plt.subplots(figsize=(8, 3.8), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    bars = ax.bar(labels, values, color=[UP if v >= 0 else DOWN for v in values], width=0.62)
    for bar, value in zip(bars, values, strict=True):
        y = value + (0.03 if value >= 0 else -0.03)
        ax.text(bar.get_x() + bar.get_width() / 2, y, f"{value:.2f}".replace(".", ","),
                ha="center", va="bottom" if value >= 0 else "top", fontsize=8.5, color=INK)
    ax.axhline(0, color=MUTED, linewidth=1)
    ax.set_ylim(min(values) - 0.2, max(values) + 0.2)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.1f}%".replace(".", ","))
    ax.grid(axis="y", color=GRID)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=MUTED, length=0, labelsize=9)
    total = f"{data['accumulated_percent']:.2f}".replace(".", ",")
    fig.suptitle(f"IPCA: {total}% acumulado em 12 meses", x=0.04, ha="left",
                 color=INK, fontsize=13, fontweight="bold")
    ax.set_title("Inflação mensal, % (Banco Central, série SGS 433, via get_ipca)", loc="left",
                 color=MUTED, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    with ExitStack() as stack:
        if args.replay:
            from replay import recorded_apis

            stack.enter_context(recorded_apis())
        data = asyncio.run(fetch(12))
    plot(data, args.out)


if __name__ == "__main__":
    main()
