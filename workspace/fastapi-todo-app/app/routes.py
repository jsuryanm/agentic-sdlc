from fastapi import APIRouter, HTTPException
from app.models import TodoItem
from app.database import fake_db

router = APIRouter()

@router.post("/todos/", response_model=TodoItem)
async def create_todo(todo: TodoItem):
    fake_db.append(todo)
    return todo

@router.get("/todos/")
async def get_todos():
    return fake_db

@router.put("/todos/{todo_id}", response_model=TodoItem)
async def update_todo(todo_id: int, todo: TodoItem):
    for index, item in enumerate(fake_db):
        if item.id == todo_id:
            fake_db[index] = todo
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")

@router.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    for index, item in enumerate(fake_db):
        if item.id == todo_id:
            del fake_db[index]
            return
    raise HTTPException(status_code=404, detail="Todo not found")

@router.patch("/todos/{todo_id}/complete")
async def complete_todo(todo_id: int):
    for item in fake_db:
        if item.id == todo_id:
            item.completed = True
            return item
    raise HTTPException(status_code=404, detail="Todo not found")
