from langchain_core.prompts import ChatPromptTemplate

from src.agents.base_agent import BaseAgent
from src.models.schemas import Requirements
from src.pipelines.state import SDLCState
from src.tools.llm_factory import LLMFactory

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

class RequirementAgent(BaseAgent):
    name = 'requirement_agent'

    def __init__(self):
        super().__init__()
        self.llm = LLMFactory.get().with_structured_output(Requirements)
        self._chain = REQUIREMENT_PROMPT | self.llm

    def _process(self, state: SDLCState) -> dict:
        feedback = self._latest_feedback(state, phase='requirements')
        result: Requirements = self._chain.invoke({
            'idea': state['idea'],
            'feedback': feedback or 'none'
        })
        self.logger.info(f'Requirements: {result.project_name} '
                         f'({len(result.user_stories)} stories)')
        return {'requirements': result.model_dump(), 'status': 'requirements_drafted'}
    
    @staticmethod
    def _latest_feedback(state: SDLCState, phase: str) -> str:
        relevant = [f for f in state.get('feedback', []) if f.get('phase') == phase]
        if not relevant:
            return ''
        return relevant[-1].get('comment','')