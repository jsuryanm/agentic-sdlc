from pydantic import BaseModel
from typing import Optional

class TodoItem(BaseModel):
    id: Optional[int] = None
    title: str
    description: str

class TodoItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None  # Pydantic models for TODO items.