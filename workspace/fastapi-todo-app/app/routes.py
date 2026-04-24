from fastapi import APIRouter, HTTPException
from app.models import TodoCreate, TodoUpdate, TodoResponse
from app.database import db

router = APIRouter()

@router.post('/todos/', response_model=TodoResponse)
async def create_todo(todo: TodoCreate):
    todo_id = len(db) + 1
    new_todo = {"id": todo_id, "title": todo.title, "description": todo.description, "completed": False}
    db.append(new_todo)
    return new_todo

@router.get('/todos/', response_model=list[TodoResponse])
async def get_todos():
    return db

@router.put('/todos/{todo_id}', response_model=TodoResponse)
async def update_todo(todo_id: int, todo_update: TodoUpdate):
    for todo in db:
        if todo['id'] == todo_id:
            if todo_update.title is not None:
                todo['title'] = todo_update.title
            if todo_update.description is not None:
                todo['description'] = todo_update.description
            if todo_update.completed is not None:
                todo['completed'] = todo_update.completed
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")

@router.delete('/todos/{todo_id}', response_model=TodoResponse)
async def delete_todo(todo_id: int):
    for index, todo in enumerate(db):
        if todo['id'] == todo_id:
            return db.pop(index)
    raise HTTPException(status_code=404, detail="Todo not found")

@router.patch('/todos/{todo_id}/complete', response_model=TodoResponse)
async def complete_todo(todo_id: int):
    for todo in db:
        if todo['id'] == todo_id:
            todo['completed'] = True
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")
