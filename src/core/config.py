from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    # LLM
    OPENAI_API_KEY: str = Field(default="")
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_TEMPERATURE: float = Field(default=0.2, ge=0, le=1)
    LLM_MAX_TOKENS: int = Field(default=2000)
    OPENAI_EMBEDDINGS_MODEL: str = Field(default="text-embedding-3-small")

    # GitHub MCP
    GITHUB_PERSONAL_ACCESS_TOKEN: str = Field(default="")
    GITHUB_REPO_OWNER: str = Field(default="")
    GITHUB_REPO_NAME: str = Field(default="")
    GITHUB_MCP_URL: str = Field(default="https://api.githubcopilot.com/mcp/")

    # QA loop
    MAX_QA_RETRIES: int = 2

    # Code review loop
    MAX_REVIEW_RETRIES: int = 2

    # Context7 MCP — doc source for code generation + review
    USE_CONTEXT7: bool = True
    CONTEXT7_MCP_COMMAND: str = "npx"
    CONTEXT7_MCP_ARGS: list[str] = Field(
        default_factory=lambda: ["-y", "@upstash/context7-mcp"]
    )
    CONTEXT7_API_KEY: Optional[str] = None
    CONTEXT7_DOC_TOKENS: int = 4000

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_BASE_URL: str = "http://localhost:8000"
    STREAMLIT_ORIGIN: str = "http://localhost:8501"

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
