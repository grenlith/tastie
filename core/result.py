from dataclasses import dataclass
from enum import Enum
from typing import Self


class ErrorKind(Enum):
    NOT_FOUND = "not_found"
    VALIDATION = "validation"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class Result[T]:
    """holds either a value or errors from service operations."""

    value: T | None
    errors: list[str]
    error_kind: ErrorKind | None = None

    @property
    def ok(self) -> bool:
        return self.value is not None and not self.errors

    @property
    def error(self) -> str | None:
        return self.errors[0] if self.errors else None

    @classmethod
    def success(cls, value: T) -> Self:
        return cls(value=value, errors=[], error_kind=None)

    @classmethod
    def failure(cls, *errors: str) -> Self:
        return cls(value=None, errors=list(errors), error_kind=ErrorKind.VALIDATION)

    @classmethod
    def not_found(cls, message: str = "Not found") -> Self:
        return cls(value=None, errors=[message], error_kind=ErrorKind.NOT_FOUND)

    @classmethod
    def conflict(cls, message: str) -> Self:
        return cls(value=None, errors=[message], error_kind=ErrorKind.CONFLICT)
