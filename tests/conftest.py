import json
from datetime import date
from pathlib import Path

import pytest

from brazil_data_mcp import clients, server

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text())


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    """Fresh caches, no retry sleeps and a fixed 'today' matching the recorded fixtures."""
    for fn in (clients.brasilapi, clients.bcb_series, clients.bcb_ptax):
        fn.cache_clear()
    monkeypatch.setattr(clients, "BACKOFF_S", 0)
    monkeypatch.setattr(server, "_today", lambda: date(2026, 11, 18))
