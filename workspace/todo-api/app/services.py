from app.models import TodoItem
from typing import List, Optional

class TodoService:
    def __init__(self):
        self.todos = []  # In-memory storage
        self.counter = 1

    def create_todo(self, item: TodoItem) -> TodoItem:
        item.id = self.counter
        self.todos.append(item)
        self.counter += 1
        return item

    def get_all_todos(self) -> List[TodoItem]:
        return self.todos

    def update_todo(self, id: int, item_update) -> Optional[TodoItem]:
        for todo in self.todos:
            if todo.id == id:
                if item_update.title:
                    todo.title = item_update.title
                if item_update.description:
                    todo.description = item_update.description
                return todo
        return None

    def delete_todo(self, id: int) -> bool:
        for index, todo in enumerate(self.todos):
            if todo.id == id:
                del self.todos[index]
                return True
        return False  # Service layer for handling business logic related to TODO items.