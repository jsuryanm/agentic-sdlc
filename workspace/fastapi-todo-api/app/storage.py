from typing import List, Optional
from app.models import TodoItem, TodoCreate, TodoUpdate

class TodoStorage:
    def __init__(self):
        self.todos = []
        self.counter = 1

    def create(self, todo: TodoCreate) -> TodoItem:
        todo_item = TodoItem(id=self.counter, **todo.dict())
        self.todos.append(todo_item)
        self.counter += 1
        return todo_item

    def get_all(self) -> List[TodoItem]:
        return self.todos

    def get(self, todo_id: int) -> Optional[TodoItem]:
        return next((todo for todo in self.todos if todo.id == todo_id), None)

    def update(self, todo_id: int, todo_update: TodoUpdate) -> Optional[TodoItem]:
        todo = self.get(todo_id)
        if todo:
            updated_data = todo.dict()
            updated_data.update(todo_update.dict(exclude_unset=True))
            updated_todo = TodoItem(**updated_data)
            self.todos = [updated_todo if t.id == todo_id else t for t in self.todos]
            return updated_todo
        return None

    def delete(self, todo_id: int) -> Optional[TodoItem]:
        todo = self.get(todo_id)
        if todo:
            self.todos = [t for t in self.todos if t.id != todo_id]
            return todo
        return None

# Create a singleton instance of TodoStorage

todo_storage = TodoStorage()
