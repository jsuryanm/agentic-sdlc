import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_create_todo():
    response = client.post("/todos/", json={"title": "Test Todo", "description": "A test todo item."})
    assert response.status_code == 200
    assert response.json()["title"] == "Test Todo"

@pytest.mark.asyncio
async def test_read_todos():
    response = client.get("/todos/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_update_todo():
    response = client.post("/todos/", json={"title": "Update Todo", "description": "An updated todo item."})
    todo_id = response.json()["id"]
    response = client.put(f"/todos/{todo_id}", json={"title": "Updated Todo", "description": "An updated todo item."})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Todo"

@pytest.mark.asyncio
async def test_delete_todo():
    response = client.post("/todos/", json={"title": "Delete Todo", "description": "A todo item to delete."})
    todo_id = response.json()["id"]
    response = client.delete(f"/todos/{todo_id}")
    assert response.status_code == 200
    assert response.json()["detail"] == "Todo item deleted"

@pytest.mark.asyncio
async def test_handle_non_existent_todo():
    response = client.get("/todos/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo item not found"
