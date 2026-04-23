from typing import List, Optional
from app.models import TodoItem, TodoCreate

class TodoStorage:
    def __init__(self):
        self.todos = []
        self.counter = 1

    def create_todo(self, todo: TodoCreate) -> TodoItem:
        new_todo = TodoItem(id=self.counter, **todo.dict())
        self.todos.append(new_todo)
        self.counter += 1
        return new_todo

    def get_all_todos(self) -> List[TodoItem]:
        return self.todos

    def get_todo(self, todo_id: int) -> Optional[TodoItem]:
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None

    def update_todo(self, todo_id: int, todo: TodoCreate) -> Optional[TodoItem]:
        for index, existing_todo in enumerate(self.todos):
            if existing_todo.id == todo_id:
                updated_todo = existing_todo.copy(update=todo.dict())
                self.todos[index] = updated_todo
                return updated_todo
        return None

    def delete_todo(self, todo_id: int) -> bool:
        for index, existing_todo in enumerate(self.todos):
            if existing_todo.id == todo_id:
                del self.todos[index]
                return True
        return False

# Instantiate the storage

todo_storage = TodoStorage()
