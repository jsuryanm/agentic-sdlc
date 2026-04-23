from fastapi import APIRouter, HTTPException
from app.models import TodoItem, TodoCreate
from app.storage import todo_storage

router = APIRouter()

@router.post("/todos/", response_model=TodoItem)
async def create_todo(todo: TodoCreate):
    return todo_storage.create_todo(todo)

@router.get("/todos/")
async def read_todos():
    return todo_storage.get_all_todos()

@router.get("/todos/{todo_id}", response_model=TodoItem)
async def read_todo(todo_id: int):
    todo = todo_storage.get_todo(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo

@router.put("/todos/{todo_id}", response_model=TodoItem)
async def update_todo(todo_id: int, todo: TodoCreate):
    updated_todo = todo_storage.update_todo(todo_id, todo)
    if updated_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return updated_todo

@router.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    success = todo_storage.delete_todo(todo_id)
    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"detail": "Todo deleted successfully"}
