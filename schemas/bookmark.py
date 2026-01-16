from urllib.parse import urlparse

from pydantic import BaseModel, field_validator

from models.models import Visibility

# prevent javascript: XSS and other dangerous schemes
ALLOWED_URL_SCHEMES = {"http", "https", "gemini", "gopher"}


class BookmarkForm(BaseModel):
    url: str
    title: str
    description: str = ""
    tags: str = ""
    visibility: str = Visibility.PUBLIC

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: str) -> str:
        parsed = urlparse(v)
        scheme = parsed.scheme.lower()

        if not scheme:
            raise ValueError("site must include a scheme (e.g., gemini://)")

        if scheme not in ALLOWED_URL_SCHEMES:
            raise ValueError(
                f"uri scheme '{scheme}' is not allowed. valid schemes: {ALLOWED_URL_SCHEMES}"
            )

        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title is required")
        if len(v) > 500:
            raise ValueError("title must be at most 500 characters")
        return v

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: str) -> str:
        return v.strip()

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        if v not in Visibility.ALL:
            return Visibility.PUBLIC
        return v
