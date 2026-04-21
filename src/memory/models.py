from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

class RunRecord(BaseModel):
    thread_id: str
    idea: str
    project_name: str
    stack: List[str]
    outcome: str
    qa_retries: int = 0
    human_feedback: List[str]
    pr_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

class Lesson(BaseModel):
    thread_id: str
    category: str
    content: str
    outcome: str