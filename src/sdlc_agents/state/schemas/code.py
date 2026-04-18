from sdlc_agents.state.schemas.base import _BaseModel
from pydantic import Field,HttpUrl


class CodebaseRef(_BaseModel):
    """Reference to the produced codebase. Never stores file contents."""

    repo_url: HttpUrl
    default_branch: str = "main"
    feature_branch: str
    head_commit_sha: str
    pr_number: int | None = None
    pr_url: HttpUrl | None = None
    files_written: list[str] = Field(default_factory=list)