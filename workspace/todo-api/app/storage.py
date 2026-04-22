from app.models import Todo, TodoCreate, TodoUpdate
from typing import List, Optional

class InMemoryStorage:
    def __init__(self):
        self.todos = []
        self.counter = 1

    def create(self, todo_create: TodoCreate) -> Todo:
        todo = Todo(id=self.counter, **todo_create.dict())
        self.todos.append(todo)
        self.counter += 1
        return todo

    def get_all(self) -> List[Todo]:
        return self.todos

    def get(self, todo_id: int) -> Optional[Todo]:
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None

    def update(self, todo_id: int, todo_update: TodoUpdate) -> Optional[Todo]:
        todo = self.get(todo_id)
        if todo:
            updated_data = todo.dict()
            updated_data.update(todo_update.dict(exclude_unset=True))
            updated_todo = Todo(**updated_data)
            self.todos = [updated_todo if t.id == todo_id else t for t in self.todos]
            return updated_todo
        return None

    def delete(self, todo_id: int) -> bool:
        for index, todo in enumerate(self.todos):
            if todo.id == todo_id:
                del self.todos[index]
                return True
        return False

# Initialize the in-memory storage

todo_storage = InMemoryStorage()