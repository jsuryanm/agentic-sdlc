"""Plain-dict handoff messages.

The upstream ``a2a.types`` protobuf classes (``Message``, ``DataPart``,
``TextPart``, ``Role``) shift across releases. We keep our own dict-shaped
messages so the rest of the codebase has a stable wire format for audit
logging and inter-agent handoffs.
"""
import uuid
from typing import Any, Dict, List, Optional


def build_handoff_message(
    from_agent: str,
    to_agent: str,
    task: str,
    context_summary: str,
    artifacts: Dict[str, Any],
    instructions: str = '',
    context_id: Optional[str] = None,
    reference_task_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    summary_text = context_summary or '(no prior summary)'
    if instructions:
        summary_text = f'{summary_text}\n\nInstructions: {instructions}'

    parts: List[Dict[str, Any]] = [{'kind': 'text', 'text': summary_text}]
    for name, payload in artifacts.items():
        if payload is None:
            continue
        parts.append({
            'kind': 'data',
            'artifact_name': name,
            'payload': payload,
        })

    return {
        'message_id': uuid.uuid4().hex[:12],
        'role': 'agent',
        'parts': parts,
        'context_id': context_id,
        'reference_task_ids': reference_task_ids or [],
        'metadata': {
            'from_agent': from_agent,
            'to_agent': to_agent,
            'task': task,
        },
    }


def extract_artifacts(message: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for part in message.get('parts', []):
        if part.get('kind') == 'data':
            name = part.get('artifact_name')
            if name:
                out[name] = part.get('payload')
    return out


def extract_summary(message: Dict[str, Any]) -> str:
    for part in message.get('parts', []):
        if part.get('kind') == 'text':
            return part.get('text', '')
    return ''


def message_to_audit_row(msg: Dict[str, Any]) -> Dict[str, Any]:
    meta = msg.get('metadata') or {}
    return {
        'id': msg.get('message_id', ''),
        'from_agent': meta.get('from_agent', ''),
        'to_agent': meta.get('to_agent', ''),
        'task': meta.get('task', ''),
        'summary': extract_summary(msg)[:500],
        'artifact_names': list(extract_artifacts(msg).keys()),
    }
