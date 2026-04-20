import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.parametrize("description", ["Buy milk", "Walk the dog", "Read a book"])
def test_create_todo(description):
    response = client.post("/todos", json={"description": description})
    assert response.status_code == 201
    assert "id" in response.json()

def test_get_todos():
    response = client.get("/todos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_update_todo():
    response = client.post("/todos", json={"description": "Test update"})
    todo_id = response.json()["id"]
    response = client.put(f"/todos/{todo_id}", json={"description": "Updated description"})
    assert response.status_code == 200
    assert response.json()["description"] == "Updated description"

def test_delete_todo():
    response = client.post("/todos", json={"description": "Test delete"})
    todo_id = response.json()["id"]
    response = client.delete(f"/todos/{todo_id}")
    assert response.status_code == 204
    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 404

@pytest.mark.parametrize("todo_id", [999, 1000])
def test_update_non_existent_todo(todo_id):
    response = client.put(f"/todos/{todo_id}", json={"description": "Should fail"})
    assert response.status_code == 404

@pytest.mark.parametrize("todo_id", [999, 1000])
def test_delete_non_existent_todo(todo_id):
    response = client.delete(f"/todos/{todo_id}")
    assert response.status_code == 404
