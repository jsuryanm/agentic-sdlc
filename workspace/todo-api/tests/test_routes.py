import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.parametrize("title, description", [
    ("Test Todo", "This is a test todo item."),
    ("Another Todo", "Another description.")
])
def test_create_todo(title, description):
    response = client.post("/todos", json={"title": title, "description": description})
    assert response.status_code == 201
    assert "id" in response.json()


def test_read_todos():
    response = client.get("/todos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_update_todo():
    response = client.post("/todos", json={"title": "Update Todo", "description": "Update description."})
    todo_id = response.json()["id"]
    response = client.put(f"/todos/{todo_id}", json={"title": "Updated Title"})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_delete_todo():
    response = client.post("/todos", json={"title": "Delete Todo", "description": "Delete this todo."})
    todo_id = response.json()["id"]
    response = client.delete(f"/todos/{todo_id}")
    assert response.status_code == 204


def test_non_existent_todo():
    response = client.get("/todos/999")
    assert response.status_code == 404
    response = client.put("/todos/999", json={"title": "Non-existent Todo"})
    assert response.status_code == 404
    response = client.delete("/todos/999")
    assert response.status_code == 404  # Unit tests for the FastAPI routes.