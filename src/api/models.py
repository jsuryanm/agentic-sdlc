from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RunCreate(BaseModel):
    idea: str = Field(..., min_length=1)
    thread_id: Optional[str] = Field(
        default=None,
        description='Optional thread id. If omitted, a new one is generated.',
    )


class ResumePayload(BaseModel):
    verdict: str = Field(description="'approve' or 'reject'")
    comment: str = ''


class RewindPayload(BaseModel):
    checkpoint_id: str


class CheckpointSummary(BaseModel):
    checkpoint_id: str
    node: str
    status: str
    has: Dict[str, bool]


class RunResponse(BaseModel):
    thread_id: str
    status: str
    stage: str  # 'awaiting_hitl' | 'done' | 'running' | 'error'
    pending_interrupt: Optional[Dict[str, Any]] = None
    state: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
