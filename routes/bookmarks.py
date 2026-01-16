from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from starlette.responses import Response

from core.dependencies import CsrfProtected, CurrentUser, DbSession, Templates
from models.models import Visibility
from schemas import extract_validation_error
from schemas.bookmark import BookmarkForm
from services.bookmark_service import BookmarkService

router = APIRouter(tags=["bookmarks"])


@router.get("/add", response_class=HTMLResponse)
async def add_form(request: Request, user: CurrentUser, templates: Templates) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "bookmark_form.html", {"bookmark": None, "user": user}
    )


@router.post("/bookmarks", response_model=None)
async def create_bookmark(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    templates: Templates,
    _: CsrfProtected,
    url: Annotated[str, Form(max_length=2048)],
    title: Annotated[str, Form(max_length=500)],
    description: Annotated[str, Form(max_length=5000)] = "",
    tags: Annotated[str, Form(max_length=500)] = "",
    visibility: Annotated[str, Form()] = Visibility.PUBLIC,
) -> Response:
    try:
        form = BookmarkForm(
            url=url,
            title=title,
            description=description,
            tags=tags,
            visibility=visibility,
        )
    except ValidationError as e:
        return templates.TemplateResponse(
            request,
            "bookmark_form.html",
            {
                "bookmark": None,
                "user": user,
                "error": extract_validation_error(e),
                "form_data": {
                    "url": url,
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "visibility": visibility,
                },
            },
        )

    service = BookmarkService(db)
    result = await service.create_bookmark(
        user_id=user.id,
        url=form.url,
        title=form.title,
        description=form.description,
        tags=form.tags,
        visibility=form.visibility,
    )

    if not result.ok:
        return templates.TemplateResponse(
            request,
            "bookmark_form.html",
            {
                "bookmark": None,
                "user": user,
                "error": result.error,
                "form_data": {
                    "url": url,
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "visibility": visibility,
                },
            },
        )

    return RedirectResponse(url="/my", status_code=303)


@router.get("/bookmarks/{bookmark_id}/edit", response_class=HTMLResponse)
async def edit_form(
    request: Request, bookmark_id: int, db: DbSession, user: CurrentUser, templates: Templates
) -> HTMLResponse:
    service = BookmarkService(db)
    bookmark = await service.get_bookmark(bookmark_id, user.id)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    return templates.TemplateResponse(
        request, "bookmark_form.html", {"bookmark": bookmark, "user": user}
    )


@router.post("/bookmarks/{bookmark_id}")
async def update_bookmark(
    request: Request,
    bookmark_id: int,
    db: DbSession,
    user: CurrentUser,
    templates: Templates,
    _: CsrfProtected,
    url: Annotated[str, Form(max_length=2048)],
    title: Annotated[str, Form(max_length=500)],
    description: Annotated[str, Form(max_length=5000)] = "",
    tags: Annotated[str, Form(max_length=500)] = "",
    visibility: Annotated[str, Form()] = Visibility.PUBLIC,
) -> Response:
    service = BookmarkService(db)
    bookmark = await service.get_bookmark(bookmark_id, user.id)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    try:
        form = BookmarkForm(
            url=url,
            title=title,
            description=description,
            tags=tags,
            visibility=visibility,
        )
    except ValidationError as e:
        return templates.TemplateResponse(
            request,
            "bookmark_form.html",
            {
                "bookmark": bookmark,
                "user": user,
                "error": extract_validation_error(e),
                "form_data": {
                    "url": url,
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "visibility": visibility,
                },
            },
        )

    result = await service.update_bookmark(
        bookmark=bookmark,
        url=form.url,
        title=form.title,
        description=form.description,
        tags=form.tags,
        visibility=form.visibility,
    )

    if not result.ok:
        await db.refresh(bookmark)
        return templates.TemplateResponse(
            request,
            "bookmark_form.html",
            {
                "bookmark": bookmark,
                "user": user,
                "error": result.error,
                "form_data": {
                    "url": url,
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "visibility": visibility,
                },
            },
        )

    return RedirectResponse(url="/my", status_code=303)


@router.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: int, db: DbSession, user: CurrentUser, _: CsrfProtected
) -> Response:
    service = BookmarkService(db)
    bookmark = await service.get_bookmark(bookmark_id, user.id)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await service.delete_bookmark(bookmark)
    return Response(status_code=200)


@router.post("/bookmarks/{bookmark_id}/save")
async def save_bookmark(
    request: Request,
    bookmark_id: int,
    db: DbSession,
    user: CurrentUser,
    templates: Templates,
    _: CsrfProtected,
) -> Response:
    service = BookmarkService(db)
    source = await service.get_bookmark(bookmark_id)

    if not source:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    if source.user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot save your own bookmark")

    if source.visibility == Visibility.PRIVATE:
        raise HTTPException(status_code=403, detail="Cannot save private bookmark")

    result = await service.create_bookmark(
        user_id=user.id,
        url=source.url,
        title=source.title,
        description=source.description,
        tags=source.tags,
        visibility=Visibility.PRIVATE,
    )

    ctx: dict[str, object] = {"bookmark": source, "user": user}
    if result.ok:
        ctx["just_saved"] = True
    else:
        ctx["already_saved"] = True

    return templates.TemplateResponse(request, "partials/save_button.html", ctx)
