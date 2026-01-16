from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from starlette.responses import Response

from config import settings
from core.auth import clear_session_cookie, set_session_cookie
from core.dependencies import CsrfProtected, CurrentUserOptional, DbSession, Templates, get_limiter
from schemas import extract_validation_errors
from schemas.auth import RegisterForm
from services.auth_service import AuthService
from services.invite_service import InviteService

router = APIRouter(tags=["auth"])
limiter = get_limiter()


@router.get("/register", response_class=HTMLResponse)
async def register_form(
    request: Request, user: CurrentUserOptional, templates: Templates
) -> Response:
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "errors": [],
            "username": "",
            "email": "",
            "invite_code": "",
            "require_invite_code": settings.REQUIRE_INVITE_CODE,
        },
    )


@router.post("/register", response_model=None)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register(
    request: Request,
    db: DbSession,
    templates: Templates,
    _: CsrfProtected,
    username: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    password_confirm: Annotated[str, Form()],
    invite_code: Annotated[str, Form()] = "",
) -> Response:
    errors: list[str] = []

    try:
        form = RegisterForm(
            username=username,
            email=email,
            password=password,
            password_confirm=password_confirm,
            invite_code=invite_code,
        )
        errors.extend(form.validate_passwords_match())
        username = form.username
    except ValidationError as e:
        errors.extend(extract_validation_errors(e))

    if settings.REQUIRE_INVITE_CODE and not errors:
        invite_service = InviteService(db)
        if not invite_code.strip():
            errors.append("Invite code is required")
        elif not await invite_service.is_code_valid(invite_code):
            errors.append("Invalid or already used invite code")

    if not errors:
        auth_service = AuthService(db)
        result = await auth_service.register_user(username, email, password)
        errors.extend(result.errors)

        if result.ok:
            user_obj = result.value
            assert user_obj is not None
            if settings.REQUIRE_INVITE_CODE:
                invite_service = InviteService(db)
                invite_result = await invite_service.validate_and_use_code(invite_code, user_obj.id)
                if not invite_result.ok:
                    errors.extend(invite_result.errors)

            if not errors:
                response = RedirectResponse(url="/", status_code=303)
                set_session_cookie(response, user_obj.id)
                return response

    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "errors": errors,
            "username": username,
            "email": email,
            "invite_code": invite_code,
            "require_invite_code": settings.REQUIRE_INVITE_CODE,
        },
    )


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, user: CurrentUserOptional, templates: Templates) -> Response:
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None, "username": ""})


@router.post("/login", response_model=None)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    db: DbSession,
    templates: Templates,
    _: CsrfProtected,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> Response:
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(username, password)

    if not user:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid username or password", "username": username},
        )

    response = RedirectResponse(url="/", status_code=303)
    set_session_cookie(response, user.id)
    return response


@router.post("/logout")
async def logout(_: CsrfProtected) -> RedirectResponse:
    response = RedirectResponse(url="/login", status_code=303)
    clear_session_cookie(response)
    return response
