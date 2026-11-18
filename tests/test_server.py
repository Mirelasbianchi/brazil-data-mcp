import httpx
import pytest
import respx
from conftest import fixture
from mcp.server.mcpserver.exceptions import ToolError

from brazil_data_mcp import server

BRASILAPI = "https://brasilapi.com.br/api"
SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados"
PTAX = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarDia(dataCotacao=@dataCotacao)"


@respx.mock
async def test_get_address_by_cep_strips_dash():
    route = respx.get(f"{BRASILAPI}/cep/v2/01310100").mock(
        return_value=httpx.Response(200, json=fixture("cep"))
    )
    result = await server.get_address_by_cep("01310-100")
    assert route.called
    assert result["street"] == "Avenida Paulista"


async def test_get_address_by_cep_rejects_invalid():
    with pytest.raises(ToolError, match="8 digits"):
        await server.get_address_by_cep("123")


@respx.mock
async def test_unknown_cep_is_a_clear_error():
    respx.get(f"{BRASILAPI}/cep/v2/99999999").mock(return_value=httpx.Response(404))
    with pytest.raises(ToolError, match="Not found"):
        await server.get_address_by_cep("99999-999")


@respx.mock
async def test_selic_ignores_values_dated_after_today():
    values = fixture("selic_range") + [{"data": "05/12/2026", "valor": "99.00"}]
    respx.get(SGS.format(432)).mock(return_value=httpx.Response(200, json=values))
    result = await server.get_selic_rate(days=3)
    assert result["rate_percent_per_year"] == 13.75
    assert result["as_of"] == "2026-11-18"
    assert len(result["history"]) == 3


@respx.mock
async def test_ipca_accumulates_monthly_values():
    respx.get(SGS.format(433)).mock(return_value=httpx.Response(200, json=fixture("ipca_range")))
    result = await server.get_ipca(months=12)
    assert (result["from"], result["to"]) == ("2025-11", "2026-10")
    # product of (1 + m/100) over Nov/2025..Oct/2026, recorded on 2026-11-18
    assert result["accumulated_percent"] == 4.63


@respx.mock
async def test_ptax_falls_back_to_previous_business_day():
    def quote(request):
        if "11-17-2026" in str(request.url):
            return httpx.Response(200, json=fixture("ptax"))
        return httpx.Response(200, json={"value": []})

    respx.get(url__startswith=PTAX).mock(side_effect=quote)
    result = await server.get_ptax_rate("2026-11-18")
    assert result["quote_date"] == "2026-11-17"
    assert result["sell"] == 5.7851


async def test_ptax_rejects_future_dates():
    with pytest.raises(ToolError, match="future"):
        await server.get_ptax_rate("2030-01-01")


@respx.mock
async def test_ddd_and_municipalities():
    respx.get(f"{BRASILAPI}/ddd/v1/11").mock(return_value=httpx.Response(200, json=fixture("ddd")))
    respx.get(f"{BRASILAPI}/ibge/municipios/v1/RR").mock(
        return_value=httpx.Response(200, json=fixture("municipios"))
    )
    ddd = await server.get_ddd("11")
    assert ddd["state"] == "SP" and "SÃO PAULO" in ddd["cities"]
    towns = await server.list_municipalities("rr")
    assert towns["count"] == 15 and towns["municipalities"][0]["nome"] == "ALTO ALEGRE"


async def test_cnpj_check_digits_are_validated_locally():
    with pytest.raises(ToolError, match="check digits"):
        await server.get_company_by_cnpj("33.000.167/0001-00")


@respx.mock
async def test_retries_transient_errors_then_succeeds():
    route = respx.get(f"{BRASILAPI}/banks/v1/260").mock(
        side_effect=[httpx.Response(429), httpx.Response(503),
                     httpx.Response(200, json=fixture("bank"))]
    )
    result = await server.get_bank(260)
    assert route.call_count == 3
    assert result["name"] == "NU PAGAMENTOS - IP"


@respx.mock
async def test_gives_up_with_a_readable_message():
    respx.get(f"{BRASILAPI}/feriados/v1/2026").mock(return_value=httpx.Response(502))
    with pytest.raises(ToolError, match="unavailable right now"):
        await server.list_national_holidays(2026)


@respx.mock
async def test_responses_are_cached():
    route = respx.get(f"{BRASILAPI}/feriados/v1/2026").mock(
        return_value=httpx.Response(200, json=fixture("holidays"))
    )
    await server.list_national_holidays(2026)
    await server.list_national_holidays(2026)
    assert route.call_count == 1
