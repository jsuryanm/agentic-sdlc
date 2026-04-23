from fastapi import APIRouter, HTTPException
from app.models import TodoCreate, TodoUpdate, TodoItem
from app.storage import todo_storage

router = APIRouter()

@router.post('/todos/', response_model=TodoItem)
async def create_todo(todo: TodoCreate):
    return todo_storage.create(todo)

@router.get('/todos/', response_model=list[TodoItem])
async def get_all_todos():
    return todo_storage.get_all()

@router.get('/todos/{todo_id}', response_model=TodoItem)
async def get_todo(todo_id: int):
    todo = todo_storage.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo

@router.put('/todos/{todo_id}', response_model=TodoItem)
async def update_todo(todo_id: int, todo_update: TodoUpdate):
    todo = todo_storage.update(todo_id, todo_update)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo

@router.delete('/todos/{todo_id}', response_model=TodoItem)
async def delete_todo(todo_id: int):
    todo = todo_storage.delete(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo
