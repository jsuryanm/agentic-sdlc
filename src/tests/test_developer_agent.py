from src.agents.developer_agent import DeveloperAgent
from src.models.schemas import GeneratedFile


def test_apply_generation_contract_adds_requirements_and_tests():
    files = [
        GeneratedFile(
            path='app/main.py',
            content='from fastapi import FastAPI\napp = FastAPI()\n',
        )
    ]
    architecture = {
        'entry_point': 'uvicorn app.main:app',
        'files': [{'path': 'app/main.py', 'purpose': 'entrypoint'}],
    }

    repaired, notes = DeveloperAgent._apply_generation_contract(files, architecture)
    paths = {f.path for f in repaired}

    assert 'requirements.txt' in paths
    assert any(p.startswith('tests/test_') and p.endswith('.py') for p in paths)
    assert any('requirements.txt' in note for note in notes)
    assert any('pytest smoke test' in note for note in notes)


def test_apply_generation_contract_repairs_missing_entrypoint():
    files = [GeneratedFile(path='requirements.txt', content='pytest>=8.0.0\n')]
    architecture = {
        'entry_point': 'uvicorn app.main:app',
        'files': [],
    }

    repaired, notes = DeveloperAgent._apply_generation_contract(files, architecture)
    by_path = {f.path: f.content for f in repaired}

    assert 'app/main.py' in by_path
    assert 'FastAPI' in by_path['app/main.py']
    assert any("entrypoint file 'app/main.py'" in note for note in notes)


def test_entrypoint_to_path_basic():
    assert DeveloperAgent._entrypoint_to_path('uvicorn app.main:app') == 'app/main.py'
    assert DeveloperAgent._entrypoint_to_path('') == ''
    assert DeveloperAgent._entrypoint_to_path('python -m pkg.sub:main') == 'pkg/sub.py'


def test_entrypoint_to_path_strips_cli_flags():
    # Previous implementation wrote '--reload.py' because split()[-1] was '--reload'.
    assert DeveloperAgent._entrypoint_to_path(
        'uvicorn app.main:app --reload'
    ) == 'app/main.py'
    assert DeveloperAgent._entrypoint_to_path(
        'uvicorn --host 0.0.0.0 --port 8000 app.main:app'
    ) == 'app/main.py'
    assert DeveloperAgent._entrypoint_to_path('app.main:app') == 'app/main.py'


def test_entrypoint_to_path_returns_empty_on_garbage():
    assert DeveloperAgent._entrypoint_to_path('--reload --host 0.0.0.0') == ''
    assert DeveloperAgent._entrypoint_to_path('uvicorn') == ''


def test_is_safe_relpath():
    assert DeveloperAgent._is_safe_relpath('app/main.py')
    assert DeveloperAgent._is_safe_relpath('tests/test_routes.py')
    assert not DeveloperAgent._is_safe_relpath('--reload.py')
    assert not DeveloperAgent._is_safe_relpath('/etc/passwd')
    assert not DeveloperAgent._is_safe_relpath('../secrets.py')
    assert not DeveloperAgent._is_safe_relpath('app/../etc/passwd')
    assert not DeveloperAgent._is_safe_relpath('')
    assert not DeveloperAgent._is_safe_relpath('C:/windows/system32.py')
