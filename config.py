import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    BASE_DIR: Path = Path(__file__).parent
    DATABASE_PATH: Path
    DATABASE_URL: str

    SECRET_KEY: str
    SESSION_EXPIRY_SECONDS: int = 7 * 24 * 60 * 60  # one week
    COOKIE_NAME: str = "tastie_session"

    CSRF_TOKEN_EXPIRY: int = 3600
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    CSRF_FORM_FIELD: str = "csrf_token"

    ENVIRONMENT: str
    IS_PRODUCTION: bool

    # only enable behind trusted reverse proxy - trusts X-Forwarded-* headers
    TRUST_PROXY: bool

    REQUIRE_INVITE_CODE: bool
    MIN_PASSWORD_LENGTH: int = 12

    # slowapi uses this format, certainly makes things easier
    RATE_LIMIT_REGISTER: str = "5/hour"
    RATE_LIMIT_LOGIN: str = "10/minute"

    SITE_NAME: str

    LOG_FILE: str
    LOG_LEVEL: str
    JSON_LOGS: bool

    def __init__(self) -> None:
        self.SECRET_KEY = os.environ.get("TASTIE_SECRET_KEY", "")
        self.ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
        self.IS_PRODUCTION = self.ENVIRONMENT == "production"
        self.REQUIRE_INVITE_CODE = os.environ.get("TASTIE_REQUIRE_INVITE_CODE", "").lower() in (
            "true",
            "1",
            "yes",
        )
        self.TRUST_PROXY = os.environ.get("TASTIE_TRUST_PROXY", "").lower() in (
            "true",
            "1",
            "yes",
        )
        self.SITE_NAME = os.environ.get("TASTIE_SITE_NAME", "tast.ie")
        self.LOG_FILE = os.environ.get("TASTIE_LOG_FILE", "")
        self.LOG_LEVEL = os.environ.get("TASTIE_LOG_LEVEL", "INFO")

        json_logs_env = os.environ.get("TASTIE_JSON_LOGS", "")
        if json_logs_env:
            self.JSON_LOGS = json_logs_env.lower() in ("true", "1", "yes")
        else:
            self.JSON_LOGS = self.IS_PRODUCTION

        db_path_str = os.environ.get("TASTIE_DATABASE_PATH", "")
        if db_path_str:
            self.DATABASE_PATH = Path(db_path_str)
        else:
            self.DATABASE_PATH = self.BASE_DIR / "tastie.db"

        self.DATABASE_URL = f"sqlite+aiosqlite:///{self.DATABASE_PATH}"

    def validate(self) -> None:
        if not self.SECRET_KEY:
            if self.IS_PRODUCTION:
                raise ValueError("TASTIE_SECRET_KEY must be set in production")
            self.SECRET_KEY = "dev-secret-key-change-in-production"
            print("WARNING: using default SECRET_KEY", file=sys.stderr)


settings = Settings()
