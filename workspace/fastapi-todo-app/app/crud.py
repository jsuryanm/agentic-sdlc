from app.models import TodoItem, TodoCreate, TodoUpdate, TodoStatus

# In-memory storage for demonstration purposes
_todos = []
_next_id = 1

def create_todo(todo_create: TodoCreate) -> TodoItem:
    global _next_id
    todo_item = TodoItem(id=_next_id, **todo_create.dict())
    _todos.append(todo_item)
    _next_id += 1
    return todo_item

def get_todo(todo_id: int) -> TodoItem:
    for todo in _todos:
        if todo.id == todo_id:
            return todo
    return None

def update_todo(todo_id: int, todo_update: TodoUpdate) -> TodoItem:
    for todo in _todos:
        if todo.id == todo_id:
            updated_data = todo.dict()
            updated_data.update(todo_update.dict(exclude_unset=True))
            updated_todo = TodoItem(**updated_data)
            _todos[_todos.index(todo)] = updated_todo
            return updated_todo
    return None

def delete_todo(todo_id: int) -> bool:
    global _todos
    _todos = [todo for todo in _todos if todo.id != todo_id]
    return True

def list_todos_by_status(status: TodoStatus) -> list[TodoItem]:
    return [todo for todo in _todos if todo.status == status]
