from fastapi import APIRouter, HTTPException
from app.models import Todo, TodoCreate, TodoUpdate
from app.database import todos_db

router = APIRouter()

@router.post("/todos/", response_model=Todo)
async def create_todo(todo: TodoCreate) -> Todo:
    """Create a new TODO item."""
    new_id = len(todos_db) + 1
    todo_item = Todo(id=new_id, **todo.dict())
    todos_db.append(todo_item)
    return todo_item

@router.get("/todos/", response_model=list[Todo])
async def read_todos() -> list[Todo]:
    """Retrieve all TODO items."""
    return todos_db

@router.get("/todos/{todo_id}", response_model=Todo)
async def read_todo(todo_id: int) -> Todo:
    """Retrieve a TODO item by its ID."""
    for todo in todos_db:
        if todo.id == todo_id:
            return todo
    raise HTTPException(status_code=404, detail="TODO item not found")

@router.put("/todos/{todo_id}", response_model=Todo)
async def update_todo(todo_id: int, todo_update: TodoUpdate) -> Todo:
    """Update a TODO item by its ID."""
    for index, todo in enumerate(todos_db):
        if todo.id == todo_id:
            updated_todo = Todo(id=todo.id, **todo_update.dict())
            todos_db[index] = updated_todo
            return updated_todo
    raise HTTPException(status_code=404, detail="TODO item not found")

@router.delete("/todos/{todo_id}", response_model=dict)
async def delete_todo(todo_id: int) -> dict:
    """Delete a TODO item by its ID."""
    for index, todo in enumerate(todos_db):
        if todo.id == todo_id:
            del todos_db[index]
            return {"detail": "TODO item deleted"}
    raise HTTPException(status_code=404, detail="TODO item not found")