import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_create_todo():
    response = client.post("/todos/", json={"id": 1, "title": "Test Todo"})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "title": "Test Todo", "completed": False}

@pytest.mark.asyncio
async def test_get_todos():
    response = client.get("/todos/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_update_todo():
    response = client.put("/todos/1", json={"id": 1, "title": "Updated Todo", "completed": False})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Todo"

@pytest.mark.asyncio
async def test_delete_todo():
    response = client.delete("/todos/1")
    assert response.status_code == 204

@pytest.mark.asyncio
async def test_complete_todo():
    response = client.patch("/todos/1/complete")
    assert response.status_code == 200
    assert response.json()["completed"] is True
