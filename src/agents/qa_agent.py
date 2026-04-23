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
    cleanup_env
)


class QAAgent(BaseAgent):
    """Runs pytest against the generated codebase using an isolated test environment."""

    name = 'qa_agent'
    card = QA_CARD
    projection_fn = ContextManager.for_qa

    def _process(self, state: SDLCState, projection: Dict[str, Any]) -> dict:
        # --- 1. Safety check ---
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
        req = project_dir / "requirements.txt"

        # --- 2. Create isolated test environment ---
        venv_dir = setup_test_env(project_dir)

        try:
            # --- 3. Install dependencies ---
            if req.exists():
                install_dependencies(venv_dir, req)

            # --- 4. Run pytest inside env ---
            result = run_pytest(venv_dir, project_dir)

            output = (result.stdout or "") + "\n" + (result.stderr or "")

            # --- 5. Parse results ---
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
                important = [
                    l for l in lines
                    if ("ERROR" in l or "FAILED" in l or "Traceback" in l)
                ]
                errors = important[:5] if important else lines[-10:]
                
            report = TestReport(
                status=status,
                passed=passed,
                failed=failed,
                errors=errors,
                raw_output=output[-4000:]
            )

            if report.status.value != "pass":
                self.logger.warning(f"[QA FAILURE] status={report.status.value}"
                                    f"errors={report.errors[:2]}")

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
    # --- 6. Cleanup environment ---
            testenv_dir = project_dir / "testenv"

            try:
                if testenv_dir.exists():
                    import shutil
                    shutil.rmtree(testenv_dir, ignore_errors=True)
                    self.logger.info(f"Cleaned up testenv at {testenv_dir}")
            except Exception as e:
                self.logger.warning(f"testenv cleanup failed (non-fatal): {e}")

        # --- 7. Retry logic ---
        retries = state.get('qa_retries', 0) + (
            0 if report.status.value == 'pass' else 1
        )

        qa_summary = (
            f"Status: {report.status.value}\n"
            f"Passed: {report.passed},Failed:{report.failed}\n"
            f"Errors: \n" + "\n".join(report.errors[:3])
        )

        return {
            'test_report': report.model_dump(mode='json'),
            'qa_retries': retries,
            "qa_summary":qa_summary,
            'status': f'qa_{report.status.value}',
        }