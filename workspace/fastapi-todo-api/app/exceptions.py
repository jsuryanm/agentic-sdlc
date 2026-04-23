from fastapi import HTTPException

class TodoNotFoundException(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="Todo not found")
