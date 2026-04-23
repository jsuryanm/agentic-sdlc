class SDLCBaseException(Exception):
    """Root exception for the Agentic SDLC system."""


# --- Agent layer ---
class AgentException(SDLCBaseException):
    """Raised when an agent fails to produce a valid output."""


class RequirementAgentException(AgentException): pass
class ArchitectAgentException(AgentException): pass
class DeveloperAgentException(AgentException): pass
class QAAgentException(AgentException): pass
class DevOpsAgentException(AgentException): pass


# --- Tool layer ---
class ToolException(SDLCBaseException):
    """Raised when a tool fails to execute."""


class LLMToolException(ToolException): pass
class MCPToolException(ToolException): pass
class TestRunnerException(ToolException): pass


# --- Pipeline layer ---
class PipelineException(SDLCBaseException):
    """Raised when the LangGraph pipeline itself fails."""


class HITLRejectedException(PipelineException):
    """Raised when the human rejects an agent's output (terminal)."""


class QALoopExceededException(PipelineException):
    """Raised when the QA retry budget is exhausted."""