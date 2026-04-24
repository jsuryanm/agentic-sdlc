from fastapi import APIRouter, HTTPException
from app.models import TodoItem, TodoCreate
from app.storage import todo_storage

router = APIRouter()

@router.post("/todos/", response_model=TodoItem)
async def create_todo(todo: TodoCreate):
    new_id = len(todo_storage) + 1
    todo_item = TodoItem(id=new_id, **todo.dict())
    todo_storage.append(todo_item)
    return todo_item

@router.get("/todos/")
async def read_todos():
    return todo_storage

@router.get("/todos/{todo_id}", response_model=TodoItem)
async def read_todo(todo_id: int):
    if todo_id <= 0 or todo_id > len(todo_storage):
        raise HTTPException(status_code=404, detail="Todo item not found")
    return todo_storage[todo_id - 1]

@router.put("/todos/{todo_id}", response_model=TodoItem)
async def update_todo(todo_id: int, todo: TodoCreate):
    if todo_id <= 0 or todo_id > len(todo_storage):
        raise HTTPException(status_code=404, detail="Todo item not found")
    updated_item = TodoItem(id=todo_id, **todo.dict())
    todo_storage[todo_id - 1] = updated_item
    return updated_item

@router.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    if todo_id <= 0 or todo_id > len(todo_storage):
        raise HTTPException(status_code=404, detail="Todo item not found")
    todo_storage.pop(todo_id - 1)
    return {"detail": "Todo item deleted"}
