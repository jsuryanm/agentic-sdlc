from __future__ import annotations

from functools import lru_cache
from typing import Literal 
from pydantic import Field,SecretStr
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env",
                                      env_file_encoding="utf-8",
                                      extra="ignore",
                                      case_sensitive=False)
    # environment metadata
    env: Literal["dev","staging","prod"] = Field("dev",alias="SDLC_ENV")

    log_level: Literal["DEBUG","INFO","WARNING","ERROR"] = Field("INFO",
                                                                 alias="SDLC_LOG_LEVEL")
    
    # llm 
    # SecretStr is used to store the sensitive info
    openai_api_key: SecretStr | None = Field(None,alias="OPENAI_API_KEY")
    default_model: str = Field("gpt-5-nano",alias="SDLC_DEFAULT_MODEL")
    default_model: str = Field("gpt-4o-mini",alias="SDLC_CHEAP_MODEL")

    # embeddings/reranker 
    # ... field requires to be assigned the value
    voyageai_api_key: SecretStr = Field(...,alias="VOYAGEAI_API_KEY")
    cohere_api_key: SecretStr = Field(...,alias="COHERE_API_KEY")

    qdrant_url: str = Field("http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: SecretStr | None = Field(None,alias="QDRANT_API_KEY")
    
    postgres_url: str = Field("postgresql://sdlc:sdlc@localhost:5432/sdlc_agents",alias="POSTGRE_URL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    checkpointer: Literal["sqlite","postgres"] = Field("sqlite",alias="SDLC_CHECKPOINTER")
    
    # Retrieval tuning 
    retrieval_top_k: int = Field(5,alias="RETRIEVAL_TOP_K",ge=1,le=50)
    retrieval_initial_k: int = Field(20, alias="RETRIEVAL_INITIAL_K", ge=5, le=200)
    retrieval_max_context_tokens: int = Field(
        4000, alias="RETRIEVAL_MAX_CONTEXT_TOKENS", ge=500, le=32000
    )
    retrieval_cache_ttl_seconds: int = Field(
        3600, alias="RETRIEVAL_CACHE_TTL_SECONDS", ge=0
    )


    mcp_github_token: SecretStr | None = Field(None, alias="MCP_GITHUB_TOKEN")
    mcp_filesystem_token: SecretStr | None = Field(None, alias="MCP_FILESYSTEM_TOKEN")
    mcp_code_exec_token: SecretStr | None = Field(None, alias="MCP_CODE_EXEC_TOKEN")
    mcp_deploy_token: SecretStr | None = Field(None, alias="MCP_DEPLOY_TOKEN")

