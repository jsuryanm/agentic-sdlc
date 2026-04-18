from sdlc_agents.state.schemas.base import _BaseModel,_utcnow
from sdlc_agents.state.enums import AgentName
from pydantic import Field
from uuid import UUID 
from datetime import datetime 


class RetrievedChunkRef(_BaseModel):
    """A reference to a retrieved chunk — IDs + score only, no content."""

    chunk_id: str
    corpus: str
    score: float
    rerank_score: float | None = None


class RetrievalTrace(_BaseModel):
    """Log entry for every retrieval call. Feeds the evaluation harness."""

    trace_id: UUID
    agent: AgentName
    corpus: str
    query: str
    chunks: list[RetrievedChunkRef]
    latency_ms: float
    timestamp: datetime = Field(default_factory=_utcnow)