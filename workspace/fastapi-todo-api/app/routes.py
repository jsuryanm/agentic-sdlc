from fastapi import APIRouter, HTTPException
from app.models import TodoItem
from app.storage import todo_storage

router = APIRouter()

@router.post("/todos", response_model=TodoItem, status_code=201)
async def create_todo(item: TodoItem):
    return todo_storage.create(item)

@router.get("/todos", response_model=list[TodoItem])
async def get_todos():
    return todo_storage.get_all()

@router.put("/todos/{id}", response_model=TodoItem)
async def update_todo(id: int, item: TodoItem):
    updated_item = todo_storage.update(id, item)
    if updated_item is None:
        raise HTTPException(status_code=404, detail="Todo item not found")
    return updated_item

@router.delete("/todos/{id}", status_code=204)
async def delete_todo(id: int):
    if not todo_storage.delete(id):
        raise HTTPException(status_code=404, detail="Todo item not found")