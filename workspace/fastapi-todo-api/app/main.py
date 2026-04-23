from fastapi import FastAPI
from app.routes import router as todo_router

app = FastAPI()

app.include_router(todo_router)

@app.get("/")
async def root() -> str:
    """Root endpoint for the FastAPI application."""
    return "Welcome to the TODO API!"