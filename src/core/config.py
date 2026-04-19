from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    # LLM
    OPENAI_API_KEY: str = Field(default="")
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_TEMPERATURE: float = Field(default=0.2, ge=0, le=1)
    LLM_MAX_TOKENS: int = Field(default=2000)

    # GitHub MCP
    GITHUB_PERSONAL_ACCESS_TOKEN: str = Field(default="")
    GITHUB_REPO_OWNER: str = Field(default="")
    GITHUB_REPO_NAME: str = Field(default="")
    GITHUB_MCP_URL: str = Field(default="https://api.githubcopilot.com/mcp/")

    # QA loop
    MAX_QA_RETRIES: int = 2

    # Paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
    WORKSPACE_DIR: Path = PROJECT_ROOT / "workspace"
    LOG_DIR: Path = PROJECT_ROOT / "logs"
    CHECKPOINT_DIR: Path = PROJECT_ROOT / ".checkpoints"

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Config()
settings.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
settings.CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)