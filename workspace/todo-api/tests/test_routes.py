import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def todo_data():
    return {"title": "Test Todo", "description": "Test Description", "completed": False}

def test_create_todo(todo_data):
    response = client.post("/todos/", json=todo_data)
    assert response.status_code == 200
    assert response.json()["title"] == todo_data["title"]


def test_read_todos():
    response = client.get("/todos/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_read_todo():
    response = client.post("/todos/", json=todo_data)
    todo_id = response.json()["id"]
    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 200
    assert response.json()["id"] == todo_id


def test_update_todo(todo_data):
    response = client.post("/todos/", json=todo_data)
    todo_id = response.json()["id"]
    updated_data = {"title": "Updated Todo", "description": "Updated Description", "completed": True}
    response = client.put(f"/todos/{todo_id}", json=updated_data)
    assert response.status_code == 200
    assert response.json()["title"] == updated_data["title"]


def test_delete_todo():
    response = client.post("/todos/", json=todo_data)
    todo_id = response.json()["id"]
    response = client.delete(f"/todos/{todo_id}")
    assert response.status_code == 200
    assert response.json()["detail"] == "Todo deleted"

    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 404
