from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "ci", "prod"] = "local"
    app_shared_secret: str = Field(min_length=8)
    database_url: str
    redis_url: str
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    openrouter_api_key: str = Field(min_length=1)
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_script_model: str = "anthropic/claude-haiku-4.5"
    llm_script_max_tokens: int = Field(default=4000, gt=0)
    llm_timeout_seconds: int = Field(default=60, gt=0)
    max_script_cost_usd: Decimal = Field(default=Decimal("0.10"), gt=Decimal(0))
    max_scenes_per_video: int = Field(default=12, gt=0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
