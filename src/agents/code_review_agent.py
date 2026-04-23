from typing import Any, Dict

from src.a2a import CODE_REVIEW_CARD
from src.agents.base_agent import BaseAgent
from src.models.schemas import CodeReview
from src.pipelines.context import ContextManager
from src.pipelines.state import SDLCState
from src.prompts.code_review_prompt import CODE_REVIEW_PROMPT
from src.tools.llm_factory import LLMFactory
from src.tools.mcp_client import fetch_docs_for_stack_sync


class CodeReviewAgent(BaseAgent):
    """Reviews the developer's generated code and requests fixes if needed."""

    name = 'code_review_agent'
    card = CODE_REVIEW_CARD
    projection_fn = ContextManager.for_code_review

    def __init__(self):
        super().__init__()
        self._chain = (
            CODE_REVIEW_PROMPT
            | LLMFactory.get(temperature=0.0).with_structured_output(CodeReview)
        )

    def _process(self, state: SDLCState, projection: Dict[str, Any]) -> dict:
        files = projection.get('files', [])
        if not files:
            review = CodeReview(
                passed=False,
                issues=[],
                required_fixes=['No files were generated; regenerate the codebase.'],
                notes='Developer produced an empty codebase.',
            )
        else:
            def _numbered(content: str) -> str:
                return '\n'.join(
                    f'{i:4d}  {line}'
                    for i, line in enumerate((content or '').splitlines(), start=1)
                )

            files_text = '\n\n'.join(
                f"--- {f['path']} ---\n{_numbered(f['content'])}" for f in files
            )
            stack = projection.get('stack') or []
            try:
                docs_context = fetch_docs_for_stack_sync(stack) or 'none'
            except Exception as e:
                self.logger.warning(f'Context7 fetch failed during review: {e}')
                docs_context = 'none'

            review = self._chain.invoke({
                'requirements_summary': projection['requirements_summary'],
                'architecture': projection['architecture'],
                'retry_attempt': projection.get('retry_attempt', 0),
                'docs_context': docs_context,
                'files': files_text,
            })

        retries = state.get('review_retries', 0)
        if not review.passed:
            retries += 1

        self.logger.info(
            f'Review: passed={review.passed}, '
            f'{len(review.issues)} issues, {len(review.required_fixes)} fixes'
        )

        return {
            'code_review': review.model_dump(mode='json'),
            'review_retries': retries,
            'status': 'review_passed' if review.passed else 'review_failed',
        }
