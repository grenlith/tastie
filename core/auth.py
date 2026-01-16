from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config import settings

_password_hasher = PasswordHasher()
_serializer = URLSafeTimedSerializer(settings.SECRET_KEY)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        _password_hasher.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


def create_session_token(user_id: int) -> str:
    return _serializer.dumps({"user_id": user_id})


def verify_session_token(token: str) -> int | None:
    try:
        data: dict[str, int] = _serializer.loads(token, max_age=settings.SESSION_EXPIRY_SECONDS)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None


def set_session_cookie(response: RedirectResponse, user_id: int) -> None:
    token = create_session_token(user_id)
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.IS_PRODUCTION,
        samesite="lax",
        max_age=settings.SESSION_EXPIRY_SECONDS,
    )


def clear_session_cookie(response: RedirectResponse) -> None:
    response.delete_cookie(key=settings.COOKIE_NAME)
