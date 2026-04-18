from sdlc_agents.state.schemas.base import _BaseModel,_utcnow
from datetime import datetime 
from pydantic import BaseModel, ConfigDict, Field, HttpUrl



class DeploymentStatus(_BaseModel):
    environment: str  # "dev" | "staging" | "prod"
    deployed_at: datetime | None = None
    health_check_url: HttpUrl | None = None
    healthy: bool | None = None
    rollback_sha: str | None = None