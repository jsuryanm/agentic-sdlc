from typing import List

from src.logger.custom_logger import logger
from src.memory.models import Lesson
from src.memory.store import LongTermMemory


def _format(lessons: List[Lesson]) -> str:
    if not lessons:
        return 'none'
    lines = []
    for i, lesson in enumerate(lessons, 1):
        marker = 'OK' if lesson.outcome == 'success' else 'WARN'
        lines.append(f'[{i}] {marker} ({lesson.category}) {lesson.content}')
    return '\n'.join(lines)


def _safe_search(query: str, category: str, k: int = 3) -> List[Lesson]:
    try:
        return LongTermMemory().search_lessons(query, k=k, category=category)
    except Exception as e:
        logger.bind(agent='recall').warning(
            f'Lesson recall failed (continuing with none): {e}'
        )
        return []


def recall_for_requirements(idea: str) -> str:
    return _format(_safe_search(idea, category='feedback'))


def recall_for_architect(requirements_summary: str) -> str:
    return _format(_safe_search(requirements_summary, category='architecture'))


def recall_for_developer(requirements_summary: str, stack: list[str]) -> str:
    stack_str = ', '.join(stack)
    query = f'{requirements_summary} stack: {stack_str}'
    return _format(_safe_search(query, category='code'))


def recall_for_qa(project_context: str) -> str:
    return _format(_safe_search(project_context, category='qa'))
