from datetime import datetime 
from typing import Annotated,Any,TypedDict
from uuid import UUID,uuid4

from pydantic import BaseModel,ConfigDict,Field,HttpUrl
from typing_extensions import NotRequired
from sdlc_agents.state.enums import (AgentName,
                                     HITLDecisionType,
                                     Phase,
                                     Severity,
                                     WorkflowStatus)

from sdlc_agents.state.schemas.base import _BaseModel,_utcnow


class A2AMessage(_BaseModel):
    """Inter-agent message envelope.

    Rules:
    - ``context_summary`` is ≤300 tokens, LLM-summarized before send
    - ``artifacts`` contains REFERENCES (URLs, IDs), never raw blobs
    - ``memory_refs`` are pointers into the retrieval store or artifact store
    """
    message_id: UUID = Field(default_factory=uuid4) # default_factory is callable function 
    trace_id: UUID 
    from_agent: AgentName
    to_agent: AgentName
    task: str = Field(..., description="Short imperative task label, e.g. 'design_system'")
    context_summary: str = Field(..., max_length=2400)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    instructions: str = ""
    memory_refs: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=_utcnow)
