from pathlib import Path
from typing import Any, Dict

from src.a2a import QA_CARD
from src.agents.base_agent import BaseAgent
from src.pipelines.context import ContextManager
from src.pipelines.state import SDLCState
from src.models.schemas import TestReport, TestStatus
from src.tools.test_runner import TestRunner

from src.tools.test_env import (
    setup_test_env,
    install_dependencies,
    run_pytest,
)


class QAAgent(BaseAgent):
    """Runs pytest against generated code in isolated env."""

    name = 'qa_agent'
    card = QA_CARD
    projection_fn = ContextManager.for_qa

    def _process(self, state: SDLCState, projection: Dict[str, Any]) -> dict:
        if not state.get('codebase'):
            return {
                'test_report': {
                    'status': 'fail',
                    'errors': ['No codebase generated'],
                    'passed': 0,
                    'failed': 0,
                    'raw_output': '',
                },
                'qa_retries': min(state.get('qa_retries', 0), 2),
                'status': 'qa_fail',
            }

        project_dir = Path(state['codebase']['project_dir'])
        req = project_dir / "requirements.txt"

        venv_dir = setup_test_env(project_dir)

        try:
            if req.exists():
                install_dependencies(venv_dir, req)

            result = run_pytest(venv_dir, project_dir)
            output = (result.stdout or "") + "\n" + (result.stderr or "")

            passed, failed = TestRunner._parse_counts(output)

            if "ERROR" in output:
                status = TestStatus.ERROR
            elif result.returncode == 0:
                status = TestStatus.PASS
            elif failed > 0:
                status = TestStatus.FAIL
            else:
                status = TestStatus.ERROR

            errors = []
            if status != TestStatus.PASS:
                lines = output.splitlines()
                errors = [
                    l for l in lines
                    if "ERROR" in l or "FAILED" in l or "Traceback" in l
                ][:5] or lines[-10:]

            report = TestReport(
                status=status,
                passed=passed,
                failed=failed,
                errors=errors,
                raw_output=output[-4000:],
            )

        except Exception as e:
            self.logger.exception(f"QA execution failed: {e}")

            report = TestReport(
                status=TestStatus.ERROR,
                passed=0,
                failed=0,
                errors=[str(e)],
                raw_output="",
            )

        finally:
            testenv_dir = project_dir / "testenv"
            try:
                import shutil
                if testenv_dir.exists():
                    shutil.rmtree(testenv_dir, ignore_errors=True)
            except Exception as e:
                self.logger.warning(f"cleanup failed: {e}")

        # -------------------------
        # HARD RETRY ENFORCEMENT
        # -------------------------
        prev_retries = state.get('qa_retries', 0)

        retries = prev_retries
        if report.status.value != 'pass':
            retries += 1

        retries = min(retries, 2)

        locks = state.get("locks", {})
        if retries >= 2:
            locks["qa"] = True

        qa_summary = (
            f"Status: {report.status.value}\n"
            f"Passed: {report.passed}, Failed: {report.failed}\n"
            f"Errors:\n" + "\n".join(report.errors[:3])
        )

        return {
            'test_report': report.model_dump(mode='json'),
            'qa_retries': retries,
            'locks': locks,
            'qa_summary': qa_summary,
            'status': f'qa_{report.status.value}',
        }