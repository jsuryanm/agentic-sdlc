import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.parametrize("todo_data, expected_status", [
    ({"title": "Test TODO", "description": "A test item"}, 201),
    ({"title": ""}, 422),  # Invalid request
])
def test_create_todo(todo_data, expected_status):
    response = client.post("/todos/", json=todo_data)
    assert response.status_code == expected_status


def test_read_todos():
    response = client.get("/todos/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_update_todo():
    # First create a TODO item
    response = client.post("/todos/", json={"title": "Update Test"})
    todo_id = response.json()["id"]

    # Now update it
    response = client.put(f"/todos/{todo_id}", json={"title": "Updated Title"})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_delete_todo():
    # First create a TODO item
    response = client.post("/todos/", json={"title": "Delete Test"})
    todo_id = response.json()["id"]

    # Now delete it
    response = client.delete(f"/todos/{todo_id}")
    assert response.status_code == 200
    assert response.json() == {"detail": "TODO item deleted"}

    # Verify it's deleted
    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 404
