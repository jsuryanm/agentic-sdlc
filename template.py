import os 
from pathlib import Path
import logging 

logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s]: %(message)s")

project_name =  "sdlc_agents"
list_of_files = [
    ".github/workflows/.gitkeep",
    "src/__init__.py",
    "src/core/__init__.py",
    "src/core/config.py",
    "src/exceptions/__init__.py",
    "src/exceptions/custom_exceptions.py",
    "src/logger/__init__.py",
    "src/logger/custom_logger.py",
    "src/models/__init__.py",
    "src/models/schemas.py",
    "src/memory/__init__.py",
    "src/memory/extractor.py",
    "src/memory/models.py",
    "src/memory/recall.py",
    "src/memory/store.py",
    "src/a2a/__init__.py",
    "src/a2a/bus.py",
    "src/a2a/cards.py",
    "src/a2a/messages.py",
    "src/knowledge/__init__.py",
    "src/knowledge/agentic_rag.py",
    "src/knowledge/ingest.py",
    "src/knowledge/retriever.py",
    "src/knowledge/store.py",
    "src/knowledge/tavily_client.py",
    "src/tools/__init__.py",
    "src/tools/llm_factory.py",
    "src/tools/mcp_client.py",
    "src/tools/test_runner.py",
    "src/prompts/__init__.py",
    "src/prompts/developer_prompt.py",
    "src/prompts/devops_prompt.py",
    "src/prompts/requirement_prompt.py",
    "src/prompts/architect_prompt.py", 
    "src/agents/__init__.py",
    "src/agents/base_agent.py",
    "src/agents/requirements_agent.py",
    "src/agents/developer_agent.py",
    "src/agents/architect_agent.py",
    "src/agents/qa_agent.py",
    "src/agents/devops_agent.py",
    "src/pipelines/__init__.py",
    "src/pipelines/state.py",
    "src/pipelines/graph.py",
    "src/dashboard/__init__.py",
    "src/dashboard/streamlit_app.py",
    "src/tests/__init__.py",
    "src/tests/test_smoke.py",
    "requirements.txt",
    ".env",
    ".env.example"]


for file_path in list_of_files:
    file_path =  Path(file_path)
    file_dir,file_name = os.path.split(file_path)

    if file_dir != "":
        os.makedirs(file_dir,exist_ok=True)
        logging.info(f"Creating directory: {file_dir} for file: {file_name}")

    if (not os.path.exists(file_path)) or (os.path.getsize(file_path) == 0):
        with open(file_path,"w") as f:
            pass
            logging.info(f"Creating an empty file: {file_path}")
    
    else:
        logging.info(f"{file_name} already exists")