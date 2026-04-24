import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client() -> TestClient:
    return TestClient(app)

@pytest.mark.asyncio
async def test_create_todo(client: TestClient):
    response = client.post('/todos/', json={'title': 'Test Todo', 'description': 'A test todo item.'})
    assert response.status_code == 200
    assert response.json()['title'] == 'Test Todo'

@pytest.mark.asyncio
async def test_get_todos(client: TestClient):
    response = client.get('/todos/')
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_update_todo(client: TestClient):
    response = client.post('/todos/', json={'title': 'Update Todo'})
    todo_id = response.json()['id']
    response = client.put(f'/todos/{todo_id}', json={'title': 'Updated Todo'})
    assert response.status_code == 200
    assert response.json()['title'] == 'Updated Todo'

@pytest.mark.asyncio
async def test_delete_todo(client: TestClient):
    response = client.post('/todos/', json={'title': 'Delete Todo'})
    todo_id = response.json()['id']
    response = client.delete(f'/todos/{todo_id}')
    assert response.status_code == 200
    assert response.json() == {'message': 'Todo item deleted successfully'}

@pytest.mark.asyncio
async def test_error_handling(client: TestClient):
    response = client.put('/todos/999', json={'title': 'Non-existent Todo'})
    assert response.status_code == 404
    assert response.json()['detail'] == 'Todo item not found'