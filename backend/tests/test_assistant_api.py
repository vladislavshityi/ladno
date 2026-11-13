import json

import httpx

from app.core.errors import BadGateway
from tests.conftest import Account, FakeLLM


async def chat(client: httpx.AsyncClient, who: Account, text: str = "Куда жаловаться на яму?"):
    return await client.post(
        "/assistant/chat",
        json={"messages": [{"role": "user", "content": text}]},
        headers=who.headers,
    )


def events(response: httpx.Response) -> list[str]:
    return [block for block in response.text.split("\n\n") if block]


async def test_chat_without_llm_is_503(client: httpx.AsyncClient, anna: Account):
    response = await chat(client, anna)
    assert response.status_code == 503 and response.json()["code"] == "llm_unavailable"
    assert "недоступен" in response.json()["detail"]


async def test_chat_streams_chunks_then_done(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.chunks = ["Обратитесь ", "в управление дорог."]
    response = await chat(client, anna)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert events(response) == [
        'data: {"delta": "Обратитесь "}',
        'data: {"delta": "в управление дорог."}',
        "data: [DONE]",
    ]


async def test_chat_error_in_the_middle_is_an_event(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.chunks = ["Начало"]
    llm.error = BadGateway("упала", "llm_error")
    blocks = events(await chat(client, anna))
    assert blocks[0] == 'data: {"delta": "Начало"}'
    assert blocks[1].startswith("event: error\n") and '"llm_error"' in blocks[1]
    assert blocks[-1] == "data: [DONE]"


async def test_chat_prompt_has_region_facts_and_own_data_only(
    client: httpx.AsyncClient, anna: Account, boris: Account, llm: FakeLLM
):
    llm.replies = ["[]"]
    await client.post("/receipts/samples/2026-11", headers=anna.headers)
    await client.post(
        "/issues", json={"category": "pothole", "answers": {"place": "road"}}, headers=anna.headers
    )
    llm.chunks = ["ок"]
    await chat(client, anna, "что у меня с квитанцией?")
    system = llm.calls[-1][0]["content"]
    assert llm.calls[-1][1] == {"role": "user", "content": "что у меня с квитанцией?"}
    assert "Управление дорог администрации г. Владивостока" in system and "ПП РФ № 354" in system
    assert "Квитанция за 2026-11, итого 11274.07" in system
    assert "pothole" in system and "Нужно ли" not in system

    await chat(client, boris)
    other = llm.calls[-1][0]["content"]
    assert "11274.07" not in other and "Данных пользователя пока нет" in other


async def test_chat_validates_messages(client: httpx.AsyncClient, anna: Account, llm: FakeLLM):
    for payload in ({"messages": []}, {"messages": [{"role": "system", "content": "x"}]},
                    {"messages": [{"role": "user", "content": ""}]}):  # fmt: skip
        response = await client.post("/assistant/chat", json=payload, headers=anna.headers)
        assert response.status_code == 422
    assert json.dumps(llm.calls) == "[]"


async def test_chat_prompt_has_code_computed_changes(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    llm.replies = ["[]"]
    for sample in ("2026-10", "2026-11"):
        await client.post(f"/receipts/samples/{sample}", headers=anna.headers)
    llm.chunks = ["ок"]
    await chat(client, anna, "почему выросла?")
    system = llm.calls[-1][0]["content"]
    assert "Изменения 2026-10 -> 2026-11, итого +3287.01 ₽" in system
    assert "Горячее водоснабжение: +646.56 ₽" in system and "norm_increased" in system


async def make_receipts(client: httpx.AsyncClient, who: Account, llm: FakeLLM) -> list[str]:
    llm.replies = ["[]"]
    ids = []
    for sample in ("2026-09", "2026-10", "2026-11"):
        response = await client.post(f"/receipts/samples/{sample}", headers=who.headers)
        ids.append(response.json()["id"])
    return ids


async def ask(client: httpx.AsyncClient, who: Account, llm: FakeLLM, **context) -> str:
    llm.chunks = ["ок"]
    response = await client.post(
        "/assistant/chat",
        json={"messages": [{"role": "user", "content": "вопрос"}], **context},
        headers=who.headers,
    )
    assert response.status_code == 200, response.text
    return llm.calls[-1][0]["content"]


async def test_chat_selected_receipts_only(client: httpx.AsyncClient, anna: Account, llm: FakeLLM):
    sept, octo, _ = await make_receipts(client, anna, llm)
    one = await ask(client, anna, llm, receipt_ids=[sept])
    assert "Квитанция за 2026-09" in one
    assert "Квитанция за 2026-10" not in one and "Изменения" not in one

    two = await ask(client, anna, llm, receipt_ids=[sept, octo])
    assert "Квитанция за 2026-09" in two and "Квитанция за 2026-11" not in two
    assert "Изменения 2026-09 -> 2026-10" in two


async def test_chat_empty_lists_exclude_data(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    await make_receipts(client, anna, llm)
    await client.post(
        "/issues", json={"category": "pothole", "answers": {"place": "road"}}, headers=anna.headers
    )
    system = await ask(client, anna, llm, receipt_ids=[], issue_ids=[])
    assert "Квитанция за" not in system and "pothole" not in system
    assert "Данных пользователя пока нет" in system


async def test_chat_selected_issue_only(client: httpx.AsyncClient, anna: Account, llm: FakeLLM):
    llm.replies = ["[]"]
    payloads = [
        {"category": "pothole", "answers": {"place": "road"}},
        {"category": "stairwell_lighting", "answers": {"scope": "floor", "duration": "week_plus"}},
    ]
    created = [
        (await client.post("/issues", json=p, headers=anna.headers)).json() for p in payloads
    ]
    system = await ask(client, anna, llm, issue_ids=[created[0]["id"]], receipt_ids=[])
    assert "pothole" in system and "stairwell_lighting" not in system


async def test_chat_foreign_or_unknown_ids_are_404(
    client: httpx.AsyncClient, anna: Account, boris: Account, llm: FakeLLM
):
    receipt_id = (await make_receipts(client, anna, llm))[0]
    issue = await client.post(
        "/issues", json={"category": "pothole", "answers": {"place": "road"}}, headers=anna.headers
    )
    missing = "00000000-0000-0000-0000-000000000000"
    for context in (
        {"receipt_ids": [receipt_id]},
        {"issue_ids": [issue.json()["id"]]},
        {"receipt_ids": [missing]},
    ):
        response = await client.post(
            "/assistant/chat",
            json={"messages": [{"role": "user", "content": "вопрос"}], **context},
            headers=boris.headers,
        )
        assert response.status_code == 404


async def test_chat_prompt_has_no_personal_data(
    client: httpx.AsyncClient, anna: Account, llm: FakeLLM
):
    await client.patch(
        "/users/me",
        json={"full_name": "Иванова Анна Сергеевна", "phone": "+79990001122", "apartment": "77"},
        headers=anna.headers,
    )
    await make_receipts(client, anna, llm)
    system = await ask(client, anna, llm)
    for secret in ("Иванова", "79990001122", "кв. 77"):
        assert secret not in system


async def test_chat_limits_selection_size(client: httpx.AsyncClient, anna: Account, llm: FakeLLM):
    ids = [f"00000000-0000-0000-0000-00000000000{i}" for i in range(6)]
    response = await client.post(
        "/assistant/chat",
        json={"messages": [{"role": "user", "content": "x"}], "issue_ids": ids},
        headers=anna.headers,
    )
    assert response.status_code == 422
