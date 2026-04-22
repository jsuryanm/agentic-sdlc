import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from langgraph.types import Command

from src.api.deps import get_graph
from src.api.models import (
    CheckpointSummary,
    ResumePayload,
    RewindPayload,
    RunCreate,
    RunResponse,
)
from src.logger.custom_logger import logger
from src.pipelines.rewind import CheckpointRewind
from src.pipelines.state import initial_state

router = APIRouter()

# --- background execution of graph.invoke -----------------------------------
# The graph runs for minutes at a time (agents call LLMs, write files, push to
# GitHub). Blocking the HTTP request for that duration prevents the dashboard
# from showing live progress. We run graph.invoke in a pool and let clients
# poll /runs/{thread_id}/state.
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix='graph-runner')
_RUNS: Dict[str, Future] = {}
_RUNS_LOCK = threading.Lock()


def _submit(thread_id: str, fn, *args) -> None:
    future = _EXECUTOR.submit(fn, *args)

    def _log_done(f: Future) -> None:
        exc = f.exception()
        if exc is not None:
            logger.bind(agent='api').exception(
                f'graph run {thread_id} failed: {exc}'
            )

    future.add_done_callback(_log_done)
    with _RUNS_LOCK:
        _RUNS[thread_id] = future


def _future_status(thread_id: str) -> str:
    """Return 'running', 'done', 'failed', or 'unknown'."""
    with _RUNS_LOCK:
        fut = _RUNS.get(thread_id)
    if fut is None:
        return 'unknown'
    if not fut.done():
        return 'running'
    return 'failed' if fut.exception() is not None else 'done'


def _cfg(thread_id: str) -> Dict[str, Any]:
    return {'configurable': {'thread_id': thread_id}}


def _current_state(graph, thread_id: str) -> Dict[str, Any]:
    try:
        snap = graph.get_state(_cfg(thread_id))
        return snap.values or {}
    except Exception as e:
        logger.bind(agent='api').warning(f'get_state failed: {e}')
        return {}


def _pending_interrupt(graph, thread_id: str) -> Optional[Dict[str, Any]]:
    try:
        snap = graph.get_state(_cfg(thread_id))
    except Exception:
        return None
    if not getattr(snap, 'next', None):
        return None
    for task in getattr(snap, 'tasks', []) or []:
        interrupts = getattr(task, 'interrupts', None) or []
        if interrupts:
            return interrupts[0].value
    return None


def _snapshot(graph, thread_id: str) -> RunResponse:
    values = _current_state(graph, thread_id)
    fut_status = _future_status(thread_id)
    # While the background future is running, the checkpoint may still be
    # showing the HITL interrupt we just resumed from (LangGraph has not yet
    # applied the Command). Treat that as 'processing', not awaiting_hitl.
    pending = None if fut_status == 'running' else _pending_interrupt(graph, thread_id)

    if fut_status == 'running':
        stage = 'processing'
    elif pending is not None:
        stage = 'awaiting_hitl'
    elif fut_status == 'failed':
        stage = 'error'
    else:
        stage = 'done' if values else 'unknown'

    return RunResponse(
        thread_id=thread_id,
        status=values.get('status', 'unknown'),
        stage=stage,
        pending_interrupt=pending,
        state=_jsonable(values),
        errors=values.get('errors', []) or [],
    )


def _jsonable(state: Dict[str, Any]) -> Dict[str, Any]:
    """Strip keys that are not trivially JSON-serialisable."""
    safe: Dict[str, Any] = {}
    for k, v in state.items():
        if k == 'last_message' and v is not None:
            safe[k] = v
            continue
        try:
            import json
            json.dumps(v, default=str)
            safe[k] = v
        except Exception:
            safe[k] = str(v)
    return safe


def _run_graph(thread_id: str, payload: Any) -> None:
    graph = get_graph()
    graph.invoke(payload, config=_cfg(thread_id))


@router.post('/runs', response_model=RunResponse)
def create_run(payload: RunCreate) -> RunResponse:
    graph = get_graph()
    thread_id = payload.thread_id or uuid.uuid4().hex[:8]

    status = _future_status(thread_id)
    if status == 'running':
        raise HTTPException(status_code=409, detail='Run already in progress')

    init = initial_state(payload.idea, thread_id)
    _submit(thread_id, _run_graph, thread_id, init)
    return _snapshot(graph, thread_id)


@router.post('/runs/{thread_id}/resume', response_model=RunResponse)
def resume_run(thread_id: str, payload: ResumePayload) -> RunResponse:
    graph = get_graph()

    if _future_status(thread_id) == 'running':
        raise HTTPException(
            status_code=409,
            detail='Graph is still processing; wait for the next HITL gate',
        )

    cmd = Command(resume={'verdict': payload.verdict, 'comment': payload.comment})
    _submit(thread_id, _run_graph, thread_id, cmd)
    return _snapshot(graph, thread_id)


@router.get('/runs/{thread_id}/state', response_model=RunResponse)
def get_run_state(thread_id: str) -> RunResponse:
    graph = get_graph()
    values = _current_state(graph, thread_id)
    if not values and _future_status(thread_id) == 'unknown':
        raise HTTPException(status_code=404, detail='Unknown thread_id')
    return _snapshot(graph, thread_id)


@router.get('/runs/{thread_id}/checkpoints', response_model=List[CheckpointSummary])
def list_checkpoints(thread_id: str) -> List[CheckpointSummary]:
    graph = get_graph()
    rewind = CheckpointRewind(graph, thread_id)
    steps = rewind.list_steps()
    return [
        CheckpointSummary(
            checkpoint_id=s.checkpoint_id,
            node=s.node,
            status=s.status,
            has=s.has,
        )
        for s in steps
    ]


@router.post('/runs/{thread_id}/rewind', response_model=RunResponse)
def rewind_run(thread_id: str, payload: RewindPayload) -> RunResponse:
    graph = get_graph()
    rewind = CheckpointRewind(graph, thread_id)
    try:
        values = rewind.rewind_to(payload.checkpoint_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Rewind failed: {e}')
    return RunResponse(
        thread_id=thread_id,
        status=values.get('status', 'unknown'),
        stage='rewound',
        pending_interrupt=None,
        state=_jsonable(values),
        errors=values.get('errors', []) or [],
    )
