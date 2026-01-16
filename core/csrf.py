import secrets

from fastapi import HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config import settings

_csrf_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="csrf")


def generate_csrf_token() -> str:
    random_value = secrets.token_urlsafe(32)
    return _csrf_serializer.dumps(random_value)


def verify_csrf_token(token: str) -> bool:
    try:
        _csrf_serializer.loads(token, max_age=settings.CSRF_TOKEN_EXPIRY)
        return True
    except (BadSignature, SignatureExpired):
        return False


async def validate_csrf(request: Request) -> None:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    token: str | None = None

    if settings.CSRF_HEADER_NAME in request.headers:
        token = request.headers[settings.CSRF_HEADER_NAME]

    if not token:
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("application/x-www-form-urlencoded") or content_type.startswith(
            "multipart/form-data"
        ):
            form = await request.form()
            form_token = form.get(settings.CSRF_FORM_FIELD)
            if isinstance(form_token, str):
                token = form_token

    if not token or not verify_csrf_token(token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


def get_csrf_token(request: Request) -> str:
    if not hasattr(request.state, "csrf_token"):
        request.state.csrf_token = generate_csrf_token()
    token: str = request.state.csrf_token
    return token
