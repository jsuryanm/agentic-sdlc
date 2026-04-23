import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_create_todo():
    response = client.post('/todos/', json={'title': 'Test Todo', 'description': 'Test Description'})
    assert response.status_code == 200
    assert response.json()['title'] == 'Test Todo'

@pytest.mark.asyncio
async def test_get_all_todos():
    response = client.get('/todos/')
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_get_todo():
    response = client.post('/todos/', json={'title': 'Test Todo', 'description': 'Test Description'})
    todo_id = response.json()['id']
    response = client.get(f'/todos/{todo_id}')
    assert response.status_code == 200
    assert response.json()['id'] == todo_id

@pytest.mark.asyncio
async def test_update_todo():
    response = client.post('/todos/', json={'title': 'Test Todo', 'description': 'Test Description'})
    todo_id = response.json()['id']
    response = client.put(f'/todos/{todo_id}', json={'title': 'Updated Todo'})
    assert response.status_code == 200
    assert response.json()['title'] == 'Updated Todo'

@pytest.mark.asyncio
async def test_delete_todo():
    response = client.post('/todos/', json={'title': 'Test Todo', 'description': 'Test Description'})
    todo_id = response.json()['id']
    response = client.delete(f'/todos/{todo_id}')
    assert response.status_code == 200
    assert response.json()['id'] == todo_id
    response = client.get(f'/todos/{todo_id}')
    assert response.status_code == 404
