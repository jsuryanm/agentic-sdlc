import time
from abc import ABC, abstractmethod

from src.logger.custom_logger import logger
from src.pipelines.state import SDLCState
from typing import Any, Callable, Dict, Optional

from a2a.types import AgentCard, Message

from src.a2a import (
    A2ABus,
    NEXT_AGENT,
    TASK_FOR_RECEIVER,
    build_handoff_message,
    message_to_audit_row
)

class BaseAgent(ABC):
    name: str = 'base_agent'
    card: Optional[AgentCard] = None

    projection_fn: Optional[Callable[[SDLCState], Dict[str, Any]]] = None

    def __init__(self):
        self.logger = logger.bind(agent=self.name)
        self._bus = A2ABus()

    def run(self, state: SDLCState) -> dict:
        self.logger.info(f'▶ {self.name} starting')
        start = time.time()

        self._log_incoming(state)
        projection = self._build_projection(state)

        try:
            updates = self._process(state, projection)
            elapsed = round(time.time() - start, 2)
            self.logger.info(f'{self.name} done in {elapsed}s')

            if 'errors' in updates and updates.get('status', '').endswith('_failed'):
                return updates
            
            from src.pipelines.context import ContextManager
            merged = {**state, **updates}
            updates['context_summary'] = ContextManager.update_rolling_summary(merged)

            outgoing = self._build_outgoing(merged, updates)
            self._bus.publish(outgoing, thread_id=state.get('thread_id', ''))
            updates['a2a_log'] = [message_to_audit_row(outgoing)]
            updates['last_message'] = outgoing.model_dump(
                mode='json', exclude_none=True
            )

            return updates

        except Exception as e:
            elapsed = round(time.time() - start, 2)
            msg = f'{self.name} failed after {elapsed}s: {e}'
            self.logger.exception(msg)
            return {'errors': [msg], 'status': f'{self.name}_failed'}
        
    @abstractmethod
    def _process(self, state: SDLCState, projection: Dict[str, Any]) -> dict: ...

    def _log_incoming(self, state: SDLCState) -> None:
        incoming = state.get('last_message') or {}
        meta = incoming.get('metadata') or {}
        if meta:
            self.logger.info(
                f'← received from {meta.get('from_agent', '?')}'
                f'task={meta.get('task', '?')}'
            )

    def _build_projection(self, state: SDLCState) -> Dict[str, Any]:
        if self.projection_fn is None:
            return {}
        fn = self.projection_fn
        if hasattr(fn, '__func__'):
            fn = fn.__func__
        return fn(state)
    
    def _build_outgoing(self, merged_state: dict, updates: dict) -> Message:
        to_agent = NEXT_AGENT.get(self.name, 'human')
        task = TASK_FOR_RECEIVER.get(to_agent, 'handoff')

        artifacts: Dict[str, Any] = {}
        for key in ('requirements', 'architecture', 'codebase',
                    'test_report', 'deployment'):
            value = updates.get(key) or merged_state.get(key)
            if value is not None:
                artifacts[key] = value

        return build_handoff_message(
            from_agent=self.name,
            to_agent=to_agent,
            task=task,
            context_summary=updates.get('context_summary','') or '',
            artifacts=artifacts,
            instructions=f'Continue pipeline from {self.name}',
            context_id=merged_state.get('thread_id')
        )