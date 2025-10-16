from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CorsSettings(BaseModel):
    allowed_origins: List[str] = Field(default_factory=list)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    db_host: str = Field(default="px_db", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="power_exchange", alias="DB_NAME")
    db_user: str = Field(default="power_user", alias="DB_USER")
    db_password: str = Field(default="power_pass", alias="DB_PASSWORD")
    database_url_override: Optional[str] = Field(default=None, alias="DATABASE_URL")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    allowed_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"], alias="ALLOWED_ORIGINS")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors: CorsSettings = Field(default_factory=CorsSettings)

    def model_post_init(self, __context: Dict[str, Any]) -> None:
        if not self.cors.allowed_origins:
            self.cors.allowed_origins = self.allowed_origins

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return f"postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    def for_logging(self) -> Dict[str, Any]:
        data = self.model_dump()
        data.pop("db_password", None)
        data.pop("openai_api_key", None)
        data.pop("database_url_override", None)
        return data


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
