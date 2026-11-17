import httpx
import pytest
import respx

from brazil_data_mcp import server


@respx.mock
async def test_get_address_by_cep_strips_dash():
    route = respx.get("https://brasilapi.com.br/api/cep/v2/01310100").mock(
        return_value=httpx.Response(200, json={"cep": "01310100", "city": "São Paulo"})
    )
    result = await server.get_address_by_cep("01310-100")
    assert route.called
    assert result["city"] == "São Paulo"


async def test_get_address_by_cep_rejects_invalid():
    with pytest.raises(ValueError):
        await server.get_address_by_cep("123")


@respx.mock
async def test_get_selic_rate_clamps_last():
    route = respx.get(
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/20"
    ).mock(return_value=httpx.Response(200, json=[{"data": "01/01/2026", "valor": "15.00"}]))
    result = await server.get_selic_rate(last=100)
    assert route.called
    assert result[0]["valor"] == "15.00"
