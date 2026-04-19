from langchain_core.prompts import ChatPromptTemplate

DEV_PROMPT = ChatPromptTemplate.from_messages([
    ('system',
     'You are a senior Python engineer. Generate COMPLETE, RUNNABLE code for '
     'every file in the architecture. Use FastAPI + Pydantic v2. Include '
     'type hints and docstrings. Always include a requirements.txt. '
     'Tests must use pytest and be runnable from the project root with '
     '`python -m pytest`. Output ONLY the structured Codebase object - no prose.'),
    ('human',
     'Requirements:\n{requirements}\n\n'
     'Architecture:\n{architecture}\n\n'
     'QA feedback from previous attempt (if any):\n{qa_feedback}\n\n'
     'Generate the full codebase')
])
