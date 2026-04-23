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

    repaired, notes = DeveloperAgent._apply_generation_contract(
        files, architecture, pinned_versions=None
    )
    paths = {f.path for f in repaired}

    assert 'requirements.txt' in paths
    assert any(p.startswith('tests/test_') and p.endswith('.py') for p in paths)
    assert any('requirements.txt' in note for note in notes)
    assert any('pytest smoke test' in note for note in notes)


def test_apply_generation_contract_pins_versions_from_digest():
    pins = {'fastapi': '0.115.0', 'pydantic': '2.9.2'}
    repaired, _ = DeveloperAgent._apply_generation_contract(
        files=[], architecture={'entry_point': '', 'files': []},
        pinned_versions=pins,
    )
    req = next(f for f in repaired if f.path == 'requirements.txt').content
    assert 'fastapi==0.115.0' in req
    assert 'pydantic==2.9.2' in req


def test_extract_pinned_versions_parses_digest():
    digest = (
        '## fastapi\nCurrent version: fastapi==0.115.4\n\n'
        '## pydantic\nUse pydantic==2.9.2 syntax.'
    )
    pins = DeveloperAgent._extract_pinned_versions(digest)
    assert pins['fastapi'] == '0.115.4'
    assert pins['pydantic'] == '2.9.2'


def test_apply_generation_contract_repairs_missing_entrypoint():
    files = [GeneratedFile(path='requirements.txt', content='pytest>=8.0.0\n')]
    architecture = {
        'entry_point': 'uvicorn app.main:app',
        'files': [],
    }

    repaired, notes = DeveloperAgent._apply_generation_contract(
        files, architecture, pinned_versions=None
    )
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


def test_repair_pytest_fixtures_injects_missing_param():
    broken = '\n'.join([
        'import pytest',
        'from fastapi.testclient import TestClient',
        '',
        '@pytest.fixture',
        'def todo_data():',
        '    return {"title": "Test"}',
        '',
        'def test_create_todo(todo_data):',
        '    assert todo_data["title"] == "Test"',
        '',
        'def test_read_todo():',
        '    client.post("/todos/", json=todo_data)',
        '',
        'def test_delete_todo():',
        '    client.post("/todos/", json=todo_data)',
        '',
    ])
    files = [GeneratedFile(path='tests/test_routes.py', content=broken)]

    repaired, notes = DeveloperAgent._repair_pytest_fixtures(files)
    content = repaired[0].content

    # Already-correct test is untouched
    assert 'def test_create_todo(todo_data):' in content
    # Two broken tests got the fixture injected
    assert 'def test_read_todo(todo_data):' in content
    assert 'def test_delete_todo(todo_data):' in content
    assert len(notes) == 2
    assert all('test_routes.py' in n for n in notes)


def test_repair_pytest_fixtures_leaves_correct_files_alone():
    ok = '\n'.join([
        'import pytest',
        '',
        '@pytest.fixture',
        'def widget():',
        '    return 1',
        '',
        'def test_uses_widget(widget):',
        '    assert widget == 1',
        '',
    ])
    files = [GeneratedFile(path='tests/test_widget.py', content=ok)]
    repaired, notes = DeveloperAgent._repair_pytest_fixtures(files)
    assert notes == []
    # content should be byte-identical (no reparse)
    assert repaired[0].content == ok


def test_repair_pytest_fixtures_detects_called_fixture_decorator():
    """@pytest.fixture(scope='module') form must still register as a fixture."""
    src = '\n'.join([
        'import pytest',
        '',
        '@pytest.fixture(scope="module")',
        'def client():',
        '    return object()',
        '',
        'def test_ping():',
        '    assert client is not None',
        '',
    ])
    files = [GeneratedFile(path='tests/test_x.py', content=src)]
    repaired, notes = DeveloperAgent._repair_pytest_fixtures(files)
    assert 'def test_ping(client):' in repaired[0].content
    assert len(notes) == 1


