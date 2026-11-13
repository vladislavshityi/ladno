"""Разбор файла квитанции моделью с картинки или PDF. В запросе только изображение квитанции."""

import base64
import io
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import TypeAdapter, ValidationError

from app.llm.client import LLMClient, Message, vision_model
from app.llm.structured import strip_fence
from app.modules.receipts.schemas import ParsedLine, ParsedReceipt

MAX_SIDE = 2048  # крупнее модель всё равно уменьшит, а мелкий шрифт таблицы страдает
SUM_TOLERANCE_PCT = Decimal("0.005")
SUM_TOLERANCE_MIN = Decimal("1")

_LINE = TypeAdapter(ParsedLine)
_SUMMARY_ROW = re.compile(r"^\s*(итого|всего|к оплате)", re.I)
_HEADER = TypeAdapter(ParsedReceipt)

_PROMPT = (  # {today} подставляется при запросе
    "Ты разбираешь квитанцию ЖКХ. Верни только JSON без пояснений: "
    '{"rows_count": 11, "period": "YYYY-MM", "management_company": {"name": "...", "inn": "..."}, '
    '"account_last4": "последние 4 цифры лицевого счёта", "area_m2": "54.30", "residents": 3, '
    '"lines": [{"service_code": "...", "service_name": "...", "unit": "м3", "volume": "4.770", '
    '"tariff": "68.40", "accrued": "326.27", "recalculation": "0.00", "total": "326.27", '
    '"method": "meter|norm|norm_increased|unknown"}], "total": "7412.55"}. '
    "Сначала посчитай строки в таблице начислений и верни их число в rows_count. "
    "В lines перечисли ВСЕ строки таблицы сверху вниз, включая нулевые и строки перерасчёта: "
    "не объединяй их и не пропускай. Строки «Итого», «Всего», «К оплате» в lines не включай. "
    "total строки равен accrued + recalculation, "
    "а total квитанции — итог «к оплате». "
    "service_code только из списка: maintenance, cold_water, hot_water, hot_water_heat, sewerage, "
    "heating, electricity, gas, waste, capital_repair, common_property_resources, intercom, other. "
    "Деньги и объёмы строками с точкой. Не возвращай ФИО, адрес, телефон и полный лицевой счёт. "
    "period — расчётный месяц квитанции (обычно в шапке «за <месяц> <год>»), год четырьмя цифрами. "
    "Сегодня {today}. "
    "Чего нет в квитанции, то null; ничего не выдумывай."
)


@dataclass
class Attempt:
    """Один ответ модели: разобранная квитанция и что в нём не сошлось."""

    receipt: ParsedReceipt
    rows_count: int | None
    rows_found: int  # строк в ответе, включая нечитаемые
    sum_diff: Decimal  # |сумма строк − итог|; 0, если итога нет

    @property
    def rows_diff(self) -> int:
        return 0 if self.rows_count is None else abs(self.rows_count - self.rows_found)

    @property
    def converges(self) -> bool:
        tolerance = max(SUM_TOLERANCE_MIN, abs(self.receipt.total or 0) * SUM_TOLERANCE_PCT)
        return self.rows_diff == 0 and self.sum_diff <= tolerance

    @property
    def mismatch(self) -> str:
        lines_total = sum((_line_total(x) for x in self.receipt.lines), Decimal(0))
        return (
            f"строк {self.rows_found}, а в таблице {self.rows_count}; "
            f"сумма строк {lines_total}, итог {self.receipt.total}"
        )


