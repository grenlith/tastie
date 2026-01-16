from dataclasses import dataclass
from enum import Enum
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.models import Bookmark, User, Visibility


class ViewContext(Enum):
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    OWNER = "owner"
    PROFILE_PUBLIC = "profile_public"
    PROFILE_AUTH = "profile_auth"


@dataclass(frozen=True)
class VisibilityFilter:
    context: ViewContext
    owner_id: int | None = None

    def apply[T: tuple[Any, ...]](self, query: Select[T]) -> Select[T]:
        match self.context:
            case ViewContext.PUBLIC:
                return query.where(Bookmark.visibility == Visibility.PUBLIC)
            case ViewContext.AUTHENTICATED:
                return query.where(
                    Bookmark.visibility.in_([Visibility.PUBLIC, Visibility.AUTHENTICATED])
                )
            case ViewContext.OWNER:
                if self.owner_id is None:
                    raise ValueError("owner_id required for OWNER context")
                return query.where(Bookmark.user_id == self.owner_id)
            case ViewContext.PROFILE_PUBLIC:
                return query.where(
                    Bookmark.user_id == self.owner_id,
                    Bookmark.visibility == Visibility.PUBLIC,
                )
            case ViewContext.PROFILE_AUTH:
                return query.where(
                    Bookmark.user_id == self.owner_id,
                    Bookmark.visibility.in_([Visibility.PUBLIC, Visibility.AUTHENTICATED]),
                )

    @classmethod
    def for_anonymous(cls) -> VisibilityFilter:
        return cls(ViewContext.PUBLIC)

    @classmethod
    def for_authenticated(cls) -> VisibilityFilter:
        return cls(ViewContext.AUTHENTICATED)

    @classmethod
    def for_owner(cls, user_id: int) -> VisibilityFilter:
        return cls(ViewContext.OWNER, owner_id=user_id)

    @classmethod
    def for_profile(cls, profile_user_id: int, viewer_id: int | None) -> VisibilityFilter:
        if viewer_id == profile_user_id:
            return cls.for_owner(profile_user_id)
        context = ViewContext.PROFILE_AUTH if viewer_id else ViewContext.PROFILE_PUBLIC
        return cls(context, owner_id=profile_user_id)

    @classmethod
    def for_user(cls, user: User | None) -> VisibilityFilter:
        return cls.for_authenticated() if user else cls.for_anonymous()


def escape_like_pattern(pattern: str) -> str:
    return pattern.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_bookmarks_query(
    visibility: VisibilityFilter,
    tag: str | None = None,
) -> Select[tuple[Bookmark]]:
    query = select(Bookmark).options(selectinload(Bookmark.user))
    query = visibility.apply(query)

    if tag:
        escaped_tag = escape_like_pattern(tag)
        query = query.where(Bookmark.tags.like(f"%{escaped_tag}%", escape="\\"))

    return query.order_by(Bookmark.created_at.desc())


async def get_all_tags(
    db: AsyncSession,
    visibility: VisibilityFilter,
) -> list[tuple[str, int]]:
    query = select(Bookmark.tags)
    query = visibility.apply(query)

    result = await db.execute(query)

    all_tags: dict[str, int] = {}
    for (tags,) in result:
        for tag in tags.split():
            all_tags[tag] = all_tags.get(tag, 0) + 1
    return sorted(all_tags.items(), key=lambda x: (-x[1], x[0]))


async def get_top_tags(
    db: AsyncSession,
    visibility: VisibilityFilter,
    limit: int = 5,
) -> list[tuple[str, int]]:
    """return top N tags by bookmark count."""
    all_tags = await get_all_tags(db, visibility)
    return all_tags[:limit]


async def get_popular_bookmarks_for_tag(
    db: AsyncSession,
    tag: str,
    visibility: VisibilityFilter,
    limit: int = 3,
) -> list[tuple[Bookmark, int]]:
    """
    get top bookmarks for a tag
    use the oldest as canonical
    """
    query = build_bookmarks_query(visibility, tag)
    result = await db.execute(query)
    bookmarks = list(result.scalars().all())

    url_data: dict[str, dict[str, Any]] = {}
    for bookmark in bookmarks:
        if bookmark.url not in url_data:
            url_data[bookmark.url] = {
                "oldest_bookmark": bookmark,
                "user_ids": {bookmark.user_id},
            }
        else:
            url_data[bookmark.url]["user_ids"].add(bookmark.user_id)
            if bookmark.created_at < url_data[bookmark.url]["oldest_bookmark"].created_at:
                url_data[bookmark.url]["oldest_bookmark"] = bookmark

    ranked = [(data["oldest_bookmark"], len(data["user_ids"])) for data in url_data.values()]
    ranked.sort(key=lambda x: (-x[1], x[0].created_at))

    return ranked[:limit]


async def get_recent_bookmarks(
    db: AsyncSession,
    visibility: VisibilityFilter,
    limit: int = 10,
) -> list[Bookmark]:
    """return the N (default 10) most recent bookmarks respecting visibility."""
    query = build_bookmarks_query(visibility)
    query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
