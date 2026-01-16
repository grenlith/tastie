from core.auth import (
    clear_session_cookie,
    create_session_token,
    hash_password,
    set_session_cookie,
    verify_password,
    verify_session_token,
)
from core.csrf import generate_csrf_token, get_csrf_token, validate_csrf, verify_csrf_token
from core.database import async_session, db_session, engine, get_session
from core.dependencies import (
    CsrfProtected,
    CurrentUser,
    CurrentUserOptional,
    DbSession,
    Templates,
    get_client_ip,
    get_current_user,
    get_current_user_optional,
    get_db_session,
    get_limiter,
    get_templates,
)
from core.logging import get_logger, request_id_var, setup_logging
from core.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from core.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    Cursor,
    Page,
    get_bookmark_cursor,
)
from core.result import ErrorKind, Result
from core.search import escape_fts5_query, fts5_search_ids

__all__ = [
    # auth
    "hash_password",
    "verify_password",
    "create_session_token",
    "verify_session_token",
    "set_session_cookie",
    "clear_session_cookie",
    # csrf
    "generate_csrf_token",
    "verify_csrf_token",
    "validate_csrf",
    "get_csrf_token",
    # database
    "engine",
    "async_session",
    "get_session",
    "db_session",
    # dependencies
    "get_db_session",
    "DbSession",
    "get_current_user_optional",
    "get_current_user",
    "CurrentUser",
    "CurrentUserOptional",
    "CsrfProtected",
    "get_client_ip",
    "get_limiter",
    "get_templates",
    "Templates",
    # logging
    "setup_logging",
    "get_logger",
    "request_id_var",
    # middleware
    "RequestIDMiddleware",
    "SecurityHeadersMiddleware",
    # result
    "Result",
    # errors
    "ErrorKind",
    # search
    "escape_fts5_query",
    "fts5_search_ids",
    # pagination
    "Cursor",
    "Page",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "get_bookmark_cursor",
]
