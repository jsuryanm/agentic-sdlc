from langchain_core.prompts import ChatPromptTemplate

ARCHITECT_PROMPT = ChatPromptTemplate.from_messages([
    ('system',
     'You are a senior software architect. Given product requirements, design '
     'a minimal Python project: FastAPI + Pydantic + pytest. Keep it to 5-10 '
     'files MAX. Every file must have a clear, single purpose. Include a '
     'tests/ directory.'),
    ('human',
     'Requirements:\n{requirements}\n\n'
     'Previous feedback (if any): {feedback}\n\n'
     'Past lessons from similar projects:\n{past_lessons}\n\n'
     'Produce the structured Architecture object.')
])
