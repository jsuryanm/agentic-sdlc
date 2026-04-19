from langchain_core.prompts import ChatPromptTemplate

DEVOPS_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a DevOps engineer. Generate a Dockerfile and a GitHub Actions "
     "CI workflow for a Python FastAPI project. CI must: install deps, run "
     "pytest, build the Docker image. Use python:3.11-slim base. Suggest a "
     "short kebab-case branch name."),
    ("human",
     "Project: {project_name}\n"
     "Entry point: {entry_point}\n"
     "Stack: {stack}"),
])