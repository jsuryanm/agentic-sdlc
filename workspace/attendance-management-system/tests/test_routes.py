import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def user_data():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User"
    }

@pytest.fixture
def attendance_data():
    return {
        "user_id": 1,
        "event_id": 1,
        "status": "present"
    }

@pytest.fixture
def event_id():
    return 1

def test_register_user(user_data):
    response = client.post('/register/', json=user_data)
    assert response.status_code == 200
    assert response.json()['username'] == user_data['username']

def test_mark_attendance(attendance_data):
    response = client.post('/attendance/', json=attendance_data)
    assert response.status_code == 200
    assert response.json()['status'] == attendance_data['status']

def test_view_attendance_report(event_id):
    response = client.get(f'/reports/{event_id}')
    assert response.status_code == 200
    assert response.json()['event_id'] == event_id
