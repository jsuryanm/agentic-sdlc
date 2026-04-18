from sdlc_agents.state.schemas.base import _BaseModel
from pydantic import Field 
from typing import Any 
from sdlc_agents.state.schemas.common import LibraryRef


class Component(_BaseModel):
    name: str
    responsibility: str
    dependencies: list[str] = Field(default_factory=list)
    interfaces: list[str] = Field(default_factory=list)


class APIEndpoint(_BaseModel):
    method: str
    path: str
    summary: str
    request_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None


class DataModel(_BaseModel):
    name: str
    fields: dict[str, str]  # field_name -> type description
    indexes: list[str] = Field(default_factory=list)


class Design(_BaseModel):
    summary: str
    tech_stack: list[LibraryRef]
    components: list[Component]
    data_models: list[DataModel] = Field(default_factory=list)
    api_endpoints: list[APIEndpoint] = Field(default_factory=list)
    diagrams_mermaid: list[str] = Field(default_factory=list)
    adrs: list[str] = Field(default_factory=list)  # markdown ADR bodies
