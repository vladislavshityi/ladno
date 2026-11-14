import httpx
import pytest
from pydantic import TypeAdapter, ValidationError

from app.core import fields
from tests.conftest import Account


def check(type_, value):
    return TypeAdapter(type_).validate_python(value)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("иванов иван", "Иванов Иван"),
        ("  ИВАНОВ   иван  петрович ", "Иванов Иван Петрович"),
        ("анна-мария о'коннор", "Анна-Мария О'Коннор"),
        ("Smith John", "Smith John"),
        ("Иванов И. И.", "Иванов И. И."),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_full_name_is_normalized(raw, expected):
    assert check(fields.FullName, raw) == expected


@pytest.mark.parametrize(
    "raw", ["Иванов", "а б в г", "Иванов 2", "Иван@ов Иван", "Иванов\nИван", "Иванов " + "и" * 100]
)
def test_full_name_is_rejected(raw):
    with pytest.raises(ValidationError):
        check(fields.FullName, raw)


@pytest.mark.parametrize(
    "raw",
    [
        "+7 900 123-45-67",
        "89001234567",
        "8 (900) 123-45-67",
        "+7(900)1234567",
        "9001234567",
        "7 900 123 45 67",
    ],
)
def test_phone_is_normalized(raw):
    assert check(fields.Phone, raw) == "+7 900 123-45-67"


@pytest.mark.parametrize(
    "raw",
    ["12345", "+1 900 123-45-67", "890012345", "+7 000 123-45-67", "89001234567x", "7+9001234567"],
)
def test_phone_is_rejected(raw):
    with pytest.raises(ValidationError, match="Введите номер в формате"):
        check(fields.Phone, raw)


def test_phone_blank_is_none():
    assert check(fields.Phone, "  ") is None


def test_email():
    assert check(fields.Email, " Anna@Example.RU ") == "anna@example.ru"
    assert check(fields.Email, "") is None
    for bad in ["anna", "anna@", "@example.ru", "anna@example", "a b@example.ru", "a@b@example.ru"]:
        with pytest.raises(ValidationError):
            check(fields.Email, bad)


def test_apartment_and_entrance():
    assert [check(fields.Apartment, v) for v in ("12", "12А", " 12/1 ", "1234а")] == [
        "12", "12а", "12/1", "1234а",
    ]  # fmt: skip
    for bad in ["", "а", "12ab", "1234567", "12-1", "кв 12"]:
        if bad:
            with pytest.raises(ValidationError):
                check(fields.Apartment, bad)
    assert check(fields.Entrance, "03") == "3" and check(fields.Entrance, "99") == "99"
    for bad in ["0", "100", "а", "-1"]:
        with pytest.raises(ValidationError):
            check(fields.Entrance, bad)


def test_text_trims_and_rejects_control_chars():
    place = fields.Place
    assert check(place, "  у лифта ") == "у лифта" and check(place, " ") is None
    with pytest.raises(ValidationError):
        check(place, "у\x00лифта")
    with pytest.raises(ValidationError):
        check(place, "у\nлифта")
    with pytest.raises(ValidationError):
        check(place, "я" * 301)


def test_description_bounds():
    assert (
        check(fields.Description, "  не горит свет \n в подъезде ") == "не горит свет \n в подъезде"
    )
    assert check(fields.Description, "  ") == ""
    for bad in ["свет", "я" * 1001, "не горит\x07 свет"]:
        with pytest.raises(ValidationError):
            check(fields.Description, bad)


def test_amounts():
    assert str(check(fields.MoneyAmount, "1234.50")) == "1234.50"
    assert check(fields.MoneyAmount, None) is None
    for bad in ["-0.01", "1000000.01", "1.234", "nan", "inf", "abc"]:
        with pytest.raises(ValidationError):
            check(fields.MoneyAmount, bad)
    assert check(fields.SignedMoney, "-150.00") and check(fields.TariffAmount, "53.4360")
    with pytest.raises(ValidationError):
        check(fields.SignedMoney, "-1000000.01")
    with pytest.raises(ValidationError):
        check(fields.VolumeAmount, "100000.5")
    with pytest.raises(ValidationError):
        check(fields.AreaAmount, "0.5")
    with pytest.raises(ValidationError):
        check(fields.AreaAmount, "1000.01")


def test_period_range():
    assert check(fields.Period, "2020-01") == "2020-01"
    for bad in ["2019-12", "2099-01", "2026-13", "2026-1", "ноябрь"]:
        with pytest.raises(ValidationError):
            check(fields.Period, bad)


async def test_profile_normalizes_and_returns_field_errors(
    client: httpx.AsyncClient, anna: Account
):
    ok = await client.put(
        "/users/me/profile",
        json={"full_name": "иванов иван", "phone": "89001234567", "email": "A@B.RU",
              "apartment": "12А", "entrance": "2"},
        headers=anna.headers,
    )  # fmt: skip
    body = ok.json()
    assert ok.status_code == 200, body
    assert body["full_name"] == "Иванов Иван" and body["phone"] == "+7 900 123-45-67"
    assert body["email"] == "a@b.ru" and body["apartment"] == "12а"

    bad = await client.put(
        "/users/me/profile",
        json={"full_name": "Иванов", "phone": "123", "entrance": "100"},
        headers=anna.headers,
    )
    error = bad.json()
    assert bad.status_code == 422 and error["code"] == "validation_error"
    assert error["fields"]["phone"] == "Введите номер в формате +7 900 123-45-67"
    assert set(error["fields"]) == {"full_name", "phone", "entrance"}
    assert "Телефон: Введите номер в формате" in error["detail"] and "ФИО:" in error["detail"]


async def test_other_errors_have_empty_fields(client: httpx.AsyncClient):
    response = await client.get("/houses/999999")
    assert response.status_code == 404 and response.json()["fields"] == {}


async def test_issue_and_receipt_inputs_are_validated(client: httpx.AsyncClient, anna: Account):
    short = await client.post(
        "/issues", json={"category": "graffiti", "description": "свет"}, headers=anna.headers
    )
    assert short.status_code == 422 and "description" in short.json()["fields"]
    ref = await client.post("/issues", json={"category": "graffiti"}, headers=anna.headers)
    bad_ref = await client.patch(
        f"/issues/{ref.json()['id']}", json={"external_ref": "a\x00b"}, headers=anna.headers
    )
    assert bad_ref.status_code == 422 and "external_ref" in bad_ref.json()["fields"]

    line = {"service_name": "Вода", "accrued": "10.005"}
    manual = await client.post(
        "/receipts/manual",
        json={"period": "2019-01", "lines": [line], "residents": 31, "area_m2": "0"},
        headers=anna.headers,
    )
    fields_ = manual.json()["fields"]
    assert manual.status_code == 422
    assert {"period", "residents", "area_m2", "lines.0.accrued"} <= set(fields_)

    long_chat = await client.post(
        "/assistant/chat",
        json={"messages": [{"role": "user", "content": "я" * 4001}]},
        headers=anna.headers,
    )
    assert long_chat.status_code == 422
