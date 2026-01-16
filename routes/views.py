import html
from dataclasses import dataclass
from datetime import UTC
from html.parser import HTMLParser
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.responses import Response

from core.dependencies import CsrfProtected, CurrentUser, CurrentUserOptional, DbSession, Templates
from models.models import User, Visibility
from queries.bookmark_queries import (
    VisibilityFilter,
    build_bookmarks_query,
    get_all_tags,
    get_popular_bookmarks_for_tag,
    get_recent_bookmarks,
    get_top_tags,
)
from schemas.bookmark import ALLOWED_URL_SCHEMES
from services.auth_service import AuthService
from services.bookmark_service import BookmarkService


async def get_saved_urls(service: BookmarkService, user: User | None) -> set[str]:
    if not user:
        return set()
    bookmarks = await service.list_bookmarks(VisibilityFilter.for_owner(user.id))
    return {b.url for b in bookmarks}


router = APIRouter(tags=["views"])


@dataclass(frozen=True, slots=True)
class ParsedBookmark:
    url: str
    title: str
    description: str
    tags: str


class NetscapeBookmarkParser(HTMLParser):
    """parses netscape bookmark html format."""

    def __init__(self) -> None:
        super().__init__()
        self.bookmarks: list[ParsedBookmark] = []
        self.folder_stack: list[str] = []
        self._current_url: str | None = None
        self._current_tags: str | None = None
        self._current_title: str = ""
        self._in_anchor = False
        self._in_folder_title = False
        self._expect_description = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k.lower(): v for k, v in attrs}
        if tag == "a" and "href" in attr_dict:
            self._current_url = attr_dict.get("href")
            self._current_tags = attr_dict.get("tags")
            self._current_title = ""
            self._in_anchor = True
        elif tag == "h3":
            self._in_folder_title = True
            self._current_title = ""
        elif tag == "dd":
            self._expect_description = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_anchor:
            self._in_anchor = False
            if self._current_url:
                if self._current_tags:
                    tags = self._current_tags.replace(",", " ")
                elif self.folder_stack:
                    tags = " ".join(self.folder_stack)
                else:
                    tags = ""
                self.bookmarks.append(
                    ParsedBookmark(
                        url=self._current_url,
                        title=self._current_title.strip(),
                        description="",
                        tags=tags,
                    )
                )
            self._current_url = None
            self._current_tags = None
        elif tag == "h3" and self._in_folder_title:
            self._in_folder_title = False
            folder_name = self._current_title.strip()
            if folder_name and folder_name.lower() not in (
                "bookmarks",
                "bookmarks bar",
                "other bookmarks",
                "bookmarks menu",
            ):
                self.folder_stack.append(folder_name)
        elif tag == "dl" and self.folder_stack:
            self.folder_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._in_anchor or self._in_folder_title:
            self._current_title += data
        elif self._expect_description and self.bookmarks:
            last = self.bookmarks[-1]
            self.bookmarks[-1] = ParsedBookmark(
                url=last.url,
                title=last.title,
                description=data.strip(),
                tags=last.tags,
            )
            self._expect_description = False


def generate_netscape_export(bookmarks: list[tuple[str, str, str, str, int]]) -> str:
    """generate netscape bookmark html from bookmark data"""
    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
        "<DL><p>",
    ]
    for url, title, description, tags, timestamp in bookmarks:
        escaped_title = html.escape(title)
        escaped_url = html.escape(url)
        tag_attr = f' TAGS="{html.escape(tags)}"' if tags else ""
        lines.append(
            f'    <DT><A HREF="{escaped_url}" ADD_DATE="{timestamp}"{tag_attr}>{escaped_title}</A>'
        )
        if description:
            lines.append(f"    <DD>{html.escape(description)}")
    lines.append("</DL><p>")
    return "\n".join(lines)


@dataclass
class ProfilePlaceholder:
    username: str


@router.get("/about", response_class=HTMLResponse)
async def about(
    request: Request,
    templates: Templates,
    user: CurrentUserOptional,
) -> HTMLResponse:
    return templates.TemplateResponse(request, "about.html", {"user": user})


@router.get("/privacy", response_class=HTMLResponse)
async def privacy(
    request: Request,
    templates: Templates,
    user: CurrentUserOptional,
) -> HTMLResponse:
    return templates.TemplateResponse(request, "privacy.html", {"user": user})


@router.get("/", response_class=HTMLResponse)
async def show_public_feed(
    request: Request,
    db: DbSession,
    user: CurrentUserOptional,
    templates: Templates,
    tag: str | None = None,
) -> HTMLResponse:
    service = BookmarkService(db)
    visibility = VisibilityFilter.for_user(user)
    saved_urls = await get_saved_urls(service, user)

    if tag:
        bookmarks = await service.list_bookmarks(visibility, tag)
        all_tags = await get_all_tags(db, visibility)

        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "bookmarks": bookmarks,
                "all_tags": all_tags,
                "current_tag": tag,
                "user": user,
                "show_authors": True,
                "saved_urls": saved_urls,
            },
        )

    top_tags = await get_top_tags(db, visibility, limit=5)
    top_tags_with_bookmarks = []
    for tag_name, tag_count in top_tags:
        popular_bookmarks = await get_popular_bookmarks_for_tag(db, tag_name, visibility, limit=3)
        top_tags_with_bookmarks.append(
            {
                "tag": tag_name,
                "count": tag_count,
                "bookmarks": popular_bookmarks,
            }
        )

    recent_bookmarks = await get_recent_bookmarks(db, visibility, limit=10)

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "top_tags_with_bookmarks": top_tags_with_bookmarks,
            "recent_bookmarks": recent_bookmarks,
            "user": user,
            "show_authors": True,
            "saved_urls": saved_urls,
        },
    )