def test_repair_test_runtime_deps_injects_pytest_asyncio():
    async_test = '\n'.join([
        'import pytest',
        'from fastapi.testclient import TestClient',
        '',
        '@pytest.mark.asyncio',
        'async def test_delete(todo_data):',
        '    assert todo_data',
        '',
    ])
    files = [
        GeneratedFile(
            path='requirements.txt',
            content='fastapi==0.115.0\npydantic==2.0.0\npytest==7.2.0\n',
        ),
        GeneratedFile(path='tests/test_routes.py', content=async_test),
    ]

    repaired, notes = DeveloperAgent._repair_test_runtime_deps(files)
    by_path = {f.path: f.content for f in repaired}

    # Packages are left unpinned so pip resolves against the installed pytest
    assert 'pytest-asyncio' in by_path['requirements.txt']
    # TestClient import in the same file → httpx too
    assert 'httpx' in by_path['requirements.txt']
    assert 'pytest.ini' in by_path
    assert 'asyncio_mode = auto' in by_path['pytest.ini']
    assert any('pytest-asyncio' in n for n in notes)


def test_repair_test_runtime_deps_injects_httpx_when_testclient_used():
    sync_test = '\n'.join([
        'from fastapi.testclient import TestClient',
        'from app.main import app',
        '',
        'client = TestClient(app)',
        '',
        'def test_health():',
        '    assert client.get("/health").status_code == 200',
        '',
    ])
    files = [
        GeneratedFile(path='requirements.txt', content='fastapi==0.115.0\npytest==7.2.0\n'),
        GeneratedFile(path='tests/test_x.py', content=sync_test),
    ]
    repaired, notes = DeveloperAgent._repair_test_runtime_deps(files)
    by_path = {f.path: f.content for f in repaired}

    assert 'httpx' in by_path['requirements.txt']
    # No async markers → no pytest.ini
    assert 'pytest.ini' not in by_path
    # No pytest-asyncio either (no async anywhere)
    assert 'pytest-asyncio' not in by_path['requirements.txt']


def test_repair_test_runtime_deps_idempotent_when_already_present():
    async_test = '\n'.join([
        'import pytest',
        '',
        '@pytest.mark.asyncio',
        'async def test_x():',
        '    pass',
        '',
    ])
    files = [
        GeneratedFile(
            path='requirements.txt',
            content='pytest==7.2.0\npytest-asyncio==0.23.8\nhttpx==0.27.2\n',
        ),
        GeneratedFile(
            path='pytest.ini',
            content='[pytest]\nasyncio_mode = auto\n',
        ),
        GeneratedFile(path='tests/test_x.py', content=async_test),
    ]
    repaired, notes = DeveloperAgent._repair_test_runtime_deps(files)
    assert notes == []
    # File set unchanged in content and membership
    assert {f.path for f in repaired} == {f.path for f in files}
    by_path = {f.path: f.content for f in repaired}
    assert by_path['requirements.txt'] == 'pytest==7.2.0\npytest-asyncio==0.23.8\nhttpx==0.27.2\n'


def test_augment_stack_with_test_libs_adds_missing_libs():
    out = DeveloperAgent._augment_stack_with_test_libs(['FastAPI', 'Pydantic'])
    # architect order preserved, then test libs appended
    assert out[:2] == ['FastAPI', 'Pydantic']
    for lib in ('pytest', 'pytest-asyncio', 'httpx'):
        assert lib in out


def test_augment_stack_with_test_libs_deduplicates_case_insensitive():
    # pytest is already in the stack under a weird case — must not appear twice
    out = DeveloperAgent._augment_stack_with_test_libs(['FastAPI', 'PyTest', 'httpx'])
    lowered = [x.lower() for x in out]
    assert lowered.count('pytest') == 1
    assert lowered.count('httpx') == 1
    # original casing wins when there's a conflict
    assert 'PyTest' in out
    assert 'pytest' not in out


def test_req_base_parses_common_specifiers():
    assert DeveloperAgent._req_base('fastapi==0.115.0') == 'fastapi'
    assert DeveloperAgent._req_base('uvicorn[standard]>=0.30') == 'uvicorn'
    assert DeveloperAgent._req_base('httpx~=0.27.0') == 'httpx'
    assert DeveloperAgent._req_base('# a comment') == ''
    assert DeveloperAgent._req_base('') == ''


def test_is_safe_relpath():
    assert DeveloperAgent._is_safe_relpath('app/main.py')
    assert DeveloperAgent._is_safe_relpath('tests/test_routes.py')
    assert not DeveloperAgent._is_safe_relpath('--reload.py')
    assert not DeveloperAgent._is_safe_relpath('/etc/passwd')
    assert not DeveloperAgent._is_safe_relpath('../secrets.py')
    assert not DeveloperAgent._is_safe_relpath('app/../etc/passwd')
    assert not DeveloperAgent._is_safe_relpath('')
    assert not DeveloperAgent._is_safe_relpath('C:/windows/system32.py')
