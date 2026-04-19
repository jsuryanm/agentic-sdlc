from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from src.agents.base_agent import BaseAgent
from src.core.config import settings
from src.models.schemas import Codebase
from src.pipelines.state import SDLCState
from src.tools.llm_factory import LLMFactory

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

class DeveloperAgent(BaseAgent):
    name = 'developer_agent'

    def __init__(self):
        super().__init__()
        llm = LLMFactory.get(temperature=0.1)
        self._chain = DEV_PROMPT | llm.with_structured_output(Codebase)

    def _process(self, state: SDLCState) -> dict:
        qa_feedback = self._build_qa_feedback(state)
        result: Codebase = self._chain.invoke({
            'requirements': state['requirements'],
            'architecture': state['architecture'],
            'qa_feedback': qa_feedback
        })

        project_name = state['requirements'].get('project_name', 'sdlc-app')
        project_dir = settings.WORKSPACE_DIR / project_name
        project_dir.mkdir(parents=True, exists_ok=True)

        for f in result.files:
            abs_path = project_dir / f.path
            abs_path.parent.mkdir(parents=True, exists_ok=True)
            abs_path.write_text(f.content, encoding='utf-8')

        self.logger.info(f'Wrote {len(result.files)} files to {project_dir}')
        return {
            'codebase': {**result.model_dump(), 'project_dir': str(project_dir)},
            'status': 'code_generated'
        }
    
    @staticmethod
    def _build_qa_feedback(state: SDLCState) -> str:
        report = state.get('test_report')
        if not report or report.get('status') == 'pass':
            return 'none'
        errors = '\n'.join(report.get('errors', []))
        return f'Tests FAILED. Fix these errors:\n{errors}'