from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from core.csrf import get_csrf_token
from core.database import engine
from core.dependencies import get_limiter
from core.logging import setup_logging
from core.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from models.models import Base
from routes import auth, bookmarks, partials, views

settings.validate()
setup_logging(settings.LOG_FILE, settings.LOG_LEVEL, settings.JSON_LOGS)

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="tastie", lifespan=lifespan)

# template context processors
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.context_processors.append(lambda request: {"csrf_token": get_csrf_token(request)})
templates.context_processors.append(lambda request: {"now": datetime.now(UTC)})
templates.context_processors.append(lambda request: {"site_name": settings.SITE_NAME})
app.state.templates = templates

limiter = get_limiter()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# middleware order: first added = last executed
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)

if settings.TRUST_PROXY:
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/favicon.ico")
async def favicon() -> RedirectResponse:
    return RedirectResponse(url="/static/logo.png")


@app.get("/apple-touch-icon.png")
async def apple_touch_icon() -> RedirectResponse:
    return RedirectResponse(url="/static/icon-100.png")


@app.get("/apple-touch-icon-precomposed.png")
async def apple_touch_icon_precomposed() -> RedirectResponse:
    return RedirectResponse(url="/static/icon-100.png")


@app.get("/manifest.json")
async def manifest() -> dict[str, object]:
    return {
        "name": settings.SITE_NAME,
        "short_name": settings.SITE_NAME,
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#333333",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }


app.include_router(auth.router)
app.include_router(bookmarks.router)
app.include_router(views.router)
app.include_router(partials.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_excludes=["*.log"])
