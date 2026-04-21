from src.agents.base_agent import BaseAgent
from src.models.schemas import Architecture
from src.pipelines.state import SDLCState
from src.tools.llm_factory import LLMFactory
from src.prompts.architect_prompt import ARCHITECT_PROMPT

from typing import Any, Dict
from src.a2a import ARCHITECT_CARD
from src.memory.recall import recall_for_architect
from src.pipelines.context import ContextManager

class ArchitectAgent(BaseAgent):
    name = 'architect_agent'
    card = ARCHITECT_CARD
    projection_fn = ContextManager.for_architect

    def __init__(self) -> None:
        super().__init__()
        self._chain = (
            ARCHITECT_PROMPT 
            | LLMFactory.get().with_structured_output(Architecture)
        )

    def _process(self, state: SDLCState, projection: Dict[str, Any]) -> dict:
        reqs = projection['requirements']
        reqs_text = reqs.get('summary','') if isinstance(reqs, dict) else str(reqs)
        past_lessons = recall_for_architect(reqs_text)

        result: Architecture = self._chain.invoke({
            'requirements': projection['requirements'],
            'feedback': projection['prior_feedback'] or 'none',
            'past_lessons': past_lessons
        })
        self.logger.info(
            f'Architecture: {len(result.files)} files, stack={result.stack}'
        )
        return {
            'architecture': result.model_dump(),
            'status': 'architecture_designed'
        }