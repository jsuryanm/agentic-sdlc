import pytest
from app.services import register_user, mark_attendance, get_attendance_report
from app.models import User, Attendance, Report

@pytest.fixture
def user():
    return User(id=1, username="testuser", email="test@example.com")

@pytest.fixture
def attendance():
    return Attendance(user_id=1, event_id=1, status="present")

@pytest.fixture
def event_id():
    return 1

async def test_register_user(user):
    result = await register_user(user)
    assert result.username == user.username

async def test_mark_attendance(attendance):
    result = await mark_attendance(attendance)
    assert result.status == attendance.status

async def test_get_attendance_report(event_id):
    result = await get_attendance_report(event_id)
    assert result.event_id == event_id