@router.get("/my", response_class=HTMLResponse)
async def show_my_bookmarks(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    templates: Templates,
    tag: str | None = None,
    imported: int | None = None,
) -> HTMLResponse:
    service = BookmarkService(db)
    visibility = VisibilityFilter.for_owner(user.id)
    bookmarks = await service.list_bookmarks(visibility, tag)
    all_tags = await get_all_tags(db, visibility)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "bookmarks": bookmarks,
            "all_tags": all_tags,
            "current_tag": tag,
            "user": user,
            "my_bookmarks": True,
            "imported_count": imported,
        },
    )


@router.get("/my/export")
async def export_bookmarks(
    db: DbSession,
    user: CurrentUser,
) -> Response:
    service = BookmarkService(db)
    bookmarks = await service.list_bookmarks(VisibilityFilter.for_owner(user.id))

    export_data: list[tuple[str, str, str, str, int]] = [
        (
            b.url,
            b.title,
            b.description,
            b.tags,
            int(b.created_at.replace(tzinfo=UTC).timestamp()),
        )
        for b in bookmarks
    ]

    content = generate_netscape_export(export_data)
    return Response(
        content=content,
        media_type="text/html",
        headers={"Content-Disposition": 'attachment; filename="bookmarks.html"'},
    )


@router.post("/my/import")
async def import_bookmarks(
    db: DbSession,
    user: CurrentUser,
    file: UploadFile,
    _: CsrfProtected,
) -> RedirectResponse:
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    parser = NetscapeBookmarkParser()
    parser.feed(text)

    service = BookmarkService(db)
    imported_count = 0

    for bookmark in parser.bookmarks:
        parsed_url = urlparse(bookmark.url)
        if parsed_url.scheme.lower() not in ALLOWED_URL_SCHEMES:
            continue

        result = await service.create_bookmark(
            user_id=user.id,
            url=bookmark.url,
            title=bookmark.title or bookmark.url,
            description=bookmark.description,
            tags=bookmark.tags,
            visibility=Visibility.PRIVATE,
        )
        if result.ok:
            imported_count += 1

    return RedirectResponse(url=f"/my?imported={imported_count}", status_code=303)


@router.get("/users/{username}", response_class=HTMLResponse)
async def show_user_profile(
    request: Request,
    db: DbSession,
    user: CurrentUserOptional,
    templates: Templates,
    username: str,
    tag: str | None = None,
) -> Response:
    auth_service = AuthService(db)
    profile_user = await auth_service.get_user_by_username(username)

    if not profile_user:
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "bookmarks": [],
                "all_tags": [],
                "current_tag": tag,
                "user": user,
                "profile_user": ProfilePlaceholder(username=username),
                "my_bookmarks": False,
                "show_authors": False,
            },
        )

    service = BookmarkService(db)
    saved_urls = await get_saved_urls(service, user)

    viewer_id = user.id if user else None
    visibility = VisibilityFilter.for_profile(profile_user.id, viewer_id)

    result = await db.execute(build_bookmarks_query(visibility, tag))
    bookmarks = result.scalars().all()
    all_tags = await get_all_tags(db, visibility)

    is_own_profile = user and user.id == profile_user.id

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "bookmarks": bookmarks,
            "all_tags": all_tags,
            "current_tag": tag,
            "user": user,
            "profile_user": profile_user,
            "my_bookmarks": is_own_profile,
            "show_authors": False,
            "saved_urls": saved_urls,
        },
    )


@router.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    db: DbSession,
    user: CurrentUserOptional,
    templates: Templates,
    q: Annotated[str, Query()] = "",
) -> Response:
    if not q:
        return RedirectResponse(url="/", status_code=302)

    service = BookmarkService(db)
    visibility = VisibilityFilter.for_user(user)
    saved_urls = await get_saved_urls(service, user)
    bookmarks = await service.search_bookmarks(q, visibility)
    all_tags = await get_all_tags(db, visibility)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "bookmarks": bookmarks,
            "all_tags": all_tags,
            "search_query": q,
            "user": user,
            "show_authors": True,
            "saved_urls": saved_urls,
        },
    )


@router.get("/my/search", response_class=HTMLResponse)
async def search_my_bookmarks(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    templates: Templates,
    q: Annotated[str, Query()] = "",
) -> Response:
    if not q:
        return RedirectResponse(url="/my", status_code=302)

    service = BookmarkService(db)
    visibility = VisibilityFilter.for_owner(user.id)
    bookmarks = await service.search_bookmarks(q, visibility)
    all_tags = await get_all_tags(db, visibility)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "bookmarks": bookmarks,
            "all_tags": all_tags,
            "search_query": q,
            "user": user,
            "my_bookmarks": True,
        },
    )
