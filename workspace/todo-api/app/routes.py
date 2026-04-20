from fastapi import APIRouter, HTTPException
from app.models import TodoItem, TodoItemUpdate
from app.services import TodoService

router = APIRouter()
service = TodoService()

@router.post("/todos", response_model=TodoItem, status_code=201)
async def create_todo(item: TodoItem):
    return service.create_todo(item)

@router.get("/todos", response_model=list[TodoItem])
async def read_todos():
    return service.get_all_todos()

@router.put("/todos/{id}", response_model=TodoItem)
async def update_todo(id: int, item: TodoItemUpdate):
    updated_item = service.update_todo(id, item)
    if updated_item is None:
        raise HTTPException(status_code=404, detail="Todo item not found")
    return updated_item

@router.delete("/todos/{id}", status_code=204)
async def delete_todo(id: int):
    if not service.delete_todo(id):
        raise HTTPException(status_code=404, detail="Todo item not found")  # FastAPI routes for CRUD operations on TODO items.