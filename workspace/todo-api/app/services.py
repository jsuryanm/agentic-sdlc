from app.models import Todo, TodoCreate, TodoUpdate
from typing import List, Optional

class TodoService:
    def __init__(self):
        self.todos = []  # In-memory storage
        self.counter = 1

    def create_todo(self, todo_create: TodoCreate) -> Todo:
        todo = Todo(id=self.counter, **todo_create.dict())
        self.todos.append(todo)
        self.counter += 1
        return todo

    def get_all_todos(self) -> List[Todo]:
        return self.todos

    def get_todo(self, todo_id: int) -> Optional[Todo]:
        return next((todo for todo in self.todos if todo.id == todo_id), None)

    def update_todo(self, todo_id: int, todo_update: TodoUpdate) -> Optional[Todo]:
        todo = self.get_todo(todo_id)
        if todo:
            update_data = todo_update.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(todo, key, value)
            return todo
        return None

    def delete_todo(self, todo_id: int) -> Optional[Todo]:
        todo = self.get_todo(todo_id)
        if todo:
            self.todos.remove(todo)
            return todo
        return None
