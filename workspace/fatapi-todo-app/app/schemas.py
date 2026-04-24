from pydantic import BaseModel

class TodoTaskBase(BaseModel):
    title: str
    description: str | None = None

class TodoTaskCreate(TodoTaskBase):
    pass

class TodoTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    completed: bool | None = None

class TodoTaskResponse(TodoTaskBase):
    id: int
    completed: bool

    class Config:
        orm_mode = True
