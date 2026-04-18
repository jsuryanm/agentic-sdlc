from sdlc_agents.state.schemas.base import _BaseModel
from pydantic import Field 

class LibraryRef(_BaseModel):
    """Pinned library selected by the Architect; filters lib_docs retrieval."""

    name: str
    version: str
    language: str = "python"
    purpose: str | None = None

