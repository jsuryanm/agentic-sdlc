from langchain_core.prompts import ChatPromptTemplate

REQUIREMENT_PROMPT = ChatPromptTemplate.from_messages([
    ('system',
     "You are a senior product manager. Convert the user's idea into concrete "
     'software requirements. Be pragmatic - target something buildable as a '
     'small Python FastAPI service in a few files. Generate 3-5 user stories, '
     'each with 2-3 acceptance criteria. Always include a tests/ directory '
     'in the implied project structure.'),
    ('human',
     'Idea:\n{idea}\n\n'
     'Previous feedback (if any): {feedback}\n\n'
     'Produce the structured Requirements object.')
])
