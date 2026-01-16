from __future__ import annotations

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from models.models import Bookmark

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class Cursor:
    """timestamp + id cursor, base64 encoded for transport."""

    created_at: datetime
    id: int

    def encode(self) -> str:
        data = {"ts": self.created_at.isoformat(), "id": self.id}
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()

    @classmethod
    def decode(cls, encoded: str) -> Cursor | None:
        try:
            data = json.loads(base64.urlsafe_b64decode(encoded))
            return cls(created_at=datetime.fromisoformat(data["ts"]), id=data["id"])
        except (ValueError, KeyError, json.JSONDecodeError):
            return None


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    next_cursor: str | None
    has_more: bool

    @property
    def total_in_page(self) -> int:
        return len(self.items)

    @classmethod
    def empty(cls) -> Page[T]:
        return cls(items=[], next_cursor=None, has_more=False)

    @classmethod
    def from_results(
        cls,
        items: list[T],
        limit: int,
        cursor_getter: Callable[[T], Cursor],
    ) -> Page[T]:
        # query should fetch limit + 1 items to detect has_more
        has_more = len(items) > limit
        page_items = items[:limit] if has_more else items

        next_cursor = None
        if page_items and has_more:
            last_item = page_items[-1]
            next_cursor = cursor_getter(last_item).encode()

        return cls(items=page_items, next_cursor=next_cursor, has_more=has_more)


def get_bookmark_cursor(bookmark: Bookmark) -> Cursor:
    return Cursor(created_at=bookmark.created_at, id=bookmark.id)
