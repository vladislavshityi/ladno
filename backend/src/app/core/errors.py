from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code = 500
    default_code = "internal_error"

    def __init__(self, detail: str, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code or self.default_code


class NotFound(AppError):
    status_code = 404
    default_code = "not_found"


class Forbidden(AppError):
    status_code = 403
    default_code = "forbidden"


class Conflict(AppError):
    status_code = 409
    default_code = "conflict"


class Unauthorized(AppError):
    status_code = 401
    default_code = "unauthorized"


class ValidationError(AppError):
    status_code = 422
    default_code = "validation_error"


class PayloadTooLarge(AppError):
    status_code = 413
    default_code = "file_too_large"


class UnsupportedMedia(AppError):
    status_code = 415
    default_code = "unsupported_file"


class TooManyRequests(AppError):
    status_code = 429
    default_code = "rate_limited"


class BadGateway(AppError):
    status_code = 502
    default_code = "bad_gateway"


class ServiceUnavailable(AppError):
    status_code = 503
    default_code = "service_unavailable"


class GatewayTimeout(AppError):
    status_code = 504
    default_code = "gateway_timeout"


FIELD_LABELS = {
    "full_name": "ФИО",
    "phone": "Телефон",
    "email": "E-mail",
    "apartment": "Квартира",
    "entrance": "Подъезд",
    "custom_address": "Адрес",
    "custom_company_name": "Управляющая компания",
    "description": "Описание",
    "text": "Описание",
    "location_details": "Место",
    "external_ref": "Номер обращения",
    "period": "Период",
    "area_m2": "Площадь",
    "residents": "Проживающие",
    "total": "Итог",
    "volume": "Объём",
    "tariff": "Тариф",
    "accrued": "Начислено",
    "recalculation": "Перерасчёт",
    "service_name": "Услуга",
    "unit": "Единица измерения",
    "name": "Название",
    "inn": "ИНН",
    "account_last4": "Лицевой счёт",
    "content": "Сообщение",
    "q": "Запрос",
}

# Типы ошибок pydantic, у которых английский текст заменяется русским.
_TYPE_MESSAGES = {
    "missing": "Обязательное поле",
    "string_type": "Нужна строка",
    "int_type": "Нужно целое число",
    "int_parsing": "Нужно целое число",
    "decimal_type": "Нужно число",
    "decimal_parsing": "Нужно число",
    "bool_type": "Нужно да или нет",
    "uuid_parsing": "Некорректный идентификатор",
    "json_invalid": "Некорректный JSON",
    "too_short": "Нужна хотя бы одна запись",
}


def _message(err: dict) -> str:
    kind, ctx = err["type"], err.get("ctx", {})
    if kind == "value_error":
        return str(ctx.get("error", err["msg"]))
    if kind == "string_too_long":
        return f"Не длиннее {ctx['max_length']} символов"
    if kind == "string_too_short":
        return f"Не короче {ctx['min_length']} символов"
    if kind == "string_pattern_mismatch":
        return "Неверный формат"
    if kind in ("greater_than_equal", "greater_than"):
        return f"Не меньше {ctx.get('ge', ctx.get('gt'))}"
    if kind in ("less_than_equal", "less_than"):
        return f"Не больше {ctx.get('le', ctx.get('lt'))}"
    if kind in ("too_long", "list_type"):
        return "Слишком много записей" if kind == "too_long" else "Нужен список"
    return _TYPE_MESSAGES.get(kind, err["msg"])


def validation_fields(errors: list[dict]) -> dict[str, str]:
    """Ошибки по полям: ключ — путь к полю без «body» (например, lines.0.volume)."""
    result: dict[str, str] = {}
    for err in errors:
        path = ".".join(str(p) for p in err["loc"][1:])
        result.setdefault(path or "body", _message(err))
    return result


def _field_label(path: str) -> str:
    name = path.split(".")[-1]
    return FIELD_LABELS.get(name, name)


def _error_response(
    status_code: int,
    detail: str,
    code: str,
    headers: dict[str, str] | None = None,
    fields: dict[str, str] | None = None,
) -> JSONResponse:
    body = {"detail": detail, "code": code, "fields": fields or {}}
    return JSONResponse(body, status_code=status_code, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, Unauthorized) else None
        return _error_response(exc.status_code, exc.detail, exc.code, headers)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        return _error_response(exc.status_code, str(exc.detail), code)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = validation_fields(exc.errors())
        parts = [
            f"{_field_label(path)}: {text}" if path != "body" else text
            for path, text in fields.items()
        ]
        return _error_response(422, "; ".join(parts), "validation_error", fields=fields)
