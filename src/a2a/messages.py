import uuid
from typing import Any, Dict, List, Optional

from a2a.types import DataPart, Message, Part, Role, TextPart

def build_handoff_message(
    from_agent: str,
    to_agent: str,
    task: str,
    context_summary: str,
    artifacts: Dict[str, Any],
    instructions: str = '',
    context_id: Optional[str] = None,
    reference_task_ids: Optional[List[str]] = None
) -> Message:
    
    parts: List[Part] = []

    summary_text = context_summary or '(no prior summary)'
    if instructions:
        summary_text = f'{summary_text}\n\nInstructions: {instructions}'
    parts.append(Part(root=TextPart(text=summary_text)))

    for name, payload in artifacts.items():
        if payload is None:
            continue
        parts.append(Part(root=DataPart(
            data={'artifact_name': name, 'payload': payload},
            metadata={'artifact': name}
        )))

    return Message(
        message_id=uuid.uuid4().hex[:12],
        role=Role.agent,
        parts=parts,
        context_id=context_id,
        reference_task_ids=reference_task_ids or [],
        metadata={
            'from_agent': from_agent,
            'to_agent': to_agent,
            'task': task
        }
    )

def extract_artifacts(message: Message) -> Dict[str,Any]:
    out: Dict[str, Any] = {}
    for part in message.parts:
        root = part.root
        if isinstance(root, DataPart):
            name = root.data.get('architect_name')
            if name:
                out[name] = root.data.get('payload')
    return out

def extract_summary(message: Message) -> str:
    for part in message.parts:
        root = part.root
        if isinstance(root, TextPart):
            return root.Text
    return ''

def message_to_audit_row(msg: Message) -> Dict[str, Any]:
    meta = msg.metadata or {}
    return {
        'id': msg.message_id,
        'from_agent': meta.get('from_agent',''),
        'to_agent': meta.get('to_agent',''),
        'task': meta.get('task',''),
        'summary': extract_summary(msg)[:500],
        'architect_names': list(extract_artifacts(msg).keys())
    }