from sdlc_agents.state.schemas.base import _BaseModel,_utcnow
from pydantic import Field
from typing import Literal,Annotated

class UserStory(_BaseModel):
    id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    priority: Annotated[int, Field(ge=1, le=5)] = 3


class NonFunctionalRequirement(_BaseModel):
    category: str  # "performance" | "security" | "scalability" | ...
    description: str
    target: str | None = None  # e.g. "p99 < 200ms"


class Requirements(_BaseModel):
    summary: str
    user_stories: list[UserStory]
    non_functional: list[NonFunctionalRequirement] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
