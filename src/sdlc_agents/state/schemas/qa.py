from sdlc_agents.state.schemas.base import _BaseModel,_utcnow
from sdlc_agents.state.schemas.a2a import AgentName
from sdlc_agents.state.enums import Phase,Severity

from pydantic import Field
from typing import Literal,Annotated
from uuid import UUID,uuid4
from datetime import datetime 

class TestCase(_BaseModel):
    name: str
    file_path: str
    kind: str  # "unit" | "integration" | "e2e"


class TestSuite(_BaseModel):
    test_cases: list[TestCase]
    framework: str = "pytest"
    coverage_target: float = 0.8


class TestFailure(_BaseModel):
    test_name: str
    message: str
    traceback: str | None = None
    file_path: str | None = None


class TestResults(_BaseModel):
    status: str  # "pass" | "fail" | "error"
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    coverage_pct: float | None = None
    failures: list[TestFailure] = Field(default_factory=list)
    run_url: HttpUrl | None = None  # link to GitHub Actions run, etc.