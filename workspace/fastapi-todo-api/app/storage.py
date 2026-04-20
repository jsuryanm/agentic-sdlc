from app.models import TodoItem
from typing import List, Optional

class TodoStorage:
    def __init__(self):
        self.todos = []  # In-memory storage
        self.counter = 1

    def create(self, item: TodoItem) -> TodoItem:
        item.id = self.counter
        self.todos.append(item)
        self.counter += 1
        return item

    def get_all(self) -> List[TodoItem]:
        return self.todos

    def update(self, id: int, item: TodoItem) -> Optional[TodoItem]:
        for idx, todo in enumerate(self.todos):
            if todo.id == id:
                self.todos[idx] = item
                item.id = id  # Maintain the same ID
                return item
        return None

    def delete(self, id: int) -> bool:
        for idx, todo in enumerate(self.todos):
            if todo.id == id:
                del self.todos[idx]
                return True
        return False

# Create a singleton instance of TodoStorage
todo_storage = TodoStorage()