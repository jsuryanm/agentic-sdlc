from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from src.logger.custom_logger import logger
from src.pipelines.state import SDLCState
from src.memory.recall import recall_for_developer,recall_for_qa


_SUMMARY_SYSTEM = (
    "You are a project historian. Produce a TERSE summary (max 150 words) of "
    "the software project being built. Include: what's been built, key "
    "decisions, open issues. Output plain prose, no lists."
)


class ContextManager:
    """Prepares per-agent input projections and maintains a rolling summary."""

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
        if qa and qa.get("status") != "pass":
            errors = qa.get("errors", [])
            qa_feedback = "\n".join(errors[:3])[:2000]

        review = state.get("code_review") or {}
        review_feedback = "none" 
        
        if review and not review.get('passed',True):
            issues = review.get("issues",[])
            priority_order = {"high":0,"medium":1,"low":2}

            sorted_issues = sorted(issues,
                                   key=lambda i: priority_order.get(i.get("severity","medium"),1))
            
            structured = []

            for i in sorted_issues:
                file = i.get("file","unknown")
                line = i.get("line",1)
                msg = i.get("message","")
                structured.append(f"{file}:{line} -> {msg}")

            review_feedback = "Fix ALL of the following issues:\n" + "\n".join(structured[:30]) 

        requirements_summary = ContextManager._summarize_reqs(state.get("requirements"))
        stack = (state.get("architecture") or {}).get("stack",[])

        past_fixes = recall_for_developer(requirements_summary,stack)
        qa_errors = (state.get("test_report") or {}).get("errors",[])
        if qa_errors:
            query = f"""
                QA Errors:
                {"\n".join(qa_errors[:2])}
                
                Context:
                {ContextManager._summarize_reqs(state.get("requirements"))}
            """
            qa_memory = recall_for_qa(query)
        else:
            qa_memory = "none"
        


        return {
            "requirements_summary": requirements_summary,
            "architecture": state.get("architecture") or {},
            "qa_feedback": qa_feedback,
            "review_feedback": review_feedback,
            "docs_context":state.get("docs_context",""),
            "past_fixes":past_fixes,
            "qa_memory":qa_memory,
            "summary": state.get("context_summary") or "",
        }

    @staticmethod
    def for_code_review(state: SDLCState) -> Dict[str, Any]:
        codebase = state.get("codebase") or {}
        files = codebase.get("files", [])
        # Trim content to keep token usage reasonable.
        trimmed = [
            {"path": f.get("path", ""), "content": (f.get("content", "") or "")[:4000]}
            for f in files
        ]
        architecture = state.get("architecture") or {}
        return {
            "requirements_summary": ContextManager._summarize_reqs(
                state.get("requirements")
            ),
            "architecture": architecture,
            "stack": architecture.get("stack", []) or [],
            "files": trimmed,
            "retry_attempt": state.get("review_retries", 0),
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
    def for_doc(phase: str):
        """Returns a projection_fn for a DocAgent bound to one phase."""
        def _projection(state: SDLCState) -> Dict[str, Any]:
            artifact_key = {
                "requirements": "requirements",
                "architecture": "architecture",
                "developer": "codebase",
                "qa": "test_report",
                "devops": "deployment",
            }[phase]
            artifact = state.get(artifact_key) or {}
            return {
                "phase": phase,
                "artifact": artifact,
                "project_dir": (state.get("codebase") or {}).get("project_dir"),
                "project_name": (state.get("requirements") or {}).get("project_name"),
                "summary": state.get("context_summary") or "",
            }
        return _projection

    @staticmethod
    def update_rolling_summary(state: SDLCState) -> str:
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
        if "code_generated" in status and state.get("codebase"):
            return (
                f"Code generated: "
                f"{len(state['codebase'].get('files', []))} files written"
            )
        if "review" in status and state.get("code_review"):
            cr = state["code_review"]
            return (
                f"Code review: passed={cr.get('passed')}, "
                f"{len(cr.get('issues', []))} issues"
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
