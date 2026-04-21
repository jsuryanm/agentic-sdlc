from langchain_core.prompts import ChatPromptTemplate
from src.agents.base_agent import BaseAgent
from src.models.schemas import Requirements
from src.pipelines.context import ContextManager
from src.pipelines.state import SDLCState
from src.tools.llm_factory import LLMFactory
from src.prompts.requirement_prompt import REQUIREMENT_PROMPT

from src.a2a import REQUIREMENTS_CARD
from typing import Any, Dict

class RequirementAgent(BaseAgent):
    name = 'requirement_agent'
    card = REQUIREMENTS_CARD
    projection_fn = ContextManager.for_requirements

    def __init__(self) -> None:
        super().__init__()
        self._chain = (
            REQUIREMENT_PROMPT
            | LLMFactory.get().with_structured_output(Requirements)
        )

    def _process(self, state: SDLCState, projection: Dict[str, Any]) -> dict:
        result: Requirements = self._chain.invoke({
            'idea': projection['idea'],
            'feedback': projection['prior_feedback'] or 'none'
        })
        self.logger.info(
            f'Requirements: {result.project_name}'
            f'({len(result.user_stories)}) stories'
        )
        return {
            'requirements': result.model_dump(),
            'status': 'requirements_drafted'
        }