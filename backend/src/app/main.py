from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

import app.models
from app.core.config import get_settings
from app.core.db import get_engine
from app.core.errors import register_exception_handlers
from app.core.schemas import ErrorResponse
from app.modules.assistant.router import router as assistant_router
from app.modules.auth.router import router as auth_router
from app.modules.bot.router import router as bot_router
from app.modules.houses.router import router as houses_router
from app.modules.issues.photos import router as photos_router
from app.modules.issues.router import router as issues_router
from app.modules.receipts.router import router as receipts_router
from app.modules.submissions.router import router as submissions_router
from app.modules.users.router import router as users_router

DESCRIPTION = (
    "Помощник жителя Владивостока по ЖКХ: кому и как пожаловаться на проблему дома или двора, "
    "понятный разбор квитанции, письмо на перерасчёт и ассистент. Вход только через Telegram."
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await get_engine().dispose()


def _operation_id(route: APIRoute) -> str:
    """Короткие имена операций (login_widget, list_issues): из них генерируется клиент фронтенда."""
    return route.name


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ладно API",
        version="1.0.0",
        description=DESCRIPTION,
        lifespan=lifespan,
        generate_unique_id_function=_operation_id,
        responses={
            401: {"model": ErrorResponse, "description": "Нужен вход"},
            404: {"model": ErrorResponse, "description": "Не найдено"},
            422: {"model": ErrorResponse, "description": "Некорректный запрос"},
        },
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    api = APIRouter(prefix="/api")
    for router in (
        auth_router,
        users_router,
        houses_router,
        issues_router,
        submissions_router,
        photos_router,
        receipts_router,
        assistant_router,
        bot_router,
    ):
        api.include_router(router)

    @api.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api)
    return app


app = create_app()
