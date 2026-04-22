import ast
from pathlib import PurePosixPath, Path
from typing import Any, Dict, List, Tuple

from src.a2a import DEVELOPER_CARD
from src.agents.base_agent import BaseAgent
from src.core.config import settings
from src.knowledge import retrieve_for_developer
from src.memory.recall import recall_for_developer
from src.models.schemas import Codebase, GeneratedFile
from src.pipelines.context import ContextManager
from src.pipelines.state import SDLCState
from src.prompts.developer_prompt import DEV_PROMPT
from src.tools.llm_factory import LLMFactory


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

        docs_context = retrieve_for_developer(
            requirements_summary=projection['requirements_summary'],
            architecture=arch
        )

        past_lessons = recall_for_developer(
            requirements_summary=projection['requirements_summary'],
            stack=arch.get('stack', [])
        )

        result: Codebase = self._chain.invoke({
            'requirements_summary': projection['requirements_summary'],
            'architecture': arch,
            'qa_feedback': projection.get('qa_feedback', 'none'),
            'review_feedback': projection.get('review_feedback', 'none'),
            'docs_context': docs_context,
            'past_lessons': past_lessons,
        })

        repaired_files, contract_notes = self._apply_generation_contract(
            result.files, arch
        )

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

    @staticmethod
    def _apply_generation_contract(
        files: List[GeneratedFile], architecture: dict
    ) -> Tuple[List[GeneratedFile], List[str]]:
        """Ensures the generated project always includes the minimum pieces QA
        needs: a requirements.txt, at least one pytest test, and the entry-point
        file declared in the architecture."""
        notes: List[str] = []
        by_path = {f.path: f for f in files}

        if 'requirements.txt' not in by_path:
            by_path['requirements.txt'] = GeneratedFile(
                path='requirements.txt',
                content='fastapi\nuvicorn[standard]\npydantic\npytest\nhttpx\n'
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
            # must look module-ish: a dot-separated Python identifier chain
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
