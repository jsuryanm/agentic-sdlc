from app.models import TodoItem
from typing import List, Dict, Optional

class InMemoryStorage:
    def __init__(self):
        self.todos: Dict[int, TodoItem] = {}
        self.counter = 1

    async def create(self, todo: TodoItem) -> TodoItem:
        todo_item = TodoItem(id=self.counter, **todo.dict())
        self.todos[self.counter] = todo_item
        self.counter += 1
        return todo_item

    async def get_all(self) -> List[TodoItem]:
        return list(self.todos.values())

    async def update(self, todo_id: int, todo: TodoItem) -> TodoItem:
        if todo_id not in self.todos:
            raise ValueError('Todo item not found')
        updated_todo = TodoItem(id=todo_id, **todo.dict())
        self.todos[todo_id] = updated_todo
        return updated_todo

    async def delete(self, todo_id: int) -> None:
        if todo_id not in self.todos:
            raise ValueError('Todo item not found')
        del self.todos[todo_id]

# Initialize the in-memory storage

todo_storage = InMemoryStorage()