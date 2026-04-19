from langchain_core.prompts import ChatPromptTemplate

REQUIREMENT_PROMPT = ChatPromptTemplate.from_messages([
    ('system',
     "You are a senior product manager. Convert the user's ideas into concrete "
     'software requirments. Be pragmatic - target something buildable as a '
     'small Python FastAPI service in a few files. Generate 3-5 user stories'
     'tests/directory.'),
     ('human',
      'Idea:\n{idea}\n\n'
      'Previous feedback (if any): {feedback}\n\n'
      'Produce the structured Requirements object.')
])