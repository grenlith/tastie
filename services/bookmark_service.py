from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    Cursor,
    Page,
    get_bookmark_cursor,
)
from core.result import Result
from core.search import fts5_search_ids
from models.models import Bookmark, BookmarkTag, Tag, Visibility
from queries.bookmark_queries import VisibilityFilter, build_bookmarks_query


class BookmarkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_bookmarks(
        self,
        visibility: VisibilityFilter,
        tag: str | None = None,
    ) -> Sequence[Bookmark]:
        query = build_bookmarks_query(visibility, tag)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_bookmarks_paginated(
        self,
        visibility: VisibilityFilter,
        tag: str | None = None,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> Page[Bookmark]:
        limit = min(max(1, limit), MAX_PAGE_SIZE)

        query = build_bookmarks_query(visibility, tag)

        decoded_cursor = Cursor.decode(cursor) if cursor else None
        if decoded_cursor:
            query = query.where(
                (Bookmark.created_at < decoded_cursor.created_at)
                | (
                    (Bookmark.created_at == decoded_cursor.created_at)
                    & (Bookmark.id < decoded_cursor.id)
                )
            )

        query = query.limit(limit + 1)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return Page.from_results(items, limit, get_bookmark_cursor)

    async def search_bookmarks(
        self,
        query: str,
        visibility: VisibilityFilter,
    ) -> Sequence[Bookmark]:
        matching_ids = await fts5_search_ids(self.db, "bookmarks_fts", query)

        if not matching_ids:
            return []

        bookmark_query = (
            select(Bookmark)
            .options(selectinload(Bookmark.user))
            .where(Bookmark.id.in_(matching_ids))
        )
        bookmark_query = visibility.apply(bookmark_query)

        bookmark_result = await self.db.execute(bookmark_query)
        bookmark_map = {b.id: b for b in bookmark_result.scalars().all()}
        return [bookmark_map[id] for id in matching_ids if id in bookmark_map]

    async def get_bookmark(self, bookmark_id: int, user_id: int | None = None) -> Bookmark | None:
        query = select(Bookmark).where(Bookmark.id == bookmark_id)
        if user_id is not None:
            query = query.where(Bookmark.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_bookmark(
        self,
        user_id: int,
        url: str,
        title: str,
        description: str = "",
        tags: str = "",
        visibility: str = Visibility.PUBLIC,
    ) -> Result[Bookmark]:
        if visibility not in Visibility.ALL:
            visibility = Visibility.PUBLIC

        existing = await self.db.execute(
            select(Bookmark).where(Bookmark.user_id == user_id).where(Bookmark.url == url)
        )
        if existing.scalar_one_or_none():
            return Result.conflict("you already have a bookmark for this site")

        bookmark = Bookmark(
            user_id=user_id,
            url=url,
            title=title,
            description=description,
            tags=tags.strip(),
            visibility=visibility,
        )
        self.db.add(bookmark)
        try:
            await self.db.commit()
            await self.db.refresh(bookmark)

            await self._sync_normalized_tags(bookmark.id, tags.strip())
            await self.db.commit()

            return Result.success(bookmark)
        except IntegrityError:
            await self.db.rollback()
            return Result.conflict("you already have a bookmark for this site")

    async def update_bookmark(
        self,
        bookmark: Bookmark,
        url: str,
        title: str,
        description: str = "",
        tags: str = "",
        visibility: str = Visibility.PUBLIC,
    ) -> Result[Bookmark]:
        if visibility not in Visibility.ALL:
            visibility = Visibility.PUBLIC

        bookmark.url = url
        bookmark.title = title
        bookmark.description = description
        bookmark.tags = tags.strip()
        bookmark.visibility = visibility

        await self._sync_normalized_tags(bookmark.id, tags.strip())

        await self.db.commit()
        return Result.success(bookmark)

    async def delete_bookmark(self, bookmark: Bookmark) -> None:
        await self.db.delete(bookmark)
        await self.db.commit()

    async def _sync_normalized_tags(self, bookmark_id: int, tags_str: str) -> None:
        """dual-write to both tags column and normalized Tag table."""
        tag_names = [t.strip() for t in tags_str.split() if t.strip()]

        await self.db.execute(delete(BookmarkTag).where(BookmarkTag.bookmark_id == bookmark_id))

        if not tag_names:
            return

        for tag_name in tag_names:
            stmt = (
                sqlite_insert(Tag)
                .values(name=tag_name)
                .on_conflict_do_nothing(index_elements=["name"])
            )
            await self.db.execute(stmt)

            result = await self.db.execute(select(Tag.id).where(Tag.name == tag_name))
            tag_id = result.scalar_one()

            await self.db.execute(
                sqlite_insert(BookmarkTag)
                .values(bookmark_id=bookmark_id, tag_id=tag_id)
                .on_conflict_do_nothing()
            )
