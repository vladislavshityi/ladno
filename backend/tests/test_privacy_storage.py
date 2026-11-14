import httpx
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Account, make_png


async def test_personal_data_is_encrypted_in_db(
    client: httpx.AsyncClient, session: AsyncSession, anna: Account
):
    profile = {"full_name": "Иванов Иван", "phone": "+79140000000", "apartment": "12"}
    await client.put("/users/me/profile", json=profile, headers=anna.headers)

    raw = (await session.execute(text("SELECT full_name, phone, apartment FROM users"))).one()
    assert all(value and value not in profile.values() for value in raw)
    me = (await client.get("/users/me", headers=anna.headers)).json()
    assert me["full_name"] == "Иванов Иван" and me["phone"] == "+7 914 000-00-00"


async def test_uploaded_photo_loses_exif(client: httpx.AsyncClient, anna: Account, tmp_path):
    exif = Image.Exif()
    exif[0x0110] = "Secret Phone Model"
    photo = make_png(exif=exif.tobytes())
    up = await client.post(
        "/photos", files={"file": ("a.png", photo, "image/png")}, headers=anna.headers
    )
    stored = (await client.get(up.json()["url"].removeprefix("/api"), headers=anna.headers)).content
    assert b"Secret Phone Model" in photo and b"Secret Phone Model" not in stored


async def test_broken_image_is_rejected(client: httpx.AsyncClient, anna: Account):
    fake = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    up = await client.post(
        "/photos", files={"file": ("a.png", fake, "image/png")}, headers=anna.headers
    )
    assert up.status_code == 415
