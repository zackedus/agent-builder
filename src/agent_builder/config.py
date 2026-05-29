"""Application settings loaded from environment / .env file."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    ollama_host: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_HOST")
    ollama_model_coder: str = Field(
        default="qwen2.5-coder:14b",
        validation_alias="OLLAMA_MODEL_CODER",
    )
    ollama_model_embed: str = Field(
        default="nomic-embed-text",
        validation_alias="OLLAMA_MODEL_EMBED",
    )
    claude_model_opus: str = Field(
        default="claude-opus-4-20250514",
        validation_alias="CLAUDE_MODEL_OPUS",
    )
    claude_model_sonnet: str = Field(
        default="claude-sonnet-4-20250514",
        validation_alias="CLAUDE_MODEL_SONNET",
    )
    workspace_dir: Path = Field(
        default=Path("./workspace"),
        validation_alias="AGENT_BUILDER_WORKSPACE",
    )
    budget_usd: float | None = Field(default=None, validation_alias="AGENT_BUILDER_BUDGET_USD")
    log_level: str = Field(default="INFO", validation_alias="AGENT_BUILDER_LOG_LEVEL")
    run_integration_tests: bool = Field(
        default=False,
        validation_alias="AGENT_BUILDER_RUN_INTEGRATION_TESTS",
    )
    sandbox_layer: Literal["subprocess", "docker", "auto"] = Field(
        default="auto",
        validation_alias="AGENT_BUILDER_SANDBOX_LAYER",
    )
    coder_use_index: bool = Field(
        default=True,
        validation_alias="AGENT_BUILDER_CODER_USE_INDEX",
    )

    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_api_key and self.anthropic_api_key.strip())


def get_settings() -> Settings:
    return Settings()
