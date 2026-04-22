import subprocess
import sys
# runs external programs,executes system commands

from pathlib import Path

from src.exceptions.custom_exceptions import TestRunnerException
from src.logger.custom_logger import logger 
from src.models.schemas import TestReport,TestStatus 

class TestRunner:
    """Runs pytest in workspace (directory where the generated code exists) 
    and parses results into a TestReport"""

    def __init__(self, workspace: Path):
        self.workspace = workspace

    def run(self) -> TestReport:
        log = logger.bind(agent="qa")
        log.info(f"Running pytest in {self.workspace}")

        preflight_err = self._preflight()
        if preflight_err is not None:
            log.info(f"Test result: error ({preflight_err})")
            return TestReport(
                status=TestStatus.ERROR,
                passed=0,
                failed=0,
                errors=[preflight_err],
                raw_output=preflight_err,
            )

        try:
            result = subprocess.run(
                args=[sys.executable,"-m","pytest","-q","--tb=short"],
                cwd=str(self.workspace), # runs inside the workspace
                capture_output=True, # captures stdout and stderr
                text=True, # returns text
                timeout=90
            )

        except subprocess.TimeoutExpired:
            # prevents infinite test time
            raise TestRunnerException("pytest timed out after 90s")
        
        except Exception as e:
            raise TestRunnerException(f"pytest failed to start: {e}") from e
        
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        passed,failed = self._parse_counts(output)

        if result.returncode == 0:
            status = TestStatus.PASS
        
        elif failed > 0:
            status = TestStatus.FAIL
        
        else:
            status = TestStatus.ERROR

        report = TestReport(status=status,
                            passed=passed,
                            failed=failed,
                            errors=[output[-1500:]] if status != TestStatus.PASS else [],
                            raw_output=output[-4000:])
        log.info(f"Test result: {status.value} ({passed} passed, {failed} failed)")
        return report 
    
    def _preflight(self) -> "str | None":
        if not (self.workspace / "requirements.txt").exists():
            return f"missing requirements.txt in {self.workspace}"
        tests_dir = self.workspace / "tests"
        has_tests = False
        if tests_dir.exists():
            has_tests = any(tests_dir.glob("test_*.py"))
        if not has_tests:
            has_tests = any(self.workspace.glob("test_*.py"))
        if not has_tests:
            return f"no tests discovered in {self.workspace}"
        return None

    @staticmethod
    def _parse_counts(output: str) -> tuple[int,int]:
        import re
        passed, failed = 0, 0
        m = re.search(r"(\d+) passed", output)
        if m: passed = int(m.group(1))
        m = re.search(r"(\d+) failed", output)
        if m: failed = int(m.group(1))
        return passed, failed

        