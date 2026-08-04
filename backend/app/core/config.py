"""Application settings, loaded from environment variables / .env."""

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    db_server: str = "localhost\\SQLEXPRESS"
    db_name: str = "PropertyManagerDb"
    db_user: str | None = None
    db_password: str | None = None
    db_driver: str = "ODBC Driver 17 for SQL Server"
    db_trusted_connection: bool = True

    # Application
    app_env: str = "development"
    app_debug: bool = True

    # JWT authentication
    jwt_secret_key: str = "change-me-to-a-long-random-value"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS
    cors_allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Build the SQLAlchemy connection URL for SQL Server via pyodbc.

        Uses the odbc_connect= form (a raw ODBC connection string, URL-encoded)
        rather than the plain mssql+pyodbc://host/db form, because a named
        instance like "localhost\\SQLEXPRESS" contains a backslash that is
        awkward to embed directly in a URL.
        """
        if self.db_trusted_connection:
            odbc_str = (
                f"DRIVER={{{self.db_driver}}};"
                f"SERVER={self.db_server};"
                f"DATABASE={self.db_name};"
                f"Trusted_Connection=yes;"
            )
        else:
            odbc_str = (
                f"DRIVER={{{self.db_driver}}};"
                f"SERVER={self.db_server};"
                f"DATABASE={self.db_name};"
                f"UID={self.db_user};"
                f"PWD={self.db_password};"
            )
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance - .env is only read once per process."""
    return Settings()
