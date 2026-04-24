from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None

class Attendance(BaseModel):
    user_id: int
    event_id: int
    status: str

class Report(BaseModel):
    event_id: int
    total_attendance: int
    present_count: int
    absent_count: int
