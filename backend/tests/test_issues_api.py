import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from tests.conftest import PNG, Account, FakeLLM
from tests.test_rules import uk_rules_with_ladder

BODY = {"patch": {"json": {"external_ref": "x"}}}
DARK = {"category": "stairwell_lighting", "answers": {"scope": "floor", "duration": "week_plus"}}


async def create(client: httpx.AsyncClient, who: Account, **payload) -> dict:
    response = await client.post("/issues", json={**DARK, **payload}, headers=who.headers)
    assert response.status_code == 201, response.text
    return response.json()


async def submit(client: httpx.AsyncClient, who: Account, issue_id: str, **extra) -> dict:
    response = await client.patch(
        f"/issues/{issue_id}", json={"status": "submitted", **extra}, headers=who.headers
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_categories_and_questions(client: httpx.AsyncClient):
    categories = (await client.get("/categories")).json()
    assert len(categories) == 12 and {"id", "title", "icon", "pos_hint"} == set(categories[0])
    questions = (await client.get("/categories/stairwell_lighting/questions")).json()
    assert [q["id"] for q in questions] == ["duration", "scope"]
    assert (await client.get("/categories/nope/questions")).status_code == 404


async def test_route_uses_profile_company(client: httpx.AsyncClient, anna: Account):
    hit = (await client.get("/addresses/search", params={"q": "Кутузова 5а"})).json()[0]
    await client.put("/users/me/profile", json={"house_id": hit["house_id"]}, headers=anna.headers)
    route = (await client.post("/issues/route", json=DARK, headers=anna.headers)).json()
    uk = (await client.get("/users/me", headers=anna.headers)).json()["management_company"]
    assert route["addressee"]["name"] == uk["name"]
    assert route["addressee"]["channels"][-1]["type"] == "pos"
    assert route["response_deadline"] == {
        "days": 10, "type": "working", "source": "ПП РФ № 354", "verified": False
    }  # fmt: skip
    assert [s["key"] for s in route["escalation"]] == ["housing_inspection", "prosecutor"]


async def test_route_without_company_and_already_contacted(
    client: httpx.AsyncClient, anna: Account
):
    route = (await client.post("/issues/route", json=DARK, headers=anna.headers)).json()
    assert "укажите её в профиле" in route["addressee"]["name"]
    shifted = {**DARK, "already_contacted_uk": True}
    route = (await client.post("/issues/route", json=shifted, headers=anna.headers)).json()
    assert route["addressee"]["key"] == "housing_inspection"
    unknown = await client.post("/issues/route", json={"category": "zzz"}, headers=anna.headers)
    assert unknown.status_code == 404


async def test_dark_entrance_scenario_to_submission(client: httpx.AsyncClient, anna: Account):
    hit = (await client.get("/addresses/search", params={"q": "Кутузова 5а"})).json()[0]
    issue = await create(client, anna, house_id=hit["house_id"], location_details="подъезд 2")
    assert issue["status"] == "draft" and issue["address"] == hit["address"]
    assert issue["category_title"] == "Не работает освещение в подъезде"
    draft = issue["draft"]
    assert "[укажите ФИО]" in draft["full"] and "подъезд 2" in draft["full"]
    assert "[укажите" not in draft["pos_short"] and len(draft["pos_short"]) <= 1000
    assert issue["deadline_at"] is None

    sub = (await client.get(f"/issues/{issue['id']}/submission", headers=anna.headers)).json()
    assert sub["channel"] == "pos_link" and sub["text"] == draft["pos_short"]
    assert sub["category_hint"] == "ЖКХ → Содержание общего имущества"
    assert sub["steps"][0].startswith("Войдите") and sub["char_limit"] == 1000
    assert sub["alternatives"][0]["channel"] == "gis_zhkh_link"

    sent_at = datetime.now(UTC)
    done = await submit(client, anna, issue["id"], submitted_at=sent_at.isoformat())
    assert done["status"] == "submitted" and done["is_overdue"] is False
    deadline = datetime.fromisoformat(done["deadline_at"])
    assert timedelta(days=10) <= deadline - sent_at <= timedelta(days=14)


async def test_overdue_flag(client: httpx.AsyncClient, anna: Account):
    issue = await create(client, anna)
    long_ago = (datetime.now(UTC) - timedelta(days=60)).isoformat()
    done = await submit(client, anna, issue["id"], submitted_at=long_ago)
    assert done["is_overdue"] is True


async def test_patch_draft_and_external_ref(client: httpx.AsyncClient, anna: Account):
    issue = await create(client, anna)
    patch = {"draft": {"full": "Мой текст", "pos_short": "Коротко"}, "external_ref": "ПОС-1"}
    body = (await client.patch(f"/issues/{issue['id']}", json=patch, headers=anna.headers)).json()
    assert body["draft"] == {"full": "Мой текст", "pos_short": "Коротко"}
    assert body["external_ref"] == "ПОС-1" and body["status"] == "draft"


async def test_list_and_get_own_issues_only(
    client: httpx.AsyncClient, anna: Account, boris: Account
):
    mine = await create(client, anna)
    assert [i["id"] for i in (await client.get("/issues", headers=anna.headers)).json()] == [
        mine["id"]
    ]
    assert (await client.get("/issues", headers=boris.headers)).json() == []
    for method, url in [("get", f"/issues/{mine['id']}"), ("patch", f"/issues/{mine['id']}"),
                        ("get", f"/issues/{mine['id']}/submission"),
                        ("post", f"/issues/{mine['id']}/escalate")]:  # fmt: skip
        response = await getattr(client, method)(url, headers=boris.headers, **BODY.get(method, {}))
        assert response.status_code == 404, url


async def test_escalation_ladder(client: httpx.AsyncClient, anna: Account):
    first = await create(client, anna)
    await submit(client, anna, first["id"], external_ref="1234")
    second = (await client.post(f"/issues/{first['id']}/escalate", headers=anna.headers)).json()
    assert second["route"]["addressee"]["name"].startswith("Государственная жилищная инспекция")
    assert second["parent_issue_id"] == first["id"] and second["escalation_level"] == 1
    assert "Ранее я обращался" in second["draft"]["full"] and "1234" in second["draft"]["full"]
    third = (await client.post(f"/issues/{second['id']}/escalate", headers=anna.headers)).json()
    assert third["route"]["addressee"]["key"] == "prosecutor" and third["route"]["escalation"] == []
    last = await client.post(f"/issues/{third['id']}/escalate", headers=anna.headers)
    assert last.status_code == 409 and last.json()["code"] == "no_escalation_left"


async def test_photos_upload_owner_only_and_attach(
    client: httpx.AsyncClient, anna: Account, boris: Account
):
    up = await client.post(
        "/photos", files={"file": ("a.png", PNG, "image/png")}, headers=anna.headers
    )
    photo = up.json()
    assert up.status_code == 201 and photo["url"] == f"/api/photos/{photo['id']}"
    own = await client.get(f"/photos/{photo['id']}", headers=anna.headers)
    assert own.status_code == 200 and own.headers["content-type"] == "image/png"
    assert (await client.get(f"/photos/{photo['id']}", headers=boris.headers)).status_code == 404
    stolen = await client.post(
        "/issues", json={**DARK, "photo_ids": [photo["id"]]}, headers=boris.headers
    )
    assert stolen.status_code == 404
    issue = await create(client, anna, photo_ids=[photo["id"]])
    assert issue["photos"] == [photo] and "фотографии, 1 шт." in issue["draft"]["full"]


async def test_photo_validation(client: httpx.AsyncClient, anna: Account):
    html = await client.post(
        "/photos", files={"file": ("a.png", b"<html>", "image/png")}, headers=anna.headers
    )
    assert html.status_code == 415 and html.json()["code"] == "unsupported_file"
    big = PNG + b"\x00" * (5 * 1024 * 1024)
    response = await client.post(
        "/photos", files={"file": ("a.png", big, "image/png")}, headers=anna.headers
    )
    assert response.status_code == 413


async def test_classify_without_llm_needs_manual_choice(client: httpx.AsyncClient, anna: Account):
    body = (
        await client.post(
            "/issues/classify", json={"text": "в подъезде не горит свет"}, headers=anna.headers
        )
    ).json()
    assert body["needs_manual_choice"] is True and body["category"] is None


async def test_classify_requires_text_or_photo(client: httpx.AsyncClient, anna: Account):
    response = await client.post("/issues/classify", json={"text": " "}, headers=anna.headers)
    assert response.status_code == 422


async def test_classify_with_llm_text_and_photo(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    photo = (
        await client.post(
            "/photos", files={"file": ("a.png", PNG, "image/png")}, headers=anna.headers
        )
    ).json()
    llm.replies = [
        '```json\n{"category": "stairwell_lighting", "confidence": 0.93, "summary": "Темно"}\n```'
    ]
    body = (
        await client.post(
            "/issues/classify",
            json={"text": "не горит свет", "photo_ids": [photo["id"]]},
            headers=anna.headers,
        )
    ).json()
    assert body["category"] == "stairwell_lighting" and body["confidence"] == 0.93
    user_message = llm.calls[0][1]["content"]
    assert [p["type"] for p in user_message] == ["text", "image_url"]
    assert user_message[1]["image_url"]["url"].startswith("data:image/png;base64,")


async def test_classify_distrusts_unknown_category_and_low_confidence(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    for reply in ('{"category": "made_up", "confidence": 0.99}',
                  '{"category": "pothole", "confidence": 0.2, "clarification": "Где яма?"}',
                  "not json at all"):  # fmt: skip
        llm.replies = [reply]
        body = (
            await client.post("/issues/classify", json={"text": "плохо"}, headers=anna.headers)
        ).json()
        assert body["needs_manual_choice"] is True and body["category"] is None
    assert body["clarification"] is None
    llm.replies = ['{"category": null, "confidence": 0.1, "clarification": "Где именно яма?"}']
    body = (
        await client.post("/issues/classify", json={"text": "плохо"}, headers=anna.headers)
    ).json()
    assert body["clarification"] == "Где именно яма?"


async def test_classify_emergency_comes_from_code_with_directory_phones(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ['{"category": "utility_outage", "confidence": 0.9, "is_emergency": false}']
    body = (
        await client.post(
            "/issues/classify", json={"text": "пахнет газом в подъезде"}, headers=anna.headers
        )
    ).json()
    assert body["is_emergency"] is True and body["emergency"]["reason"] == "Возможная утечка газа"
    assert {c["value"] for c in body["emergency"]["contacts"]} >= {"104", "112"}


async def test_summary_uses_llm_only_if_numbers_are_supported(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ["Свет в подъезде не горит больше недели."]
    good = await create(client, anna)
    assert good["draft"]["full"].count("Свет в подъезде не горит больше недели.") == 1
    llm.replies = ["С 28.10.2026 в подъезде темно."]
    bad = await create(client, anna)
    assert "28.10" not in bad["draft"]["full"] and "Обращение касается" in bad["draft"]["full"]
    sent = json.dumps(llm.calls[0], ensure_ascii=False)
    assert "location_details" not in sent


async def test_llm_failure_falls_back_to_template(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    from app.core.errors import ServiceUnavailable

    llm.error = ServiceUnavailable("нет")
    issue = await create(client, anna)
    assert "Обращение касается проблемы" in issue["draft"]["full"]


async def test_create_validates_category_and_photos(client: httpx.AsyncClient, anna: Account):
    unknown = await client.post("/issues", json={"category": "zzz"}, headers=anna.headers)
    assert unknown.status_code == 404
    bad = await client.post(
        "/issues", json={**DARK, "photo_ids": ["not-uuid"]}, headers=anna.headers
    )
    assert bad.status_code == 422 and bad.json()["code"] == "validation_error"


@pytest.mark.parametrize(("category", "answers", "rule"), uk_rules_with_ladder())
async def test_route_after_uk_names_next_step_in_explanation(
    client: httpx.AsyncClient, anna: Account, category: str, answers: dict, rule: dict
):
    body = {"category": category, "answers": answers, "already_contacted_uk": True}
    route = (await client.post("/issues/route", json=body, headers=anna.headers)).json()
    assert route["addressee"]["key"] == rule["escalation"][0]
    assert route["explanation"].startswith("Вы уже обращались в УК без результата")
    assert route["addressee"]["name"] in route["explanation"]
    assert "обязанность УК" not in route["explanation"] and route["fix_deadline"] is None


async def test_summary_must_not_address_uk_when_addressee_is_inspection(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ["Обращаюсь в управляющую компанию: в подъезде не горит свет."]
    issue = await create(client, anna, already_contacted_uk=True)
    assert issue["route"]["addressee"]["key"] == "housing_inspection"
    assert "управляющую компанию" not in issue["draft"]["full"]
    assert "Обращение касается" in issue["draft"]["full"]
    prompt = json.dumps(llm.calls[0], ensure_ascii=False)
    assert "Государственная жилищная инспекция" in prompt
    llm.replies = ["В подъезде не горит свет уже больше недели."]
    fine = await create(client, anna, already_contacted_uk=True)
    assert "больше недели" in fine["draft"]["full"]


async def test_summary_for_uk_may_mention_uk(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ["Прошу управляющую компанию заменить лампы, обращаюсь в управляющую компанию."]
    issue = await create(client, anna)
    assert "заменить лампы" in issue["draft"]["full"]


async def test_escalation_replaces_summary_that_names_uk(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ["Обращаюсь в управляющую компанию: свет не горит."]
    first = await create(client, anna)
    assert "Обращаюсь в управляющую компанию" in first["draft"]["full"]
    second = (await client.post(f"/issues/{first['id']}/escalate", headers=anna.headers)).json()
    assert "управляющую компанию" not in second["draft"]["full"].split("Суть проблемы:")[1]


async def test_route_by_house_id_uses_that_house_company(client: httpx.AsyncClient, anna: Account):
    hit = (await client.get("/addresses/search", params={"q": "Кутузова 5а"})).json()[0]
    house = await client.get(f"/houses/{hit['house_id']}", headers=anna.headers)
    company = house.json()["management_company"]["name"]
    route = (
        await client.post(
            "/issues/route", json={**DARK, "house_id": hit["house_id"]}, headers=anna.headers
        )
    ).json()
    assert route["addressee"]["name"] == company
    profile_only = (await client.post("/issues/route", json=DARK, headers=anna.headers)).json()
    assert "укажите её в профиле" in profile_only["addressee"]["name"]


async def test_missing_applicant_fields_and_refresh_letter(
    client: httpx.AsyncClient, anna: Account
):
    issue = await create(client, anna)
    assert issue["missing_applicant_fields"] == ["full_name", "apartment", "phone"]
    assert (
        "От: [укажите ФИО], кв. [укажите номер], тел. [укажите телефон]" in issue["draft"]["full"]
    )
    edited = issue["draft"]["full"].replace("Прошу устранить", "Очень прошу устранить")
    patch = {"draft": {"full": edited, "pos_short": issue["draft"]["pos_short"]}}
    await client.patch(f"/issues/{issue['id']}", json=patch, headers=anna.headers)

    profile = {"full_name": "Иванов И. И.", "apartment": "12", "phone": "+79990001122"}
    await client.put("/users/me/profile", json=profile, headers=anna.headers)
    refreshed = (
        await client.post(f"/issues/{issue['id']}/refresh-letter", headers=anna.headers)
    ).json()
    assert refreshed["missing_applicant_fields"] == []
    assert "От: Иванов И. И., кв. 12, тел. +79990001122" in refreshed["draft"]["full"]
    assert "Очень прошу устранить" in refreshed["draft"]["full"]  # правки остались
    assert refreshed["draft"]["pos_short"] == issue["draft"]["pos_short"]


async def test_refresh_letter_only_for_own_drafts(
    client: httpx.AsyncClient, anna: Account, boris: Account
):
    issue = await create(client, anna)
    url = f"/issues/{issue['id']}/refresh-letter"
    assert (await client.post(url, headers=boris.headers)).status_code == 404
    await submit(client, anna, issue["id"])
    response = await client.post(url, headers=anna.headers)
    assert response.status_code == 409 and response.json()["code"] == "not_a_draft"
