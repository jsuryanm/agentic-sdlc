from sdlc_agents.state.schemas.base import _BaseModel,_utcnow
from sdlc_agents.state.schemas.a2a import AgentName
from sdlc_agents.state.enums import Phase,Severity

from pydantic import Field
from typing import Literal,Annotated
from uuid import UUID,uuid4
from datetime import datetime 

class FeedbackEntry(_BaseModel):
    """A single piece of feedback — from a human (HITL) or from the Critic."""

    feedback_id: UUID = Field(default_factory=uuid4)
    source: AgentName  # HUMAN | CRITIC
    phase: Phase
    severity: Severity = Severity.WARNING
    message: str
    suggested_change: str | None = None
    timestamp: datetime = Field(default_factory=_utcnow)


class HITLDecision(_BaseModel):
    """Record of a human's decision at an approval gate."""

    decision_id: UUID = Field(default_factory=uuid4)
    phase: Phase
    reviewer: str  # username / email
    decision: HITLDecisionType
    feedback: str | None = None
    timestamp: datetime = Field(default_factory=_utcnow)


class CriticScore(_BaseModel):
    phase: Phase
    score: Annotated[float, Field(ge=0.0, le=10.0)]
    rationale: str
    findings: list[FeedbackEntry] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=_utcnow)