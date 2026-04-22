import os
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx
import streamlit as st

API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
POLL_INTERVAL_SEC = 1.5

st.set_page_config(page_title='Agentic SDLC', layout='wide')
st.title('Agentic SDLC')
st.caption(f'Backend: {API_BASE_URL}')


def _client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE_URL, timeout=30.0)


def _handle_response(resp: httpx.Response) -> Optional[Dict[str, Any]]:
    if resp.status_code >= 400:
        st.error(f'API error {resp.status_code}: {resp.text}')
        return None
    return resp.json()


def _set_from_response(data: Dict[str, Any]) -> None:
    st.session_state.thread_id = data.get('thread_id', st.session_state.thread_id)
    st.session_state.stage = data.get('stage', 'done')
    st.session_state.pending_interrupt = data.get('pending_interrupt')
    st.session_state.latest_state = data.get('state', {})
    st.session_state.errors = data.get('errors', []) or []
    st.session_state.status = data.get('status', 'unknown')


def _fetch_state() -> Optional[Dict[str, Any]]:
    try:
        with _client() as client:
            resp = client.get(f'/runs/{st.session_state.thread_id}/state')
        return _handle_response(resp)
    except httpx.HTTPError as e:
        st.warning(f'Polling failed: {e}')
        return None


def _dedupe_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Agents often re-emit doc entries across retries. Keep the last one per
    (phase, path)."""
    latest: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for d in docs:
        if not isinstance(d, dict):
            continue
        key = f"{d.get('phase', '')}::{d.get('path', '') or d.get('title', '')}"
        if key not in latest:
            order.append(key)
        latest[key] = d
    return [latest[k] for k in order]


# --- session state ---
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = uuid.uuid4().hex[:8]
    st.session_state.stage = 'idle'
    st.session_state.pending_interrupt = None
    st.session_state.latest_state = {}
    st.session_state.errors = []
    st.session_state.status = 'idle'


# --- sidebar: start a new run ---
with st.sidebar:
    st.subheader('New run')
    idea = st.text_area(
        'Your idea',
        value='A FastAPI TODO API with CRUD and in-memory storage',
    )
    busy = st.session_state.stage in ('awaiting_hitl', 'processing')
    if st.button('Start', type='primary', disabled=busy):
        new_tid = uuid.uuid4().hex[:8]
        try:
            with _client() as client:
                resp = client.post(
                    '/runs',
                    json={'idea': idea, 'thread_id': new_tid},
                )
            data = _handle_response(resp)
        except httpx.HTTPError as e:
            st.error(f'Could not reach API at {API_BASE_URL}: {e}')
            data = None
        if data:
            _set_from_response(data)
            st.rerun()

    st.divider()
    st.caption(f'Thread: `{st.session_state.thread_id}`')
    st.caption(f'Stage: **{st.session_state.stage}**')
    st.caption(f'Status: {st.session_state.status}')


# --- if graph is processing, poll /state and surface progress --------------
if st.session_state.stage == 'processing':
    state = st.session_state.latest_state or {}
    st.subheader('Pipeline running...')
    with st.status('Agents working', expanded=True) as s:
        s.write(f'Current status: **{st.session_state.status}**')
        if state.get('codebase'):
            cb = state['codebase']
            if isinstance(cb, dict) and cb.get('project_dir'):
                s.write(f'Project directory: `{cb["project_dir"]}`')
        if state.get('deployment'):
            dep = state['deployment']
            if isinstance(dep, dict) and dep.get('branch_name'):
                s.write(f'Deploy branch: `{dep["branch_name"]}`')
        if st.session_state.errors:
            s.write('Errors so far:')
            for e in st.session_state.errors:
                s.write(f'- {e}')

    # One-shot poll per rerun; schedule the next rerun.
    data = _fetch_state()
    if data:
        _set_from_response(data)
    time.sleep(POLL_INTERVAL_SEC)
    st.rerun()

# --- HITL prompt -----------------------------------------------------------
elif st.session_state.stage == 'awaiting_hitl':
    intr = st.session_state.pending_interrupt or {}
    phase = intr.get('phase', 'unknown')
    st.subheader(f'Human review - {phase}')
    st.json(intr.get('preview') or {}, expanded=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button('Approve', type='primary'):
            try:
                with _client() as client:
                    resp = client.post(
                        f'/runs/{st.session_state.thread_id}/resume',
                        json={'verdict': 'approve', 'comment': ''},
                    )
                data = _handle_response(resp)
            except httpx.HTTPError as e:
                st.error(f'Resume failed: {e}')
                data = None
            if data:
                _set_from_response(data)
                st.rerun()
    with col2:
        comment = st.text_input('Reject with feedback:', key=f'fb_{phase}')
        if st.button('Reject and retry'):
            try:
                with _client() as client:
                    resp = client.post(
                        f'/runs/{st.session_state.thread_id}/resume',
                        json={
                            'verdict': 'reject',
                            'comment': comment or 'Please revise.',
                        },
                    )
                data = _handle_response(resp)
            except httpx.HTTPError as e:
                st.error(f'Resume failed: {e}')
                data = None
            if data:
                _set_from_response(data)
                st.rerun()

elif st.session_state.stage == 'done':
    st.success('Run complete')
    final = st.session_state.latest_state or {}
    deployment = final.get('deployment') or {}
    pr_url = deployment.get('pr_url') if isinstance(deployment, dict) else None
    if pr_url:
        st.link_button('Open pull request', pr_url)
    docs = _dedupe_docs(final.get('docs') or [])
    if docs:
        st.subheader('Phase documentation')
        for d in docs:
            with st.expander(d.get('title') or d.get('phase', 'doc')):
                if d.get('path'):
                    st.caption(f'File: {d["path"]}')
                st.markdown(d.get('content_markdown', ''))
    with st.expander('Final state', expanded=False):
        st.json(final)

elif st.session_state.stage == 'error':
    st.error('Pipeline failed')
    if st.session_state.errors:
        for e in st.session_state.errors:
            st.error(e)

else:
    st.info('Enter an idea in the sidebar and click Start.')

if st.session_state.errors and st.session_state.stage != 'error':
    with st.expander('Errors', expanded=False):
        for e in st.session_state.errors:
            st.error(e)
