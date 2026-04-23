from app.models import TodoItem, TodoCreate
from typing import List, Optional

class TodoStorage:
    def __init__(self):
        self.todos = []
        self.counter = 1

    def create_todo(self, todo: TodoCreate) -> TodoItem:
        todo_item = TodoItem(id=self.counter, **todo.dict())
        self.todos.append(todo_item)
        self.counter += 1
        return todo_item

    def get_all_todos(self) -> List[TodoItem]:
        return self.todos

    def get_todo(self, todo_id: int) -> Optional[TodoItem]:
        return next((todo for todo in self.todos if todo.id == todo_id), None)

    def update_todo(self, todo_id: int, todo_update: TodoCreate) -> Optional[TodoItem]:
        todo = self.get_todo(todo_id)
        if todo:
            updated_data = todo.dict()
            updated_data.update(todo_update.dict(exclude_unset=True))
            updated_todo = TodoItem(**updated_data)
            self.todos = [updated_todo if t.id == todo_id else t for t in self.todos]
            return updated_todo
        return None

    def delete_todo(self, todo_id: int) -> bool:
        todo = self.get_todo(todo_id)
        if todo:
            self.todos.remove(todo)
            return True
        return False
