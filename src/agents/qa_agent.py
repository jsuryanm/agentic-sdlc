import subprocess
from pathlib import Path
from typing import Any, Dict

from src.a2a import QA_CARD
from src.agents.base_agent import BaseAgent
from src.pipelines.context import ContextManager
from src.pipelines.state import SDLCState
from src.tools.test_runner import TestRunner


class QAAgent(BaseAgent):
    """Runs pytest against the generated codebase."""

    name = 'qa_agent'
    card = QA_CARD
    projection_fn = ContextManager.for_qa

    def _process(self, state: SDLCState, projection: Dict[str, Any]) -> dict:
        if not state.get('codebase'):
            return {
                'test_report': {
                    'status': 'fail',
                    'errors': ['Developer agent produced no codebase'],
                    'passed': 0,
                    'failed': 0,
                    'raw_output': '',
                },
                'qa_retries': 0,
                'status': 'qa_fail',
            }
        project_dir = Path(state['codebase']['project_dir'])
        runner = TestRunner(project_dir)

        self._install_deps(project_dir)

        report = runner.run()

        retries = state.get('qa_retries', 0) + (0 if report.status.value == 'pass' else 1)

        return {
            'test_report': report.model_dump(mode='json'),
            'qa_retries': retries,
            'status': f'qa_{report.status.value}',
        }

    def _install_deps(self, project_dir: Path) -> None:
        req = project_dir / 'requirements.txt'
        if not req.exists():
            return
        try:
            subprocess.run(
                ['pip', 'install', '-q', '-r', str(req)],
                timeout=120,
                capture_output=True,
                check=False,
            )
        except Exception as e:
            self.logger.warning(f'Dependencies installation failed (continuing): {e}')
