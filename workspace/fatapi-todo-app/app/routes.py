from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db

router = APIRouter()

@router.post('/tasks/', response_model=schemas.TodoTaskResponse)
async def create_task(task: schemas.TodoTaskCreate, db: Session = next(get_db())):
    db_task = models.TodoTask(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.get('/tasks/', response_model=list[schemas.TodoTaskResponse])
async def read_tasks(skip: int = 0, limit: int = 10, db: Session = next(get_db())):
    tasks = db.query(models.TodoTask).offset(skip).limit(limit).all()
    return tasks

@router.put('/tasks/{task_id}', response_model=schemas.TodoTaskResponse)
async def update_task(task_id: int, task: schemas.TodoTaskUpdate, db: Session = next(get_db())):
    db_task = db.query(models.TodoTask).filter(models.TodoTask.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in task.dict(exclude_unset=True).items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.delete('/tasks/{task_id}', response_model=schemas.TodoTaskResponse)
async def delete_task(task_id: int, db: Session = next(get_db())):
    db_task = db.query(models.TodoTask).filter(models.TodoTask.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()
    return db_task

@router.patch('/tasks/{task_id}/complete', response_model=schemas.TodoTaskResponse)
async def complete_task(task_id: int, db: Session = next(get_db())):
    db_task = db.query(models.TodoTask).filter(models.TodoTask.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db_task.completed = True
    db.commit()
    db.refresh(db_task)
    return db_task
