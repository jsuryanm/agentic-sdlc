from pydantic import BaseModel
from typing import List

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str

class AttendanceCreate(BaseModel):
    user_id: int
    event_id: int
    status: str

class ReportResponse(BaseModel):
    event_id: int
    total_attendance: int
    present_count: int
    absent_count: int
