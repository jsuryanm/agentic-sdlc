from fastapi import APIRouter, HTTPException
from app.models import TodoItem
from app.storage import todo_storage

router = APIRouter()

@router.post("/todos/", response_model=TodoItem)
async def create_todo(todo: TodoItem) -> TodoItem:
    return todo_storage.create(todo)

@router.get("/todos/", response_model=list[TodoItem])
async def read_todos() -> list[TodoItem]:
    return todo_storage.get_all()

@router.get("/todos/{todo_id}", response_model=TodoItem)
async def read_todo(todo_id: int) -> TodoItem:
    todo = todo_storage.get(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo

@router.put("/todos/{todo_id}", response_model=TodoItem)
async def update_todo(todo_id: int, todo: TodoItem) -> TodoItem:
    updated_todo = todo_storage.update(todo_id, todo)
    if updated_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return updated_todo

@router.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    success = todo_storage.delete(todo_id)
    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"detail": "Todo deleted"}
