import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_todo():
    response = client.post("/todos", json={"title": "Test Todo", "description": "Test Description"})
    assert response.status_code == 201
    assert response.json()["title"] == "Test Todo"


def test_read_todos():
    response = client.get("/todos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_update_todo():
    response = client.post("/todos", json={"title": "Update Todo"})
    todo_id = response.json()["id"]
    response = client.put(f"/todos/{todo_id}", json={"title": "Updated Title"})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_delete_todo():
    response = client.post("/todos", json={"title": "Delete Todo"})
    todo_id = response.json()["id"]
    response = client.delete(f"/todos/{todo_id}")
    assert response.status_code == 204


def test_read_todo_not_found():
    response = client.get("/todos/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo not found"
