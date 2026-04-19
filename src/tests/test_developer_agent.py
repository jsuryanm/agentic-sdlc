from src.agents.developer_agent import DeveloperAgent
from src.models.schemas import GeneratedFile


def test_apply_generation_contract_adds_requirements_and_tests():
    files = [GeneratedFile(path="app/main.py", content="from fastapi import FastAPI\napp = FastAPI()\n")]
    architecture = {
        "entry_point": "uvicorn app.main:app",
        "files": [{"path": "app/main.py", "purpose": "entrypoint"}],
    }

    repaired, notes = DeveloperAgent._apply_generation_contract(files, architecture)
    paths = {f.path for f in repaired}

    assert "requirements.txt" in paths
    assert any(p.startswith("tests/test_") and p.endswith(".py") for p in paths)
    assert any("requirements.txt" in note for note in notes)
    assert any("pytest smoke test" in note for note in notes)


def test_apply_generation_contract_repairs_missing_entrypoint():
    files = [GeneratedFile(path="requirements.txt", content="pytest>=8.0.0\n")]
    architecture = {
        "entry_point": "uvicorn app.main:app",
        "files": [],
    }

    repaired, notes = DeveloperAgent._apply_generation_contract(files, architecture)
    by_path = {f.path: f.content for f in repaired}

    assert "app/main.py" in by_path
    assert "FastAPI" in by_path["app/main.py"]
    assert any("entrypoint file 'app/main.py'" in note for note in notes)
