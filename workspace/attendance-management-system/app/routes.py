from fastapi import APIRouter
from app.schemas import UserCreate, AttendanceCreate, ReportResponse
from app.services import register_user, mark_attendance, get_attendance_report

router = APIRouter()

@router.post('/register/', response_model=UserCreate)
async def register_user_route(user: UserCreate):
    return await register_user(user)

@router.post('/attendance/', response_model=AttendanceCreate)
async def mark_attendance_route(attendance: AttendanceCreate):
    return await mark_attendance(attendance)

@router.get('/reports/{event_id}', response_model=ReportResponse)
async def view_attendance_report(event_id: int):
    return await get_attendance_report(event_id)
