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
