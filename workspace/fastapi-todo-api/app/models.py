from pydantic import BaseModel
from typing import Optional

class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None

class TodoCreate(TodoBase):
    """Model for creating a TODO item."""
    pass

class TodoUpdate(TodoBase):
    """Model for updating a TODO item."""
    pass

class Todo(TodoBase):
    id: int

    class Config:
        orm_mode = True