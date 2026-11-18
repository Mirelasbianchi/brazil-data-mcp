"""Serve the responses recorded from the live APIs on 2026-11-18 (tests/fixtures)."""

import json
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest import mock

import httpx
import respx

from brazil_data_mcp import server

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures"
RECORDED_ON = date(2026, 11, 18)


def _load(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text())


@contextmanager
def recorded_apis():
    api = "https://brasilapi.com.br/api"
    sgs = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados"
    ptax = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"

    def ptax_quote(request):
        # on the morning of 2026-11-18 the day's PTAX was not out yet; the last quote was 11-17
        hit = "11-17-2026" in str(request.url)
        return httpx.Response(200, json=_load("ptax") if hit else {"value": []})

    with respx.mock(assert_all_called=False) as router, \
            mock.patch.object(server, "_today", lambda: RECORDED_ON):
        router.get(f"{api}/cep/v2/01310100").respond(json=_load("cep"))
        router.get(f"{api}/banks/v1/260").respond(json=_load("bank"))
        router.get(f"{api}/feriados/v1/2026").respond(json=_load("holidays"))
        router.get(f"{api}/ddd/v1/11").respond(json=_load("ddd"))
        router.get(f"{api}/ibge/municipios/v1/RR").respond(json=_load("municipios"))
        router.get(sgs.format(432)).respond(json=_load("selic_range"))
        router.get(sgs.format(433)).respond(json=_load("ipca_range"))
        router.get(url__startswith=ptax).mock(side_effect=ptax_quote)
        yield router
