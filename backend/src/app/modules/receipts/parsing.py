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

from app.core.text import numbers_in
from app.llm.client import LLMClient, Message, vision_model
from app.llm.structured import strip_fence
from app.modules.receipts.schemas import ParsedLine, ParsedReceipt

PARSE_MAX_TOKENS = 4000  # таблица на 15–20 строк в JSON с транскрипцией
MAX_SIDE = 2048  # крупнее модель всё равно уменьшит, а мелкий шрифт таблицы страдает
SUM_TOLERANCE_PCT = Decimal("0.005")
SUM_TOLERANCE_MIN = Decimal("1")

_LINE = TypeAdapter(ParsedLine)
_SUMMARY_ROW = re.compile(r"^\s*(итого|всего|к оплате)", re.I)
_HEADER = TypeAdapter(ParsedReceipt)

_PROMPT = (  # {today} подставляется при запросе
    "Ты разбираешь фото квитанции ЖКХ. Верни только JSON без пояснений в такой форме "
    "(в угловых скобках описание значения, а не пример): "
    '{"readable": <true или false>, "multiple_documents": <true или false>, '
    '"rows_text": ["<строка таблицы начислений дословно, как напечатана>"], '
    '"total_text": "<строка «Итого» и строка «К оплате» дословно>", '
    '"rows_count": <число строк таблицы начислений>, "period": "<YYYY-MM>", '
    '"management_company": {"name": "<название>", "inn": "<ИНН>"}, '
    '"account_last4": "<последние 4 цифры лицевого счёта>", "area_m2": "<число строкой>", '
    '"residents": <число>, '
    '"lines": [{"service_code": "<код из списка>", "service_name": "<название>", '
    '"unit": "<единица>", "volume": "<число строкой>", "tariff": "<число строкой>", '
    '"accrued": "<число строкой>", "recalculation": "<число строкой>", '
    '"total": "<число строкой>", "method": "meter|norm|norm_increased|unknown"}], '
    '"total": "<число строкой>", "amount_due": "<число строкой>"}. '
    "Порядок работы: сначала перепиши строки таблицы начислений в rows_text дословно, "
    "со всеми числами строки, затем заполни lines строго по rows_text: каждое число в lines "
    "должно быть напечатано в соответствующей строке rows_text. "
    "Если таблицу начислений не видно или текст нечитаем, верни readable=false и пустые "
    "rows_text и lines. Никогда не придумывай строки, услуги и суммы. "
    "Если на фото несколько платёжных документов (видны соседние квитанции), разбери один, "
    "самый крупный и полный, и верни multiple_documents=true. "
    "В lines перечисли ВСЕ строки таблицы сверху вниз, включая нулевые и строки перерасчёта: "
    "не объединяй их и не пропускай. Строки «Итого», «Всего», «К оплате» в lines не включай. "
    "Если у услуги есть отдельная строка или колонка общедомовых нужд (ОДН), прибавь её к "
    "accrued этой услуги, если так напечатан итог по услуге. "
    "total строки равен accrued + recalculation. "
    "total квитанции равен строке «Итого» — сумме начислений за период; "
    "amount_due — сумма «К оплате» с учётом долга или аванса, она может отличаться от total "
    "и быть отрицательной; если такой строки нет, null. "
    "service_code только из списка: maintenance, cold_water, hot_water, hot_water_heat, sewerage, "
    "heating, electricity, gas, waste, capital_repair, common_property_resources, intercom, other. "
    "Деньги и объёмы строками с точкой. Не возвращай ФИО, адрес, телефон и полный лицевой счёт. "
    "period — расчётный месяц квитанции (обычно в шапке «за <месяц> <год>»), год четырьмя цифрами. "
    "Сегодня {today}. "
    "Чего нет в квитанции, то null; ничего не выдумывай и не подставляй значения из описания."
)

_ORIENTATION_PROMPT = (
    "На фото документ с текстом. На сколько градусов по часовой стрелке повёрнут текст "
    "относительно нормального горизонтального чтения слева направо? "
    "Ответь одним числом: 0, 90, 180 или 270."
)

UNRELIABLE = "Не удалось надёжно прочитать квитанцию — проверьте строки или введите вручную."
UNREADABLE = "Не удалось прочитать квитанцию — сфотографируйте таблицу начислений чётче."
MULTIPLE = "На фото несколько квитанций, разобрана одна."
_THOUSANDS_GAP = re.compile(r"(?<![\d,.])(\d{1,3})[ \u00a0](\d{3})(?![\d])")


@dataclass
class Attempt:
    """Один ответ модели: разобранная квитанция и что в нём не сошлось."""

    receipt: ParsedReceipt
    rows_count: int | None
    rows_found: int  # строк в ответе, включая нечитаемые
    sum_diff: Decimal  # |сумма строк − итог|; 0, если итога нет
    readable: bool = True

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


def rotate_image(data: bytes, degrees: int) -> bytes:
    """Поворот изображения по часовой стрелке в обратную сторону от наклона текста."""
    if degrees not in (90, 180, 270):
        return data
    try:
        with Image.open(io.BytesIO(data)) as image:
            fixed = image.rotate(degrees, expand=True)
            out = io.BytesIO()
            fixed.convert("RGB").save(out, format="JPEG", quality=90)
    except (UnidentifiedImageError, OSError):
        return data
    return out.getvalue()


def _image_part(image: bytes, content_type: str, detail: str) -> dict:
    data_uri = f"data:{content_type};base64,{base64.b64encode(image).decode()}"
    return {"type": "image_url", "image_url": {"url": data_uri, "detail": detail}}


def _pdf_part(data: bytes) -> dict:
    data_uri = f"data:application/pdf;base64,{base64.b64encode(data).decode()}"
    return {"type": "file", "file": {"filename": "receipt.pdf", "file_data": data_uri}}


