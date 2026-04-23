from fastapi import APIRouter, HTTPException
from app.models import TodoCreate, TodoResponse
from app.storage import todo_storage

todo_router = APIRouter()

@todo_router.post("/todos/", response_model=TodoResponse)
async def create_todo(todo: TodoCreate):
    return todo_storage.create(todo)

@todo_router.get("/todos/", response_model=list[TodoResponse])
async def read_todos():
    return todo_storage.get_all()

@todo_router.put("/todos/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: int, todo: TodoCreate):
    updated_todo = todo_storage.update(todo_id, todo)
    if updated_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return updated_todo

@todo_router.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    success = todo_storage.delete(todo_id)
    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"detail": "Todo deleted successfully"}
