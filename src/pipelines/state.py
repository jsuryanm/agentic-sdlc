from operator import add
from typing import Annotated, List, Optional
from typing_extensions import TypedDict


class SDLCState(TypedDict):
    idea: str
    thread_id: str

    # Agent outputs (correspond to models/schemas.py)
    requirements: Optional[dict]
    architecture: Optional[dict]
    codebase: Optional[dict]
    code_review: Optional[dict]
    test_report: Optional[dict]
    deployment: Optional[dict]

    feedback: Annotated[List[dict], add]

    qa_retries: int
    review_retries: int

    errors: Annotated[List[str], add]
    status: str

    # Messaging and memory
    a2a_log: Annotated[List[dict], add]
    last_message: Optional[dict]
    context_summary: Optional[str]

    # Per-phase documentation reports
    docs: Annotated[List[dict], add]


def initial_state(idea: str, thread_id: str) -> SDLCState:
    return SDLCState(
        idea=idea,
        thread_id=thread_id,
        requirements=None,
        architecture=None,
        codebase=None,
        code_review=None,
        test_report=None,
        deployment=None,
        feedback=[],
        qa_retries=0,
        review_retries=0,
        errors=[],
        status='initialized',
        a2a_log=[],
        last_message=None,
        context_summary=None,
        docs=[],
    )
