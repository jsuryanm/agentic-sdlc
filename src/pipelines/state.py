from operator import add
from typing import Annotated, List, Optional
from typing_extensions import TypedDict

class SDLCState(TypedDict):
    idea: str
    thread_id: str

    requirements: Optional[dict]
    architecture: Optional[dict]
    codebase: Optional[dict]
    test_report: Optional[dict]
    deployment: Optional[dict]

    feedback: Annotated[List[dict], add]

    qa_retries: int

    errors: Annotated[List[str], add]
    status: str

def initial_state(idea: str, thread_id: str) -> SDLCState:
    return SDLCState(
        idea=idea,
        thread_id=thread_id,
        requirements=None,
        architecture=None,
        codebase=None,
        test_report=None,
        deployment=None,
        feedback=[],
        qa_retires=0,
        errors=[],
        status='initialized'
    )