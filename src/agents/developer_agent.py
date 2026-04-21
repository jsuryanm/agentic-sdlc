from pathlib import Path
from src.agents.base_agent import BaseAgent
from src.core.config import settings
from src.models.schemas import Codebase
from src.pipelines.state import SDLCState
from src.tools.llm_factory import LLMFactory
from src.prompts.developer_prompt import DEV_PROMPT

from typing import Any, Dict
from src.a2a import DEVELOPER_CARD
from src.knowledge import retrieve_for_developer
from src.memory.recall import recall_for_developer
from src.pipelines.context import ContextManager

class DeveloperAgent(BaseAgent):
    name = 'developer_agent'
    card = DEVELOPER_CARD
    projection_fn = ContextManager.for_developer

    def __init__(self):
        super().__init__()
        self._chain = (
            DEV_PROMPT 
            | LLMFactory.get(temperature=0.1).with_structured_output(Codebase)
        )

    def _process(self, state: SDLCState, projection: Dict[str, Any]) -> dict:
        arch = projection['architecture']

        docs_context = retrieve_for_developer(
            requirements_summary=projection['requirements_summary'],
            architecture = arch
        )

        past_lessons = recall_for_developer(
            requirements_summary=projection['requirements_summary'],
            stack=arch.get('stack', [])
        )

        result: Codebase = self._chain.invoke({
            'requirements_summary': projection['requirements_summary'],
            'architecture': arch,
            'qa_feedback': projection['qa_feedback'],
            'docs_context': docs_context,
            'past_lessons': past_lessons
        })

        project_name = (
            (state.get('requirements') or {}).get('project_name','sdlc_app')
        )
        project_dir = settings.WORKSPACE_DIR / project_name
        project_dir.mkdir(parents=True, exists_ok=True)

        for f in result.files:
            abs_path = project_dir / f.path
            abs_path.parent.mkdir(parents=True, exists_ok=True)
            abs_path.write_text(f.content, encoding='utf-8')

        self.logger.info(f'Wrote {len(result.files)} files to {project_dir}')
        return {
            'codebase': {
                **result.model_dump(),
                'project_dir': str(project_dir)
            },
            'status': 'code_generated'
        }