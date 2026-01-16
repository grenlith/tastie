from pydantic import ValidationError

from schemas.auth import LoginForm, RegisterForm
from schemas.bookmark import BookmarkForm

# pydantic prefixes custom validator messages with this
_PYDANTIC_VALUE_ERROR_PREFIX = "Value error, "


def extract_validation_error(e: ValidationError) -> str:
    msg = e.errors()[0]["msg"]
    if msg.startswith(_PYDANTIC_VALUE_ERROR_PREFIX):
        return msg[len(_PYDANTIC_VALUE_ERROR_PREFIX) :]
    return msg


def extract_validation_errors(e: ValidationError) -> list[str]:
    errors: list[str] = []
    for error in e.errors():
        msg = error["msg"]
        if msg.startswith(_PYDANTIC_VALUE_ERROR_PREFIX):
            msg = msg[len(_PYDANTIC_VALUE_ERROR_PREFIX) :]
        errors.append(msg)
    return errors


__all__ = [
    "RegisterForm",
    "LoginForm",
    "BookmarkForm",
    "extract_validation_error",
    "extract_validation_errors",
]
