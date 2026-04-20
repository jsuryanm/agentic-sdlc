from pydantic import BaseModel
from typing import Optional

class TodoItem(BaseModel):
    id: int
    description: str
    completed: Optional[bool] = False  # Default value is False.