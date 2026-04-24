from fastapi import APIRouter, HTTPException
from app.models import Todo, TodoCreate, TodoUpdate
from app.services import TodoService

router = APIRouter()
service = TodoService()

@router.post('/todos/', response_model=Todo)
async def create_todo(todo_create: TodoCreate):
    todo = service.create_todo(todo_create)
    return todo

@router.get('/todos/', response_model=list[Todo])
async def read_todos():
    return service.get_all_todos()

@router.get('/todos/{todo_id}', response_model=Todo)
async def read_todo(todo_id: int):
    todo = service.get_todo(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo

@router.put('/todos/{todo_id}', response_model=Todo)
async def update_todo(todo_id: int, todo_update: TodoUpdate):
    todo = service.update_todo(todo_id, todo_update)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo

@router.delete('/todos/{todo_id}', response_model=Todo)
async def delete_todo(todo_id: int):
    todo = service.delete_todo(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo
