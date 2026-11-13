from fastapi import APIRouter, Response, status

from app.core.deps import ConsentedUser, CurrentUser, SessionDep
from app.modules.users import service
from app.modules.users.schemas import ConsentRequest, ProfileUpdate, UserExport, UserRead

router = APIRouter(prefix="/users/me", tags=["users"])


@router.get("", response_model=UserRead)
async def get_me(user: CurrentUser) -> UserRead:
    return service.to_read(user)


@router.put("/profile", response_model=UserRead)
async def update_profile(data: ProfileUpdate, user: ConsentedUser, session: SessionDep) -> UserRead:
    """Профиль «Мой дом»: дом, подъезд и УК. ФИО, телефон и квартира на сервер не отправляются."""
    return service.to_read(await service.update_profile(session, user, data))


@router.get("/export", response_model=UserExport)
async def export_me(user: CurrentUser, session: SessionDep) -> UserExport:
    """Выгрузка всех данных пользователя одним JSON."""
    return await service.export_data(session, user)


@router.post("/consent", response_model=UserRead)
async def accept_consent(data: ConsentRequest, user: CurrentUser, session: SessionDep) -> UserRead:
    """Фиксирует согласие на обработку данных: версия текста и время."""
    return service.to_read(await service.accept_consent(session, user, data.version))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(user: CurrentUser, session: SessionDep) -> Response:
    """Удаляет аккаунт и все его данные без возможности восстановления."""
    await service.delete_account(session, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
