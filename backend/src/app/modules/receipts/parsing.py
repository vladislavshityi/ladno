"""Разбор файла квитанции моделью с картинки или PDF. В запросе только изображение квитанции."""

import base64

from pydantic import TypeAdapter

from app.llm.client import LLMClient, Message
from app.llm.structured import ask_json
from app.modules.receipts.schemas import ParsedReceipt

_ADAPTER = TypeAdapter(ParsedReceipt)

_PROMPT = (
    "Ты разбираешь квитанцию ЖКХ. Верни только JSON без пояснений: "
    '{"period": "YYYY-MM", "management_company": {"name": "...", "inn": "..."}, '
    '"account_last4": "последние 4 цифры лицевого счёта", "area_m2": "54.30", "residents": 3, '
    '"lines": [{"service_code": "...", "service_name": "...", "unit": "м3", "volume": "4.770", '
    '"tariff": "68.40", "accrued": "326.27", "recalculation": "0.00", "total": "326.27", '
    '"method": "meter|norm|norm_increased|unknown"}], "total": "7412.55"}. '
    "service_code только из списка: maintenance, cold_water, hot_water, hot_water_heat, sewerage, "
    "heating, electricity, gas, waste, capital_repair, common_property_resources, intercom, other. "
    "Деньги и объёмы строками с точкой. Не возвращай ФИО, адрес, телефон и полный лицевой счёт. "
    "Чего нет в квитанции, то null; ничего не выдумывай."
)


def _file_part(data: bytes, content_type: str) -> dict:
    data_uri = f"data:{content_type};base64,{base64.b64encode(data).decode()}"
    if content_type == "application/pdf":
        return {"type": "file", "file": {"filename": "receipt.pdf", "file_data": data_uri}}
    return {"type": "image_url", "image_url": {"url": data_uri}}


async def extract_receipt(llm: LLMClient, data: bytes, content_type: str) -> ParsedReceipt:
    user: Message = {
        "role": "user",
        "content": [{"type": "text", "text": "Разбери квитанцию."}, _file_part(data, content_type)],
    }
    return await ask_json(llm, [{"role": "system", "content": _PROMPT}, user], _ADAPTER)
