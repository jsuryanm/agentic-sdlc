from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from src.logger.custom_logger import logger
from src.pipelines.state import SDLCState

_SUMMARY_SYSTEM = (
    "You are a project historian. Produce a TERSE summary (max 150 words) of "
    "the software project being built. Include: what's been built, key "
    "decisions, open issues. Output plain prose, no lists."
)


class ContextManager:

    @staticmethod
    def for_requirements(state: SDLCState) -> Dict[str, Any]:
        return {
            "idea": state["idea"],
            "prior_feedback": ContextManager._latest_feedback(state, "requirements"),
            "summary": state.get("context_summary") or "",
        }

    @staticmethod
    def for_architect(state: SDLCState) -> Dict[str, Any]:
        return {
            "requirements": state.get("requirements") or {},
            "prior_feedback": ContextManager._latest_feedback(state, "architecture"),
            "summary": state.get("context_summary") or "",
        }

    @staticmethod
    def for_developer(state: SDLCState) -> Dict[str, Any]:
        qa = state.get("test_report") or {}
        qa_feedback = "none"
        # Only include distilled errors — not 4KB of pytest raw_output
        if qa and qa.get("status") != "pass":
            errors = qa.get("errors", [])
            qa_feedback = "\n".join(errors[:3])[:2000]
        return {
            "requirements_summary": ContextManager._summarize_reqs(
                state.get("requirements")
            ),
            "architecture": state.get("architecture") or {},
            "qa_feedback": qa_feedback,
            "summary": state.get("context_summary") or "",
        }

    @staticmethod
    def for_qa(state: SDLCState) -> Dict[str, Any]:
        codebase = state.get("codebase") or {}
        return {
            "project_dir": codebase.get("project_dir"),
            "file_count": len(codebase.get("files", [])),
            "retry_attempt": state.get("qa_retries", 0),
        }

    @staticmethod
    def for_devops(state: SDLCState) -> Dict[str, Any]:
        return {
            "project_name": (state.get("requirements") or {}).get("project_name"),
            "entry_point": (state.get("architecture") or {}).get("entry_point"),
            "stack": (state.get("architecture") or {}).get("stack", []),
            "project_dir": (state.get("codebase") or {}).get("project_dir"),
        }

    @staticmethod
    def update_rolling_summary(state: SDLCState) -> str:
        """Called by BaseAgent after each successful _process."""
        # Lazy import — keeps projections importable without langchain stack
        from src.tools.llm_factory import LLMFactory

        prior = state.get("context_summary") or "(project just started)"
        latest = ContextManager._latest_event(state)

        try:
            llm = LLMFactory.get(temperature=0.0)
            response = llm.invoke([
                SystemMessage(content=_SUMMARY_SYSTEM),
                HumanMessage(content=(
                    f"Prior summary:\n{prior}\n\n"
                    f"Latest event:\n{latest}\n\n"
                    f"Updated summary:"
                )),
            ])
            new_summary = response.content.strip()
            logger.bind(agent="context").info(
                f"Summary updated ({len(new_summary)} chars)"
            )
            return new_summary
        except Exception as e:
            logger.bind(agent="context").warning(f"Summary update failed: {e}")
            return prior

    @staticmethod
    def _latest_feedback(state: SDLCState, phase: str) -> str:
        relevant = [f for f in state.get("feedback", []) if f.get("phase") == phase]
        return relevant[-1].get("comment", "") if relevant else ""

    @staticmethod
    def _summarize_reqs(reqs: Optional[dict]) -> str:
        if not reqs:
            return "(none)"
        stories = reqs.get("user_stories", [])
        titles = [s.get("title", "") for s in stories]
        return (
            f"Project: {reqs.get('project_name')}. "
            f"Summary: {reqs.get('summary', '')[:200]}. "
            f"Stories ({len(stories)}): {', '.join(titles)}"
        )

    @staticmethod
    def _latest_event(state: SDLCState) -> str:
        status = state.get("status", "")
        if "requirements" in status and state.get("requirements"):
            return (
                f"Requirements drafted: "
                f"{state['requirements'].get('project_name')}"
            )
        if "architecture" in status and state.get("architecture"):
            arch = state["architecture"]
            return (
                f"Architecture: stack={arch.get('stack')}, "
                f"{len(arch.get('files', []))} files"
            )
        if "code" in status and state.get("codebase"):
            return (
                f"Code generated: "
                f"{len(state['codebase'].get('files', []))} files written"
            )
        if "qa" in status and state.get("test_report"):
            tr = state["test_report"]
            return (
                f"Tests {tr.get('status')}: "
                f"{tr.get('passed')} passed, {tr.get('failed')} failed"
            )
        if "deployment" in status:
            return "Deployment artifacts ready"
        return f"Status: {status}"
