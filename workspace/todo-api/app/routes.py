from fastapi import APIRouter, HTTPException
from app.models import TodoItem, TodoCreate
from app.storage import todo_storage

router = APIRouter()

@router.post('/todos/', response_model=TodoItem)
async def create_todo(todo: TodoCreate):
    try:
        return await todo_storage.create(todo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/todos/', response_model=list[TodoItem])
async def get_todos():
    return await todo_storage.get_all()

@router.put('/todos/{todo_id}', response_model=TodoItem)
async def update_todo(todo_id: int, todo: TodoCreate):
    try:
        return await todo_storage.update(todo_id, todo)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete('/todos/{todo_id}', response_model=dict)
async def delete_todo(todo_id: int):
    try:
        await todo_storage.delete(todo_id)
        return {'message': 'Todo item deleted successfully'}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
