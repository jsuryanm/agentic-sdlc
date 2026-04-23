import shutil
import sys
import subprocess
from pathlib import Path


def setup_test_env(project_dir: Path) -> Path:
    venv_dir = project_dir / "testenv"
    if venv_dir.exists():
        shutil.rmtree(venv_dir, ignore_errors=True)
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True
    )
    return venv_dir


def install_dependencies(venv_dir: Path, req_file: Path):
    python_executable = venv_dir / (
        "Scripts" if sys.platform == "win32" else "bin"
    ) / "python"

    # --- 1. Upgrade pip, setuptools, wheel (CRITICAL for Python 3.12) ---
    subprocess.run(
        [str(python_executable), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
        check=True,
        capture_output=True,
        text=True
    )

    # --- 2. Install project dependencies ---
    result = subprocess.run(
        [str(python_executable), "-m", "pip", "install", "-r", str(req_file)],
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"pip install failed (exit {result.returncode}):\n"
            f"{result.stdout[-1000:]}\n{result.stderr[-1000:]}"
        )

def run_pytest(venv_dir: Path, project_dir: Path):
    pytest_path = venv_dir / (
        "Scripts" if sys.platform == "win32" else "bin"
    ) / "pytest"

    # Fall back to the host interpreter if the venv pytest wasn't installed
    if not pytest_path.exists():
        cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short"]
    else:
        cmd = [str(pytest_path), "-q", "--tb=short"]

    return subprocess.run(
        cmd,
        cwd=str(project_dir),
        capture_output=True,
        text=True,
        timeout=90,
    )


def cleanup_env(venv_dir: Path):
    if venv_dir.exists():
        shutil.rmtree(venv_dir, ignore_errors=True)