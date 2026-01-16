from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from core.dependencies import CurrentUser, CurrentUserOptional, DbSession, Templates
from core.pagination import DEFAULT_PAGE_SIZE
from queries.bookmark_queries import VisibilityFilter, get_all_tags
from services.bookmark_service import BookmarkService

router = APIRouter(tags=["partials"])


@router.get("/tags", response_class=HTMLResponse)
async def get_public_tags(
    request: Request, db: DbSession, user: CurrentUserOptional, templates: Templates
) -> HTMLResponse:
    all_tags = await get_all_tags(db, VisibilityFilter.for_user(user))
    return templates.TemplateResponse(
        request, "partials/tags.html", {"all_tags": all_tags, "user": user}
    )


@router.get("/my/tags", response_class=HTMLResponse)
async def get_my_tags(
    request: Request, db: DbSession, user: CurrentUser, templates: Templates
) -> HTMLResponse:
    all_tags = await get_all_tags(db, VisibilityFilter.for_owner(user.id))
    return templates.TemplateResponse(
        request, "partials/tags.html", {"all_tags": all_tags, "user": user, "my_bookmarks": True}
    )


@router.get("/bookmarks", response_class=HTMLResponse)
async def get_public_bookmarks(
    request: Request,
    db: DbSession,
    user: CurrentUserOptional,
    templates: Templates,
    tag: str | None = None,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=100),
) -> HTMLResponse:
    service = BookmarkService(db)
    page = await service.list_bookmarks_paginated(
        VisibilityFilter.for_user(user), tag, cursor, limit
    )

    return templates.TemplateResponse(
        request,
        "partials/bookmark_list.html",
        {
            "bookmarks": page.items,
            "user": user,
            "show_authors": True,
            "next_cursor": page.next_cursor,
            "has_more": page.has_more,
            "current_tag": tag,
        },
    )


@router.get("/my/bookmarks", response_class=HTMLResponse)
async def get_my_bookmarks(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    templates: Templates,
    tag: str | None = None,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=100),
) -> HTMLResponse:
    service = BookmarkService(db)
    page = await service.list_bookmarks_paginated(
        VisibilityFilter.for_owner(user.id), tag, cursor, limit
    )

    return templates.TemplateResponse(
        request,
        "partials/bookmark_list.html",
        {
            "bookmarks": page.items,
            "user": user,
            "my_bookmarks": True,
            "next_cursor": page.next_cursor,
            "has_more": page.has_more,
            "current_tag": tag,
        },
    )
