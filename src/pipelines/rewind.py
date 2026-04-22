from dataclasses import dataclass
from typing import Any, List

from src.logger.custom_logger import logger


@dataclass
class Step:
    """One entry in a run's history."""
    checkpoint_id: str
    node: str            
    has: dict[str, bool]


class CheckpointRewind:

    def __init__(self, graph, thread_id: str) -> None:
        self.graph = graph
        self.thread_id = thread_id
        self.config = {"configurable": {"thread_id": thread_id}}
        self.log = logger.bind(agent="rewind")

    def list_steps(self) -> List[Step]:
        snapshots = list(self.graph.get_state_history(self.config))
        snapshots.reverse()

        steps = []
        for snap in snapshots:
            values = snap.values or {}
            step = Step(
                checkpoint_id=snap.config["configurable"]["checkpoint_id"],
                node=(snap.next[0] if snap.next else "(end)"),
                status=values.get("status", "unknown"),
                has={
                    "requirements": values.get("requirements") is not None,
                    "architecture": values.get("architecture") is not None,
                    "codebase": values.get("codebase") is not None,
                    "test_report": values.get("test_report") is not None,
                    "deployment": values.get("deployment") is not None,
                },
            )
            steps.append(step)
        return steps

    def rewind_to(self, checkpoint_id: str) -> dict:
        cfg = {
            "configurable": {
                "thread_id": self.thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }
        snapshot = self.graph.get_state(cfg)
        self.log.info(
            f"Rewound thread {self.thread_id} to checkpoint {checkpoint_id} "
            f"(status={snapshot.values.get('status')})"
        )
        return snapshot.values

    def replay_config(self, checkpoint_id: str) -> dict:
        """Build a graph.invoke() config that continues from a checkpoint."""
        return {
            "configurable": {
                "thread_id": self.thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }
