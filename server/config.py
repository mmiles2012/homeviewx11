"""HomeView server configuration using pydantic-settings."""

import os
from pathlib import Path
from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server configuration — reads from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_prefix="HOMEVIEW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Network
    host: str = "0.0.0.0"
    port: int = 8000

    # Server identity
    server_name: str = os.uname().nodename

    # Runtime mode — accepts HOMEVIEW_MOCK=1 or HOMEVIEW_MOCK_MODE=true
    mock_mode: bool = Field(
        default=False,
        validation_alias=AliasChoices("HOMEVIEW_MOCK", "HOMEVIEW_MOCK_MODE"),
    )

    # Storage paths
    db_path: str = str(Path.home() / ".homeview" / "homeview.db")
    profiles_dir: str = str(Path.home() / ".homeview" / "profiles")
    layouts_dir: str = str(Path(__file__).parent.parent / "layouts")

    # Chromium
    chromium_binary: str = "chromium-browser"

    # X11 display
    display: str = ":0"

    @field_validator("mock_mode", mode="before")
    @classmethod
    def parse_bool_env(cls, v: Any) -> Any:
        """Accept '1'/'0' in addition to pydantic-settings default 'true'/'false'."""
        if isinstance(v, str):
            if v.strip() == "1":
                return True
            if v.strip() == "0":
                return False
        return v

    # Mock mode display resolution (used when mock_mode=True)
    mock_display_width: int = 1920
    mock_display_height: int = 1080


@lru_cache(maxsize=1)
def get_config() -> Settings:
    """Return the cached settings instance."""
    return Settings()
