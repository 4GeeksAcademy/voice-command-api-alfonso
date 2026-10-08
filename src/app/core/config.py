import os
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _default_allowed_origins() -> list[str]:
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    codespace_name = os.environ.get("CODESPACE_NAME")
    forwarding_domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")
    if codespace_name and forwarding_domain:
        origins.append(f"https://{codespace_name}-5173.{forwarding_domain}")
    return origins


class Settings(BaseSettings):
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-20b"
    groq_transcription_model: str = "whisper-large-v3-turbo"
    request_timeout_seconds: float = 45.0
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=_default_allowed_origins
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
