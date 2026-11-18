import pytest

from brazil_data_mcp import validation


def test_valid_cnpj_with_punctuation():
    assert validation.cnpj("33.000.167/0001-01") == "33000167000101"


@pytest.mark.parametrize("value", ["11111111111111", "123", "33000167000102"])
def test_invalid_cnpj(value):
    with pytest.raises(ValueError):
        validation.cnpj(value)


def test_uf_and_ddd():
    assert validation.uf(" sp ") == "SP"
    assert validation.ddd(21) == "21"
    with pytest.raises(ValueError):
        validation.uf("XX")
    with pytest.raises(ValueError):
        validation.ddd("01")
