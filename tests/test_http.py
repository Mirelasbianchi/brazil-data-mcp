from starlette.testclient import TestClient

from brazil_data_mcp.http import create_app


def test_health_and_tools_list_over_http():
    # deployed behind a load balancer: requests arrive with the public hostname
    with TestClient(create_app(host="0.0.0.0"), base_url="https://mcp.example.com") as client:
        assert client.get("/health").json()["status"] == "ok"
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"accept": "application/json, text/event-stream",
                     "mcp-protocol-version": "2025-06-18"},
        )
        assert response.status_code == 200
        names = {tool["name"] for tool in response.json()["result"]["tools"]}
        assert {"get_selic_rate", "get_company_by_cnpj"} <= names
