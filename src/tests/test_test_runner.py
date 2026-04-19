import shutil
import uuid
from pathlib import Path

import src.models.schemas as schemas
import src.tools.test_runner as runner_mod


def _make_local_test_dir(prefix: str) -> Path:
    path = Path(".worktrees") / f"{prefix}_{uuid.uuid4().hex[:8]}"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_preflight_missing_requirements():
    test_dir = _make_local_test_dir("runner_req_missing")
    tests_dir = test_dir / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_api.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    report = runner_mod.TestRunner(test_dir).run()

    assert report.status == schemas.TestStatus.ERROR
    assert any("missing requirements.txt" in err for err in report.errors)
    shutil.rmtree(test_dir, ignore_errors=True)


def test_preflight_missing_tests():
    test_dir = _make_local_test_dir("runner_tests_missing")
    (test_dir / "requirements.txt").write_text("pytest>=8.0.0\n", encoding="utf-8")

    report = runner_mod.TestRunner(test_dir).run()

    assert report.status == schemas.TestStatus.ERROR
    assert any("no tests discovered" in err for err in report.errors)
    shutil.rmtree(test_dir, ignore_errors=True)
