from pydantic_settings import BaseSettings
from pydantic import Field, AliasChoices
from typing import Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def _strip_sslmode(url: str) -> str:
    """asyncpg 'sslmode' so'rov parametrini tushunmaydi (faqat psycopg2 tushunadi).
    Render/Heroku kabi provayderlar odatda '?sslmode=require' qo'shib beradi —
    buni asyncpg uchun to'g'ri 'ssl=true' ga aylantiramiz."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    sslmode = query.pop("sslmode", None)
    if sslmode and sslmode != "disable":
        query["ssl"] = "true"
    new_query = urlencode(query)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


class Settings(BaseSettings):
    postgres_host: str = Field("localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(5432, env="POSTGRES_PORT")
    postgres_db: str = Field("pharmbaseuz", env="POSTGRES_DB")
    postgres_user: str = Field("pharmuser", env="POSTGRES_USER")
    postgres_password: str = Field("strongpassword123", env="POSTGRES_PASSWORD")

    use_sqlite: bool = Field(True, env="USE_SQLITE")
    sqlite_path: str = Field("pharmbaseuz.db", env="SQLITE_PATH")

    redis_host: str = Field("localhost", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")
    redis_db: int = Field(0, env="REDIS_DB")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")

    admin_ids: str = Field("", env="ADMIN_IDS")
    admin_password: str = Field("admin123", env="ADMIN_PASSWORD")
    admin_password_hash: Optional[str] = Field(None, env="ADMIN_PASSWORD_HASH")
    admin_username: str = Field("admin", env="ADMIN_USERNAME")
    site_secret_key: str = Field(default_factory=lambda: __import__("os").environ.get("SESSION_SECRET", "o'zgartiring-maxfiy-kalit-123"), env="SITE_SECRET_KEY")
    site_name: str = Field("PharmBaseUZ", env="SITE_NAME")
    site_background_url: str = Field("", env="SITE_BACKGROUND_URL")
    site_animation_style: str = Field("pills", env="SITE_ANIMATION_STYLE")
    site_animation_image_url: str = Field("", env="SITE_ANIMATION_IMAGE_URL")

    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    timezone: str = Field("Asia/Tashkent", env="TIMEZONE")

    rate_limit_requests: int = Field(30, env="RATE_LIMIT_REQUESTS")
    rate_limit_minutes: int = Field(1, env="RATE_LIMIT_MINUTES")

    # Render.com to'g'ridan-to'g'ri DATABASE_URL beradi (postgres:// formatida)
    database_url_override: Optional[str] = Field(
        None, validation_alias=AliasChoices("DATABASE_URL", "database_url_override")
    )

    @property
    def database_url(self) -> str:
        # Render bergan DATABASE_URL ni ustuvor ishlatamiz
        if self.database_url_override:
            url = self.database_url_override
            # Render "postgres://" beradi, SQLAlchemy "postgresql+asyncpg://" talab qiladi
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return _strip_sslmode(url)
        if self.use_sqlite:
            return f"sqlite+aiosqlite:///{self.sqlite_path}"
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        if self.database_url_override:
            url = self.database_url_override
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
            return url
        if self.use_sqlite:
            return f"sqlite:///{self.sqlite_path}"
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def admin_id_list(self) -> list[int]:
        if not self.admin_ids:
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
