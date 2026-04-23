import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def todo_data():
    return {
        "title": "Test Todo",
        "description": "This is a test todo item."
    }

def test_create_todo(todo_data):
    response = client.post("/todos/", json=todo_data)
    assert response.status_code == 200
    assert "id" in response.json()


def test_read_todos():
    response = client.get("/todos/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_update_todo(todo_data):
    create_response = client.post("/todos/", json=todo_data)
    todo_id = create_response.json()["id"]
    updated_data = {"title": "Updated Todo", "description": "Updated description."}
    response = client.put(f"/todos/{todo_id}", json=updated_data)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Todo"


def test_delete_todo():
    create_response = client.post("/todos/", json={"title": "Todo to delete"})
    todo_id = create_response.json()["id"]
    response = client.delete(f"/todos/{todo_id}")
    assert response.status_code == 200
    assert response.json()["detail"] == "Todo deleted successfully"

    # Verify deletion
    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 404
