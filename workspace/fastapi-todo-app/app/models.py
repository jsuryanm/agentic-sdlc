from pydantic import BaseModel
from typing import Optional

class TodoItem(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool = False