async def detect_rotation(llm: LLMClient, image: bytes, content_type: str) -> int:
    """Дешёвый запрос: на сколько градусов повёрнут текст. Не число — не поворачиваем."""
    messages: list[Message] = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": _ORIENTATION_PROMPT},
                _image_part(image, content_type, "low"),
            ],
        }
    ]
    answer = await llm.complete(messages, model=vision_model(), max_tokens=5)
    match = re.fullmatch(r"\s*(0|90|180|270)\s*°?\s*\.?\s*", answer)
    return int(match.group(1)) if match else 0


def _supported_numbers(text: str) -> set[Decimal]:
    """Числа из текста квитанции: пробелы разрядов убраны, запятая как точка, знак не важен."""
    return {Decimal(x) for x in numbers_in(_THOUSANDS_GAP.sub(r"\1\2", text))}


def _line_total(line: ParsedLine) -> Decimal:
    return line.total if line.total is not None else line.accrued + line.recalculation


def _is_summary_row(item: object) -> bool:
    """Модель иногда возвращает строку «Итого» как услугу: тогда итог задвоился бы."""
    return isinstance(item, dict) and bool(_SUMMARY_ROW.match(str(item.get("service_name", ""))))


def _is_confirmed(line: ParsedLine, printed: set[Decimal]) -> bool:
    """Сумма строки должна быть напечатана в транскрипции таблицы."""
    return line.accrued in printed or _line_total(line) in printed


def _parse_answer(text: str) -> Attempt:
    """Строки проверяются по одной: нечитаемую или не найденную в транскрипции отбрасываем."""
    raw = json.loads(strip_fence(text))
    raw_lines = raw.pop("lines", None) or []
    rows_count = raw.pop("rows_count", None)
    rows_text = raw.pop("rows_text", None) or []
    total_text = raw.pop("total_text", None) or ""
    amount_due = raw.pop("amount_due", None)
    multiple = raw.pop("multiple_documents", False)
    if raw.pop("readable", True) is False:
        receipt = _HEADER.validate_python({"warnings": [UNREADABLE]})
        return Attempt(receipt, None, 0, Decimal(0), readable=False)

    receipt = _HEADER.validate_python({**raw, "lines": [], "warnings": []})
    printed = _supported_numbers("\n".join(map(str, rows_text)))
    raw_lines = [x for x in raw_lines if not _is_summary_row(x)]
    parsed: list[ParsedLine] = []
    for item in raw_lines:
        try:
            parsed.append(_LINE.validate_python(item))
        except ValidationError:
            name = item.get("service_name") if isinstance(item, dict) else None
            receipt.warnings.append(f"Не удалось прочитать строку: {name or 'без названия'}")
    confirmed = [x for x in parsed if _is_confirmed(x, printed)]
    for line in parsed:
        if line not in confirmed:
            receipt.warnings.append(f"Строка не найдена в тексте квитанции: {line.service_name}")
    receipt.lines = confirmed

    total_printed = receipt.total is None or receipt.total in _supported_numbers(str(total_text))
    if (parsed and len(confirmed) * 2 < len(parsed)) or not total_printed:
        receipt.warnings.insert(0, UNRELIABLE)
    if multiple is True:
        receipt.warnings.append(MULTIPLE)
    due = _money_or_none(amount_due)
    if due is not None and receipt.total is not None and due != receipt.total:
        receipt.warnings.append(f"К оплате с учётом долга или аванса: {due:.2f} ₽.")

    lines_total = sum((_line_total(x) for x in receipt.lines), Decimal(0))
    sum_diff = abs(lines_total - receipt.total) if receipt.total is not None else Decimal(0)
    rows_count = rows_count if isinstance(rows_count, int) else None
    return Attempt(receipt, rows_count, len(raw_lines), sum_diff)


def _money_or_none(value: object) -> Decimal | None:
    try:
        return Decimal(str(value)) if value is not None else None
    except ArithmeticError:
        return None


def _better(first: Attempt | None, second: Attempt | None) -> Attempt:
    candidates = [x for x in (first, second) if x is not None]
    return min(candidates, key=lambda x: (not x.readable, x.rows_diff, x.sum_diff))


async def _ask(llm: LLMClient, messages: list[Message]) -> tuple[Attempt | None, str, str]:
    """Ответ модели, его текст и ошибка разбора (пусто, если разобрался)."""
    text = await llm.complete(
        messages, json_mode=True, model=vision_model(), max_tokens=PARSE_MAX_TOKENS
    )
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


async def _file_part(llm: LLMClient, data: bytes, content_type: str) -> dict:
    """PDF отдаём как есть; фото готовим, а при необходимости разворачиваем по ответу модели."""
    if content_type == "application/pdf":
        return _pdf_part(data)
    image = prepare_image(data)
    kind = "image/jpeg" if image is not data else content_type
    degrees = await detect_rotation(llm, image, kind)
    if degrees:
        image, kind = rotate_image(image, degrees), "image/jpeg"
    return _image_part(image, kind, "high")


async def extract_receipt(llm: LLMClient, data: bytes, content_type: str) -> ParsedReceipt:
    """Не больше трёх запросов: ориентация, разбор и повтор, если строки или сумма не сошлись."""
    part = await _file_part(llm, data, content_type)
    user: Message = {
        "role": "user",
        "content": [{"type": "text", "text": "Разбери квитанцию."}, part],
    }
    messages: list[Message] = [
        {"role": "system", "content": _PROMPT.replace("{today}", date.today().isoformat())},
        user,
    ]
    first, text, error = await _ask(llm, messages)
    if first is not None and (first.converges or not first.readable):
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
