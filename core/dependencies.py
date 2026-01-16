from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.auth import verify_session_token
from core.csrf import validate_csrf
from core.database import async_session
from models.models import User


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user_optional(
    request: Request,
    db: DbSession,
) -> User | None:
    from services.auth_service import AuthService

    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        return None

    user_id = verify_session_token(token)
    if not user_id:
        return None

    auth_service = AuthService(db)
    return await auth_service.get_user_by_id(user_id)


async def get_current_user(
    request: Request,
    db: DbSession,
) -> User:
    user = await get_current_user_optional(request, db)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]


async def validate_csrf_token(request: Request) -> None:
    await validate_csrf(request)


CsrfProtected = Annotated[None, Depends(validate_csrf_token)]


def get_client_ip(request: Request) -> str:
    if settings.TRUST_PROXY:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # format: "client, proxy1, proxy2" - first is original
            return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


def get_limiter() -> Limiter:
    return Limiter(key_func=get_client_ip, enabled=settings.ENVIRONMENT != "test")


def get_templates(request: Request) -> Jinja2Templates:
    templates: Jinja2Templates = request.app.state.templates
    return templates


Templates = Annotated[Jinja2Templates, Depends(get_templates)]
