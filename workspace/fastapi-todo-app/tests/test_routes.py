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
async def test_get_todos():
    response = client.get('/todos/')
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_update_todo():
    response = client.post('/todos/', json={'title': 'Update Todo'})
    todo_id = response.json()['id']
    response = client.put(f'/todos/{todo_id}', json={'title': 'Updated Title'})
    assert response.status_code == 200
    assert response.json()['title'] == 'Updated Title'

@pytest.mark.asyncio
async def test_delete_todo():
    response = client.post('/todos/', json={'title': 'Delete Todo'})
    todo_id = response.json()['id']
    response = client.delete(f'/todos/{todo_id}')
    assert response.status_code == 200
    assert response.json()['id'] == todo_id

@pytest.mark.asyncio
async def test_complete_todo():
    response = client.post('/todos/', json={'title': 'Complete Todo'})
    todo_id = response.json()['id']
    response = client.patch(f'/todos/{todo_id}/complete')
    assert response.status_code == 200
    assert response.json()['completed'] is True
