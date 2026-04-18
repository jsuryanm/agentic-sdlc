from datetime import datetime,timezone
from typing import Annotated,Any,TypedDict
from uuid import UUID,uuid4

from pydantic import BaseModel,ConfigDict,Field,HttpUrl
from typing_extensions import NotRequired

class _BaseModel(BaseModel):
    """Base model with sensible defaults for all state objects."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)