def prepare_image(data: bytes) -> bytes:
    """Поворот по EXIF, RGB и длинная сторона не больше MAX_SIDE; нечитаемое отдаём как есть."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            picture = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError):
        return data
    picture.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    picture.save(out, format="JPEG", quality=90)
    return out.getvalue()


def _file_part(data: bytes, content_type: str) -> dict:
    if content_type == "application/pdf":
        data_uri = f"data:{content_type};base64,{base64.b64encode(data).decode()}"
        return {"type": "file", "file": {"filename": "receipt.pdf", "file_data": data_uri}}
    image = prepare_image(data)
    kind = "image/jpeg" if image is not data else content_type
    data_uri = f"data:{kind};base64,{base64.b64encode(image).decode()}"
    return {"type": "image_url", "image_url": {"url": data_uri, "detail": "high"}}


def _line_total(line: ParsedLine) -> Decimal:
    return line.total if line.total is not None else line.accrued + line.recalculation


def _is_summary_row(item: object) -> bool:
    """Модель иногда возвращает строку «Итого» как услугу: тогда итог задвоился бы."""
    return isinstance(item, dict) and bool(_SUMMARY_ROW.match(str(item.get("service_name", ""))))


def _parse_answer(text: str) -> Attempt:
    """Строки проверяются по одной: нечитаемую отбрасываем с предупреждением, остальные живут."""
    raw = json.loads(strip_fence(text))
    raw_lines = raw.pop("lines", None) or []
    rows_count = raw.pop("rows_count", None)
    receipt = _HEADER.validate_python({**raw, "lines": [], "warnings": []})
    raw_lines = [x for x in raw_lines if not _is_summary_row(x)]
    for item in raw_lines:
        try:
            receipt.lines.append(_LINE.validate_python(item))
        except ValidationError:
            name = item.get("service_name") if isinstance(item, dict) else None
            receipt.warnings.append(f"Не удалось прочитать строку: {name or 'без названия'}")
    lines_total = sum((_line_total(x) for x in receipt.lines), Decimal(0))
    sum_diff = abs(lines_total - receipt.total) if receipt.total is not None else Decimal(0)
    rows_count = rows_count if isinstance(rows_count, int) else None
    return Attempt(receipt, rows_count, len(raw_lines), sum_diff)


def _better(first: Attempt | None, second: Attempt | None) -> Attempt:
    candidates = [x for x in (first, second) if x is not None]
    return min(candidates, key=lambda x: (x.rows_diff, x.sum_diff))


async def _ask(llm: LLMClient, messages: list[Message]) -> tuple[Attempt | None, str, str]:
    """Ответ модели, его текст и ошибка разбора (пусто, если разобрался)."""
    text = await llm.complete(messages, json_mode=True, model=vision_model())
    try:
        return _parse_answer(text), text, ""
    except (ValueError, ValidationError, AttributeError) as exc:
        return None, text, str(exc)


def _followup(first_text: str, problem: str) -> Message:
    return {
        "role": "user",
        "content": (
            f"Твой прошлый ответ:\n{first_text}\n\nПроблема: {problem}. "
            "Посмотри на квитанцию ещё раз, найди пропущенные или неверно прочитанные строки "
            "и верни полный исправленный JSON в том же формате."
        ),
    }


async def extract_receipt(llm: LLMClient, data: bytes, content_type: str) -> ParsedReceipt:
    """Не больше двух запросов: второй только если строки или сумма не сошлись."""
    user: Message = {
        "role": "user",
        "content": [{"type": "text", "text": "Разбери квитанцию."}, _file_part(data, content_type)],
    }
    messages: list[Message] = [
        {"role": "system", "content": _PROMPT.replace("{today}", date.today().isoformat())},
        user,
    ]
    first, text, error = await _ask(llm, messages)
    if first is not None and first.converges:
        return first.receipt

    problem = first.mismatch if first else f"ответ не разобрался ({error})"
    second, _, error = await _ask(llm, [*messages, _followup(text, problem)])
    if first is None and second is None:
        raise ValueError(error)
    best = _better(first, second)
    if not best.converges and best.rows_diff:
        best.receipt.warnings.append(
            f"Распознано строк: {best.rows_found}, в таблице их {best.rows_count}. "
            "Проверьте, не пропущены ли начисления."
        )
    return best.receipt
