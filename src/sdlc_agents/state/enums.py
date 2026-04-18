from __future__ import annotations 
from enum import StrEnum 
# same as enum where all the members are strings

class Phase(StrEnum):
    """SDLC phases, in chronological order."""
    INIT = "init"
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    DEVELOPMENT = "development"
    QA = "qa"
    DEVOPS = "devops"
    DEPLOYED = "deployed"


class WorkflowStatus(StrEnum):
    """Top-level workflow status."""
    PENDING = "pending"
    RUNNING = "design"
    WAITING_FOR_HUMAN = "waiting_for_human"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class AgentName(StrEnum):
    """Names used in A2A messages and tool registry."""
    REQUIREMENT = "requirement"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    QA = "qa"
    DEVOPS = "devops"
    CRITIC = "critic"
    HUMAN = "human"
    SYSTEM = "system"

class HITLDecisionType(StrEnum):
    """Human decisions at an approval gate."""
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"

class Severity(StrEnum):
    """Severity levels for feedback and critic findings."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
