from langchain_core.prompts import ChatPromptTemplate

from src.agents.base_agent import BaseAgent
from src.models.schemas import Architecture
from src.pipelines.state import SDLCState
from src.tools.llm_factory import LLMFactory

ARCHITECT_PROMPT = ChatPromptTemplate.from_messages([
    ('system',
     'You are a senior software architect. Given product requirements, design '
     'a minimal Python project: FastAPI + Pydantic + pytest. Keep it to 5-10 '
     'files MAX. Every file must have a clear, single purpose. Include a '
     'tests/ directory.'),
    ('human',
     'Requirements:\n{requirements}\n\n'
     'Previous feedback (if any): {feedback}\n\n'
     'Produce the structured Architecture object.')
])

class ArchitectAgent(BaseAgent):
    name = 'architect_agent'

    def __init__(self):
        super().__init__()
        self._chain = ARCHITECT_PROMPT | LLMFactory.get().with_structured_output(Architecture)

    def _process(self, state: SDLCState) -> dict:
        feedback = self._latest_feedback(state, 'architecture')
        result: Architecture = self._chain.invoke({
            'requirements': state['requirements'],
            'feedback': feedback or 'none'
        })
        self.logger.info(f'Architecture: {len(result.files)} files, '
                         f'stack={result.stack}')
        return {'architecture': result.model_dump(), 'status': 'architecture_designed'}
    
    @staticmethod
    def _latest_feedback(state: SDLCState, phase: str) -> str:
        relevant = [f for f in state.get('feedback', []) if f.get('phase') == phase]
        return relevant[-1].get('comment', '') if relevant else ''