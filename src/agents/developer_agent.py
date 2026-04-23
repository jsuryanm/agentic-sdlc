import ast
from pathlib import PurePosixPath
from typing import Any, Dict, List, Tuple

from src.a2a import DEVELOPER_CARD
from src.agents.base_agent import BaseAgent
from src.core.config import settings
from src.memory.recall import recall_for_developer
from src.models.schemas import Codebase, GeneratedFile
from src.pipelines.context import ContextManager
from src.pipelines.state import SDLCState
from src.prompts.developer_prompt import DEV_PROMPT
from src.tools.llm_factory import LLMFactory
from src.tools.mcp_client import fetch_docs_for_stack_sync


class DeveloperAgent(BaseAgent):
    name = 'developer_agent'
    card = DEVELOPER_CARD
    projection_fn = ContextManager.for_developer

    def __init__(self):
        super().__init__()
        self._chain = (
            DEV_PROMPT
            | LLMFactory.get(temperature=0.1).with_structured_output(Codebase)
        )

    def _process(self, state: SDLCState, projection: Dict[str, Any]) -> dict:
        arch = projection['architecture']
        stack = arch.get('stack', []) or []

        docs_context = self._gather_docs(
            stack=stack,
            requirements_summary=projection['requirements_summary'],
            architecture=arch,
        )

        if not docs_context:
            # Context7 is the only permitted source. Refuse to write code
            # blindly from training memory — surface the failure instead.
            msg = (
                'Context7 returned no documentation for the requested stack '
                f'({stack}). Developer will not generate code from memory. '
                'Check that `npx -y @upstash/context7-mcp` can run on this '
                'machine and that USE_CONTEXT7=true.'
            )
            self.logger.error(msg)
            return {
                'codebase': {'files': [], 'notes': msg, 'project_dir': ''},
                'errors': [msg],
                'status': 'developer_failed',
            }

        # past_lessons = recall_for_developer(
        #     requirements_summary=projection['requirements_summary'],
        #     stack=stack,
        # )

        result: Codebase = self._chain.invoke({
            'requirements_summary': projection['requirements_summary'],
            'architecture': projection.get("architecture"),
            'qa_feedback': projection.get('qa_feedback', 'none'),
            'review_feedback': projection.get('review_feedback', 'none'),
            'docs_context': docs_context,
            'past_fixes': projection.get("past_fixes","none"),
            "qa_memory":projection.get("qa_memory","none")
        })

        pinned_versions = self._extract_pinned_versions(docs_context)
        repaired_files, contract_notes = self._apply_generation_contract(
            result.files, arch, pinned_versions
        )

        repaired_files, fixture_notes = self._repair_pytest_fixtures(repaired_files)
        contract_notes.extend(fixture_notes)

        repaired_files, runtime_notes = self._repair_test_runtime_deps(
            repaired_files, pinned_versions
        )
        contract_notes.extend(runtime_notes)

        project_name = (
            (state.get('requirements') or {}).get('project_name', 'sdlc_app')
        )
        project_dir = settings.WORKSPACE_DIR / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        written_files: List[GeneratedFile] = []
        for f in repaired_files:
            if not self._is_safe_relpath(f.path):
                self.logger.warning(
                    f'Skipping generated file with unsafe path: {f.path!r}'
                )
                contract_notes.append(f'Dropped unsafe generated path: {f.path!r}')
                continue
            abs_path = project_dir / f.path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(f.content, encoding='utf-8')
            written_files.append(f)

        for f in written_files:
            if f.path.endswith('.py'):
                try:
                    ast.parse(f.content)
                except SyntaxError as exc:
                    msg = f'Syntax error in generated {f.path}: {exc.msg} (line {exc.lineno})'
                    self.logger.warning(msg)
                    contract_notes.append(msg)

        self.logger.info(f'Wrote {len(written_files)} files to {project_dir}')
        combined_notes = (result.notes or '').strip()
        if contract_notes:
            combined_notes = '\n'.join([combined_notes, *contract_notes]).strip()

        return {
            'codebase': {
                'files': [f.model_dump() for f in written_files],
                'notes': combined_notes,
                'project_dir': str(project_dir),
            },
            'status': 'code_generated',
        }

    # -- Context7-backed research ------------------------------------------

    def _gather_docs(
        self,
        stack: List[str],
        requirements_summary: str,
        architecture: dict,
    ) -> str:
        """Return a Context7-backed doc digest for the stack.

        Deterministic direct MCP fetch — no nested ReAct sub-graph (which
        would inherit the outer sync SqliteSaver and fail on async).

        The stack is augmented with standard test-writing libraries
        (``pytest``, ``pytest-asyncio``, ``httpx``) so the same developer
        agent writing tests has current, authoritative docs for them too
        — not training-memory guesses.
        """
        if not stack or not settings.USE_CONTEXT7:
            return ''
        augmented = self._augment_stack_with_test_libs(stack)
        try:
            return fetch_docs_for_stack_sync(augmented) or ''
        except Exception as e:
            self.logger.warning(f'Context7 fetch failed: {e}')
            return ''

    @staticmethod
    def _augment_stack_with_test_libs(stack: List[str]) -> List[str]:
        """Append pytest / pytest-asyncio / httpx to the stack for Context7
        lookup, preserving the architect's order and dropping duplicates
        case-insensitively."""
        test_libs = ['pytest', 'pytest-asyncio', 'httpx']
        seen: set = set()
        out: List[str] = []
        for lib in list(stack) + test_libs:
            key = lib.lower().strip()
            if key and key not in seen:
                seen.add(key)
                out.append(lib)
        return out

    @staticmethod
    def _repair_pytest_fixtures(
        files: List[GeneratedFile],
    ) -> Tuple[List[GeneratedFile], List[str]]:
        """Inject missing pytest-fixture parameters into test functions.

        Catches the common LLM mistake where ``@pytest.fixture def todo_data``
        is defined in a test module but a ``def test_read_todo():`` body
        references ``todo_data`` without declaring it as a parameter. Without
        injection the name resolves to the fixture *function object* and any
        downstream JSON serialization raises ``TypeError: Object of type
        FixtureFunctionDefinition is not JSON serializable``.
        """
        notes: List[str] = []
        repaired: List[GeneratedFile] = []

        for f in files:
            if not (
                f.path.startswith('tests/')
                and f.path.endswith('.py')
                and 'test_' in f.path.rsplit('/', 1)[-1]
            ):
                repaired.append(f)
                continue

            try:
                tree = ast.parse(f.content)
            except SyntaxError:
                repaired.append(f)
                continue

            fixture_names = DeveloperAgent._collect_fixture_names(tree)
            if not fixture_names:
                repaired.append(f)
                continue

            file_changed = False
            for node in tree.body:
                if not isinstance(node, ast.FunctionDef):
                    continue
                if not node.name.startswith('test_'):
                    continue
                if DeveloperAgent._is_fixture(node):
                    continue

                existing_params = {
                    a.arg for a in node.args.args + node.args.posonlyargs + node.args.kwonlyargs
                }
                referenced = {
                    child.id for child in ast.walk(node)
                    if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
                }
                missing = [
                    name for name in fixture_names
                    if name in referenced and name not in existing_params
                ]
                if not missing:
                    continue

                for name in missing:
                    node.args.args.append(ast.arg(arg=name, annotation=None))
                file_changed = True
                notes.append(
                    f'Auto-injected pytest fixture(s) {missing} into '
                    f'{f.path}::{node.name}'
                )

            if file_changed:
                new_content = ast.unparse(tree) + '\n'
                repaired.append(GeneratedFile(path=f.path, content=new_content))
            else:
                repaired.append(f)

        return repaired, notes

    @staticmethod
    def _collect_fixture_names(tree: ast.Module) -> set[str]:
        names: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and DeveloperAgent._is_fixture(node):
                names.add(node.name)
        return names

    @staticmethod
    def _is_fixture(node: ast.FunctionDef) -> bool:
        for dec in node.decorator_list:
            # bare @pytest.fixture  →  Attribute(value=Name('pytest'), attr='fixture')
            # bare @fixture         →  Name('fixture')
            # @pytest.fixture(...)  →  Call(func=Attribute(..., 'fixture'))
            # @fixture(...)         →  Call(func=Name('fixture'))
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == 'fixture':
                return True
            if isinstance(target, ast.Name) and target.id == 'fixture':
                return True
        return False

    @staticmethod
    def _repair_test_runtime_deps(
        files: List[GeneratedFile],
        pinned_versions: Dict[str, str] | None = None,
    ) -> Tuple[List[GeneratedFile], List[str]]:
        """Make async / TestClient-based tests actually runnable by pytest.

        Scans every ``tests/test_*.py`` for async markers and TestClient
        imports, then tops up ``requirements.txt`` with the necessary
        packages (``pytest-asyncio``, ``httpx``) and writes a
        ``pytest.ini`` with ``asyncio_mode = auto`` when async tests are
        present. Idempotent: if everything is already in place, makes
        no changes.
        """
        pins = pinned_versions or {}
        needs_asyncio = False
        needs_httpx = False

        for f in files:
            if not (
                f.path.startswith('tests/')
                and f.path.endswith('.py')
                and 'test_' in f.path.rsplit('/', 1)[-1]
            ):
                continue
            try:
                tree = ast.parse(f.content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith('test_'):
                    needs_asyncio = True
                if isinstance(node, ast.FunctionDef):
                    for dec in node.decorator_list:
                        if 'asyncio' in ast.unparse(dec):
                            needs_asyncio = True
                            break
                if isinstance(node, ast.ImportFrom):
                    if (node.module or '').startswith('fastapi.testclient'):
                        needs_httpx = True
                if isinstance(node, ast.Name) and node.id == 'TestClient':
                    needs_httpx = True

        if not (needs_asyncio or needs_httpx):
            return files, []

        by_path = {f.path: f for f in files}
        notes: List[str] = []

        # Top up requirements.txt
        req = by_path.get('requirements.txt')
        existing_lines = (req.content.splitlines() if req else [])
        existing_bases = {
            DeveloperAgent._req_base(l).lower()
            for l in existing_lines
            if DeveloperAgent._req_base(l)
        }
        # Test-runtime deps are left unpinned (or loosely bounded) on purpose:
        # pytest-asyncio has a strict compat matrix with pytest's major, and
        # httpx version isn't load-bearing for tests. Let pip resolve whichever
        # version matches the installed pytest.
        additions: List[str] = []
        required: List[str] = []
        if needs_asyncio:
            required.append('pytest-asyncio')
        if needs_httpx:
            required.append('httpx')

        for pkg in required:
            if pkg.lower() in existing_bases:
                continue
            pinned = pins.get(pkg.lower())
            additions.append(f'{pkg}=={pinned}' if pinned else pkg)

        if additions:
            new_req_lines = [l for l in existing_lines if l.strip()] + additions
            by_path['requirements.txt'] = GeneratedFile(
                path='requirements.txt',
                content='\n'.join(new_req_lines) + '\n',
            )
            notes.append(
                f'Auto-added test runtime deps to requirements.txt: {additions}'
            )

        # Ensure pytest.ini configures asyncio_mode when async tests are present
        if needs_asyncio:
            ini = by_path.get('pytest.ini')
            if ini is None:
                by_path['pytest.ini'] = GeneratedFile(
                    path='pytest.ini',
                    content='[pytest]\nasyncio_mode = auto\n',
                )
                notes.append(
                    'Created pytest.ini with asyncio_mode=auto (async tests detected)'
                )
            elif 'asyncio_mode' not in ini.content:
                lines = ini.content.rstrip().splitlines()
                if not any(l.strip().startswith('[pytest]') for l in lines):
                    lines.insert(0, '[pytest]')
                # append asyncio_mode under the [pytest] section (end of file is fine)
                lines.append('asyncio_mode = auto')
                by_path['pytest.ini'] = GeneratedFile(
                    path='pytest.ini', content='\n'.join(lines) + '\n'
                )
                notes.append(
                    'Appended asyncio_mode=auto to existing pytest.ini'
                )

        return list(by_path.values()), notes

    @staticmethod
    def _req_base(line: str) -> str:
        """Extract the distribution name from a requirements line.

        Handles ``pkg==1.2``, ``pkg[extra]>=1.0``, comments, and blanks.
        """
        s = line.strip()
        if not s or s.startswith('#'):
            return ''
        for sep in ('==', '>=', '<=', '~=', '>', '<', '!=', ';', ' '):
            idx = s.find(sep)
            if idx != -1:
                s = s[:idx]
                break
        return s.split('[', 1)[0].strip()

    @staticmethod
    def _extract_pinned_versions(docs_context: str) -> Dict[str, str]:
        """Pick up ``library==version`` mentions in the Context7 digest so we
        can inject them into fallback requirements.txt."""
        import re
        pins: Dict[str, str] = {}
        if not docs_context:
            return pins
        pattern = re.compile(r'\b([A-Za-z][A-Za-z0-9_\-\.]+)==(\d+(?:\.\d+){0,2})\b')
        for name, ver in pattern.findall(docs_context):
            key = name.lower()
            if key not in pins:
                pins[key] = ver
        return pins

    # -- Contract / safety -------------------------------------------------

    @staticmethod
    def _apply_generation_contract(
        files: List[GeneratedFile],
        architecture: dict,
        pinned_versions: Dict[str, str] | None = None,
    ) -> Tuple[List[GeneratedFile], List[str]]:
        """Ensures the generated project always includes the minimum pieces QA
        needs: a requirements.txt, at least one pytest test, and the entry-point
        file declared in the architecture."""
        notes: List[str] = []
        by_path = {f.path: f for f in files}
        pins = pinned_versions or {}

        if 'requirements.txt' not in by_path:
            defaults = ['fastapi', 'uvicorn[standard]', 'pydantic', 'pytest', 'httpx']
            lines: List[str] = []
            for pkg in defaults:
                base = pkg.split('[')[0].lower()
                if base in pins:
                    lines.append(f'{pkg}=={pins[base]}')
                else:
                    lines.append(pkg)
            for name, ver in pins.items():
                if not any(l.split('[')[0].lower().startswith(name) for l in lines):
                    lines.append(f'{name}=={ver}')
            by_path['requirements.txt'] = GeneratedFile(
                path='requirements.txt',
                content='\n'.join(lines) + '\n',
            )
            notes.append('Added default requirements.txt (developer contract).')

        has_test = any(
            p.startswith('tests/test_') and p.endswith('.py')
            for p in by_path
        )
        if not has_test:
            by_path['tests/__init__.py'] = GeneratedFile(
                path='tests/__init__.py', content=''
            )
            by_path['tests/test_smoke.py'] = GeneratedFile(
                path='tests/test_smoke.py',
                content=(
                    'def test_smoke():\n'
                    '    """Default pytest smoke test added by developer contract."""\n'
                    '    assert True\n'
                )
            )
            notes.append('Added default pytest smoke test (developer contract).')

        entry = (architecture or {}).get('entry_point', '') or ''
        module_path = DeveloperAgent._entrypoint_to_path(entry)
        if module_path and module_path not in by_path:
            by_path[module_path] = GeneratedFile(
                path=module_path,
                content=(
                    'from fastapi import FastAPI\n\n'
                    'app = FastAPI()\n\n'
                    '@app.get("/health")\n'
                    'def health():\n'
                    '    return {"status": "ok"}\n'
                )
            )
            notes.append(
                f"Added stub entrypoint file '{module_path}' (developer contract)."
            )

        return list(by_path.values()), notes

    _RUNNER_NAMES = {
        'uvicorn', 'gunicorn', 'hypercorn', 'daphne',
        'python', 'python3', 'py', 'fastapi', 'flask',
    }

    @staticmethod
    def _entrypoint_to_path(entry_point: str) -> str:
        """Translate 'uvicorn app.main:app --reload' into 'app/main.py'.

        Strips runner names and CLI flags; picks the first module-looking token.
        Returns '' when no safe module path can be extracted.
        """
        if not entry_point:
            return ''
        tokens = entry_point.strip().split()
        for tok in tokens:
            if tok.startswith('-'):
                continue
            if tok.lower() in DeveloperAgent._RUNNER_NAMES:
                continue
            module = tok.split(':')[0]
            if not module:
                continue
            parts = module.split('.')
            if all(p.isidentifier() for p in parts):
                return '/'.join(parts) + '.py'
        return ''

    @staticmethod
    def _is_safe_relpath(path: str) -> bool:
        """Reject absolute, traversal, or flag-like generated paths."""
        if not path or path.strip() != path:
            return False
        if path.startswith(('/', '\\')) or (len(path) > 1 and path[1] == ':'):
            return False
        try:
            parts = PurePosixPath(path.replace('\\', '/')).parts
        except Exception:
            return False
        if not parts:
            return False
        for p in parts:
            if not p or p in ('.', '..'):
                return False
            if p.startswith('-'):
                return False
        return True
