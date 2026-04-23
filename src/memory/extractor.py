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
    "You are a senior software engineer performing a post-mortem on an automated SDLC run.\n\n"

    "Your goal is to extract 2–5 HIGH-VALUE lessons that help future agents FIX similar issues.\n\n"

    "IMPORTANT:\n"
    "- Lessons must be GENERALIZABLE but also ACTIONABLE\n"
    "- Each lesson should describe:\n"
    "    (1) the failure pattern\n"
    "    (2) the root cause\n"
    "    (3) the concrete fix\n\n"

    "GOOD examples:\n"
    "- 'Pytest fixture errors occur when fixtures are not passed as function arguments → fix by adding the fixture parameter explicitly.'\n"
    "- 'ModuleNotFoundError happens when dependencies are missing → fix by adding the package to requirements.txt.'\n"
    "- 'FastAPI response validation fails when response_model mismatches → fix by aligning schema with returned object.'\n\n"

    "BAD examples:\n"
    "- 'Tests failed'\n"
    "- 'There were errors in the code'\n"
    "- 'Fix the bug'\n\n"

    "Rules:\n"
    "- Be concise (1–2 sentences per lesson)\n"
    "- Prefer patterns over one-off facts\n"
    "- Include concrete fixes (what to change)\n"
    "- Focus on issues that are likely to repeat\n"
    "- Cover multiple categories when possible (architecture, code, qa, feedback)\n\n"

    "If the run failed:\n"
    "- Focus on what to AVOID and how to FIX it\n\n"

    "If the run succeeded:\n"
    "- Focus on what WORKED and why\n\n"

    "Output only structured lessons."
)

def extract_lessons(
        thread_id: str,
        final_state: Dict[str, Any],
        outcome: str
) -> List[Lesson]:
    log = logger.bind(agent='extractor')

    summary_parts = []

    if reqs := final_state.get('requirements'):
        summary_parts.append(
            f"Requirements: {reqs.get('summary', '')[:300]}"
        )

    if arch := final_state.get('architecture'):
        summary_parts.append(
            f"Stack: {arch.get('stack')}, "
            f"Files: {len(arch.get('files', []))}"
        )

    if report := final_state.get('test_report'):
        errors = report.get("errors", [])[:3]

        summary_parts.append(
            f"Test status: {report.get('status')}\n"
            f"Errors:\n" + "\n".join(errors)
        )

    if feedback := final_state.get('feedback'):
        comments = [f.get('comment', '') for f in feedback if f.get('comment')]
        if comments:
            summary_parts.append(
                f"Human feedback: {'; '.join(comments[:3])}"
            )

    run_summary = '\n'.join(summary_parts)

    try:
        llm = LLMFactory.get(temperature=0.2).with_structured_output(_LessonBundle)
        bundle: _LessonBundle = llm.invoke([
            SystemMessage(content=_EXTRACTOR_SYSTEM),
            HumanMessage(content=(
                f"Outcome: {outcome}\n\n"
                f"Run summary:\n{run_summary}\n\n"
                f"Extract lessons"
            ))
        ])
    except Exception as e:
        log.warning(f'Lesson extraction failed (continuing): {e}')
        return []

    lessons = []

    for ext in bundle.lessons:
        content = ext.content.strip().lower()

        # --- classify ---
        if "fixture" in content:
            tag = "[PYTEST_FIX]"
        elif "import" in content or "module not found" in content:
            tag = "[IMPORT_FIX]"
        elif "dependency" in content or "requirements" in content:
            tag = "[DEPENDENCY_FIX]"
        elif "assert" in content or "test" in content:
            tag = "[TEST_FIX]"
        else:
            tag = "[GENERAL_FIX]"

        lessons.append(
            Lesson(
                thread_id=thread_id,
                category=ext.category,
                content=f"{tag} {ext.content.strip()}",
                outcome=outcome
            )
        )

    log.info(f'Extracted {len(lessons)} lessons from run {thread_id}')
    return lessons