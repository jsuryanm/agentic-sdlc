from app.models import TodoCreate, TodoResponse
from typing import List, Dict, Optional

class InMemoryStorage:
    def __init__(self):
        self.todos: Dict[int, TodoResponse] = {}
        self.counter = 1

    def create(self, todo: TodoCreate) -> TodoResponse:
        todo_response = TodoResponse(
            id=self.counter,
            title=todo.title,
            description=todo.description,
            completed=False,
        )
        self.todos[self.counter] = todo_response
        self.counter += 1
        return todo_response

    def get_all(self) -> List[TodoResponse]:
        return list(self.todos.values())

    def update(self, todo_id: int, todo: TodoCreate) -> Optional[TodoResponse]:
        if todo_id in self.todos:
            self.todos[todo_id].title = todo.title
            self.todos[todo_id].description = todo.description
            return self.todos[todo_id]
        return None

    def delete(self, todo_id: int) -> bool:
        if todo_id in self.todos:
            del self.todos[todo_id]
            return True
        return False

# Initialize the in-memory storage

todo_storage = InMemoryStorage()
