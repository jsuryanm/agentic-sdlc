import json
from pathlib import Path
from typing import Any, Dict, List

import markdown as md_lib
from fpdf import FPDF

from src.a2a import DOC_CARD
from src.agents.base_agent import BaseAgent
from src.core.config import settings
from src.models.schemas import PhaseDocument
from src.pipelines.context import ContextManager
from src.pipelines.state import SDLCState
from src.prompts.doc_prompt import DOC_PROMPT
from src.tools.llm_factory import LLMFactory


def _render_pdf(markdown_text: str, out_path: Path) -> None:
    html = md_lib.markdown(markdown_text, extensions=['extra'])
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font('Helvetica', size=11)
    pdf.write_html(html)
    pdf.output(str(out_path))

PHASE_TITLES = {
    'requirements': 'Requirements',
    'architecture': 'Architecture',
    'developer': 'Development',
    'qa': 'Quality Assurance',
    'devops': 'DevOps',
}


class DocAgent(BaseAgent):
    """Generates a Markdown report for one SDLC phase.

    When the project directory is known (from the developer phase onward), the
    report is written directly to ``<project_dir>/docs/<phase>.md``. For earlier
    phases the content is buffered in ``state['docs']`` and flushed to disk by
    the first DocAgent instance that sees a project_dir.
    """

    card = DOC_CARD

    def __init__(self, phase: str):
        if phase not in PHASE_TITLES:
            raise ValueError(f'Unknown doc phase: {phase}')
        self.phase = phase
        self.name = f'doc_{phase}_agent'
        self.projection_fn = ContextManager.for_doc(phase)
        super().__init__()
        self._chain = (
            DOC_PROMPT
            | LLMFactory.get(temperature=0.2).with_structured_output(PhaseDocument)
        )

    def _process(self, state: SDLCState, projection: Dict[str, Any]) -> dict:
        artifact = projection.get('artifact') or {}
        project_name = projection.get('project_name') or 'sdlc_app'
        project_dir = projection.get('project_dir')

        try:
            artifact_json = json.dumps(artifact, indent=2, default=str)[:6000]
        except Exception:
            artifact_json = str(artifact)[:6000]

        doc: PhaseDocument = self._chain.invoke({
            'phase': self.phase,
            'phase_title': PHASE_TITLES[self.phase],
            'project_name': project_name,
            'summary': projection.get('summary') or '',
            'artifact_json': artifact_json,
        })

        entry = {
            'phase': self.phase,
            'title': doc.title,
            'summary': doc.summary,
            'content_markdown': doc.content_markdown,
            'path': None,
            'pdf_path': None,
        }

        pending_entries: List[dict] = []
        new_entry = entry

        if project_dir:
            docs_root = Path(project_dir) / 'docs'
            docs_root.mkdir(parents=True, exist_ok=True)
            # Flush any buffered earlier-phase entries first.
            for buffered in state.get('docs', []) or []:
                if buffered.get('path'):
                    continue
                phase_key = buffered.get('phase', 'report')
                target = docs_root / f'{phase_key}.md'
                pdf_target = docs_root / f'{phase_key}.pdf'
                md_text = buffered.get('content_markdown', '')
                target.write_text(md_text, encoding='utf-8')
                try:
                    _render_pdf(md_text, pdf_target)
                    pdf_str = str(pdf_target)
                except Exception as e:
                    self.logger.warning(f'PDF render failed for {phase_key}: {e}')
                    pdf_str = None
                pending_entries.append({
                    **buffered, 'path': str(target), 'pdf_path': pdf_str,
                })
            own_target = docs_root / f'{self.phase}.md'
            own_pdf = docs_root / f'{self.phase}.pdf'
            own_target.write_text(doc.content_markdown, encoding='utf-8')
            try:
                _render_pdf(doc.content_markdown, own_pdf)
                own_pdf_str = str(own_pdf)
            except Exception as e:
                self.logger.warning(f'PDF render failed for {self.phase}: {e}')
                own_pdf_str = None
            new_entry = {**entry, 'path': str(own_target), 'pdf_path': own_pdf_str}
            self.logger.info(f'Wrote {self.phase} doc to {own_target} (+ pdf)')
        else:
            self.logger.info(
                f'project_dir not yet known; buffering {self.phase} doc'
            )

        docs_update = pending_entries + [new_entry]

        return {
            'docs': docs_update,
            'status': f'doc_{self.phase}_written',
        }
