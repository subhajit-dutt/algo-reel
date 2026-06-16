from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

TTSResponseFormat = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]


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

    openai_api_key: str = Field(min_length=1)
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice_default: str = "coral"
    tts_instructions: str = "Calm tutorial voice, clear pacing, slight pause between sentences."
    tts_response_format: TTSResponseFormat = "wav"
    tts_timeout_seconds: int = Field(default=60, gt=0)
    tts_max_retries: int = Field(default=2, ge=0)
    tts_max_concurrency: int = Field(default=4, gt=0)
    media_root: str = "./.media"

    render_image: str = "algoreel-render:m4"
    render_video_size: str = "1280x720"
    render_video_fps: int = Field(default=30, gt=0)
    render_bg_color: str = "0x0B132B"
    render_memory: str = "2g"
    render_cpus: str = Field(default="1.0", min_length=1)
    render_pids_limit: int = Field(default=256, gt=0)
    render_user: str = "10001:10001"
    render_timeout_seconds: int = Field(default=120, gt=0)
    render_result_timeout_seconds: int = Field(default=900, gt=0)
    compose_result_timeout_seconds: int = Field(default=300, gt=0)

    manim_image: str = "algoreel-manim:m5"
    llm_codegen_model: str = "anthropic/claude-sonnet-4.6"
    llm_codegen_retry_model: str = "anthropic/claude-opus-4.8"
    llm_critic_model: str = "anthropic/claude-haiku-4.5"
    llm_codegen_max_tokens: int = Field(default=8000, gt=0)
    manim_max_attempts: int = Field(default=3, gt=0)
    manim_render_timeout_seconds: int = Field(default=300, gt=0)
    manim_tmpfs_size: str = "512m"
    max_render_cost_usd: Decimal = Field(default=Decimal("1.50"), gt=Decimal(0))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
