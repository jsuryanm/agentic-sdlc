from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.logger.custom_logger import logger
from src.memory.models import Lesson
from src.tools.llm_factory import LLMFactory

class _ExtractedLesson(BaseModel):
    
    category: str = Field(
        description='One of: architecture, code, qa, feedback'
    )

    content: str = Field(
        description='The lesson, 1-3 sentences. Should be GENERIC enough '
                    'to apply to similar future projects, not specific to this one.'
    )

class _LessonBundle(BaseModel):
    lessons: List[_ExtractedLesson] = Field(
        description='2-5 lessons from this run, across different categories'
    )

_EXTRACTOR_SYSTEM = (
    "You are a software project post-mortem analyst. Given a completed project "
    "run (requirements, architecture, test outcome, human feedback), distill "
    "2-5 lessons that might help FUTURE similar projects. "
    "\n\n"
    "Rules for good lessons:\n"
    "  - Be GENERIC, not specific to this project's details\n"
    "  - Prefer patterns ('X tends to fail when Y') over facts ('X failed')\n"
    "  - Cover multiple categories: architecture, code, qa, feedback\n"
    "  - Skip boring/trivial observations\n"
    "  - If the run failed, lessons should be about what to AVOID\n"
    "  - If the run succeeded, lessons should be about what WORKED"
)

def extract_lessons(
        thread_id: str,
        final_state: Dict[str,Any],
        outcome: str
) -> List[Lesson]:
    log = logger.bind(agent='extractor')

    summary_parts = []
    if reqs := final_state.get('requirements'):
        summary_parts.append(f'Requirements: {reqs.get('summary', '')[:300]}')
    if arch := final_state.get('architecture'):
        summary_parts.append(
            f'Stack: {arch.get('stack')}, '
            f'Files: {len(arch.get('files',[]))}'
        )
    if report := final_state.get('test_report'):
        summary_parts.append(
            f'Tests: {report.get('status')} '
            f'(retries: {final_state.get('qa_retries', 0)}'
        )
    if feedback := final_state.get('feedback'):
        comments = [f.get('comment', '') for f in feedback if f.get('comment')]
        if comments:
            summary_parts.append(f'Human feedback: {'; '.join(comments[:3])}')

    run_summary = '\n'.join(summary_parts)

    try:
        llm = LLMFactory.get(temperature=0.2).with_structured_output(_LessonBundle)
        bundle: _LessonBundle = llm.invoke([
            SystemMessage(content=_EXTRACTOR_SYSTEM),
            HumanMessage(content=(
                f'Outcome: {outcome}\n\n'
                f'Run summary:\n{run_summary}\n\n'
                f'Extract lessons'
            ))
        ])
    except Exception as e:
        log.warning(f'Lesson extraction failed (continuing): {e}')
        return []
    
    lessons = [
        Lesson(
            thread_id=thread_id,
            category=ext.category,
            content=ext.content,
            outcome=outcome
        )
        for ext in bundle.lessons
    ]
    log.info(f'Extracted {len(lessons)} lessons from run {thread_id}')
    return lessons