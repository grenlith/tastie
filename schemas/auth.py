from pydantic import BaseModel, EmailStr, field_validator

from config import settings


class RegisterForm(BaseModel):
    username: str
    email: EmailStr
    password: str
    password_confirm: str
    invite_code: str = ""

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.lower().strip()
        if len(v) < 3:
            raise ValueError("username must be at least 3 characters")
        if len(v) > 30:
            raise ValueError("username must be at most 30 characters")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < settings.MIN_PASSWORD_LENGTH:
            raise ValueError(f"password must be at least {settings.MIN_PASSWORD_LENGTH} characters")
        return v

    def validate_passwords_match(self) -> list[str]:
        if self.password != self.password_confirm:
            return ["passwords do not match"]
        return []


class LoginForm(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        return v.lower().strip()
