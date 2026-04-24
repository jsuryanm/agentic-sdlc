import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(setup_database):
    with TestClient(app) as c:
        yield c

@pytest.mark.asyncio
async def test_create_task(client):
    response = client.post('/tasks/', json={"title": "Test Task", "description": "Test Description"})
    assert response.status_code == 200
    assert response.json()['title'] == "Test Task"

@pytest.mark.asyncio
async def test_read_tasks(client):
    response = client.get('/tasks/')
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_update_task(client):
    response = client.post('/tasks/', json={"title": "Update Task", "description": "Update Description"})
    task_id = response.json()['id']
    response = client.put(f'/tasks/{task_id}', json={"title": "Updated Task"})
    assert response.status_code == 200
    assert response.json()['title'] == "Updated Task"

@pytest.mark.asyncio
async def test_delete_task(client):
    response = client.post('/tasks/', json={"title": "Delete Task", "description": "Delete Description"})
    task_id = response.json()['id']
    response = client.delete(f'/tasks/{task_id}')
    assert response.status_code == 200
    assert response.json()['id'] == task_id

@pytest.mark.asyncio
async def test_complete_task(client):
    response = client.post('/tasks/', json={"title": "Complete Task", "description": "Complete Description"})
    task_id = response.json()['id']
    response = client.patch(f'/tasks/{task_id}/complete')
    assert response.status_code == 200
    assert response.json()['completed'] is True
