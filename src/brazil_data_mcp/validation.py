"""Input validation for Brazilian identifiers, done locally before any network call."""

import re

UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
    "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}


def digits(value: str | int) -> str:
    return re.sub(r"\D", "", str(value))


def cep(value: str) -> str:
    number = digits(value)
    if len(number) != 8:
        raise ValueError(f"CEP must have 8 digits, got {len(number)} ('{value}')")
    return number


def cnpj(value: str) -> str:
    """Return the 14 digits of a CNPJ after checking both verification digits."""
    number = digits(value)
    if len(number) != 14 or number == number[0] * 14:
        raise ValueError(f"'{value}' is not a valid CNPJ: it must have 14 digits")

    def check_digit(base: str) -> str:
        weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(base):]
        remainder = sum(int(d) * w for d, w in zip(base, weights, strict=True)) % 11
        return "0" if remainder < 2 else str(11 - remainder)

    first = check_digit(number[:12])
    second = check_digit(number[:12] + first)
    if number[12:] != first + second:
        raise ValueError(f"'{value}' is not a valid CNPJ: the check digits do not match")
    return number


def uf(value: str) -> str:
    code = value.strip().upper()
    if code not in UFS:
        raise ValueError(f"'{value}' is not a Brazilian state code (e.g. SP, RJ, MG)")
    return code


def ddd(value: str | int) -> str:
    code = digits(value)
    if len(code) != 2 or code[0] == "0":
        raise ValueError(f"'{value}' is not a DDD area code (two digits, e.g. 11 or 21)")
    return code
