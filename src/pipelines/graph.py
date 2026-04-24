from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt

from src.agents.architect_agent import ArchitectAgent
from src.agents.code_review_agent import CodeReviewAgent
from src.agents.developer_agent import DeveloperAgent
from src.agents.devops_agent import DevOpsAgent
from src.agents.doc_agent import DocAgent
from src.agents.qa_agent import QAAgent
from src.agents.requirements_agent import RequirementAgent
from src.core.config import settings
from src.logger.custom_logger import logger
from src.pipelines.state import SDLCState


# -------------------------
# Agents
# -------------------------
_req = RequirementAgent()
_arch = ArchitectAgent()
_dev = DeveloperAgent()
_review = CodeReviewAgent()
_qa = QAAgent()
_ops = DevOpsAgent()

_doc_requirements = DocAgent('requirements')
_doc_architecture = DocAgent('architecture')
_doc_developer = DocAgent('developer')
_doc_qa = DocAgent('qa')
_doc_devops = DocAgent('devops')


# -------------------------
# Helpers
# -------------------------
def _agent_node(agent):
    def node(state: SDLCState) -> dict:
        return agent.run(state)
    return node


def _latest_verdict(state: SDLCState, phase: str) -> str:
    for fb in reversed(state.get("feedback") or []):
        if fb.get("phase") == phase:
            return fb.get("verdict", "approve")
    return "approve"


def _locked(state: SDLCState, key: str) -> bool:
    return (state.get("locks") or {}).get(key, False)


# -------------------------
# HITL Nodes
# -------------------------
def _hitl(phase: str, preview_key: str):
    def node(state: SDLCState) -> dict:
        decision = interrupt({
            "phase": phase,
            "preview": state.get(preview_key),
            "message": f"Review {phase}",
        })

        return {
            "feedback": [{
                "phase": phase,
                "verdict": decision.get("verdict", "approve"),
                "comment": decision.get("comment", "")
            }]
        }

    return node


hitl_requirements = _hitl("requirements", "requirements")
hitl_architecture = _hitl("architecture", "architecture")


def hitl_developer(state: SDLCState) -> dict:
    decision = interrupt({
        "phase": "developer",
        "preview": state.get("codebase"),
        "message": "Approve developer output",
    })

    return {
        "feedback": [{
            "phase": "developer",
            "verdict": decision.get("verdict", "approve"),
            "comment": decision.get("comment", "")
        }]
    }


def hitl_review(state: SDLCState) -> dict:
    decision = interrupt({
        "phase": "code_review",
        "preview": state.get("code_review"),
        "message": "Review code review",
    })

    return {
        "feedback": [{
            "phase": "code_review",
            "verdict": decision.get("verdict", "approve"),
            "comment": decision.get("comment", "")
        }]
    }


def hitl_qa(state: SDLCState) -> dict:
    decision = interrupt({
        "phase": "qa",
        "preview": state.get("test_report"),
        "message": "QA review",
    })

    return {
        "feedback": [{
            "phase": "qa",
            "verdict": decision.get("verdict", "approve"),
            "comment": decision.get("comment", "")
        }]
    }


def hitl_deploy(state: SDLCState) -> dict:
    decision = interrupt({
        "phase": "deployment",
        "preview": state,
        "message": "Deploy or rollback",
    })

    return {
        "feedback": [{
            "phase": "deployment",
            "verdict": decision.get("verdict", "approve"),
            "comment": decision.get("comment", "")
        }]
    }


# -------------------------
# ROUTING (STRICT 2-TRY RULES)
# -------------------------

# REQUIREMENTS
def route_req(state: SDLCState) -> str:
    return "doc_requirements" if _latest_verdict(state, "requirements") == "approve" else "requirement"


# ARCHITECTURE
def route_arch(state: SDLCState) -> str:
    return "doc_architecture" if _latest_verdict(state, "architecture") == "approve" else "architect"


# -------------------------
# DEVELOPER FLOW (LOCK SAFE)
# -------------------------
def route_dev_hitl(state: SDLCState) -> str:
    if _locked(state, "code_review"):
        return "code_review"

    return "code_review" if _latest_verdict(state, "developer") == "approve" else "developer"


# -------------------------
# CODE REVIEW (STRICT LIMIT)
# -------------------------
def route_code_review(state: SDLCState) -> str:
    review = state.get("code_review") or {}
    retries = state.get("review_retries", 0)

    if retries >= 2:
        return "hitl_review"   # HARD STOP LOOP

    if review.get("passed"):
        return "hitl_review"

    return "developer"


def route_hitl_review(state: SDLCState) -> str:
    retries = state.get("review_retries", 0)

    if retries >= 2:
        return "doc_developer"

    return "doc_developer" if _latest_verdict(state, "code_review") == "approve" else "developer"


# -------------------------
# QA (STRICT LIMIT)
# -------------------------
def route_qa(state: SDLCState) -> str:
    report = state.get("test_report") or {}
    retries = state.get("qa_retries", 0)

    if retries >= 2:
        return "hitl_qa"

    return "hitl_qa" if report.get("status") == "pass" else "developer"


def route_hitl_qa(state: SDLCState) -> str:
    retries = state.get("qa_retries", 0)

    if retries >= 2:
        return "doc_qa"

    return "doc_qa" if _latest_verdict(state, "qa") == "approve" else "developer"


# -------------------------
# DEPLOY
# -------------------------
def route_hitl_deploy(state: SDLCState) -> str:
    return "devops" if _latest_verdict(state, "deployment") == "approve" else "qa"


# -------------------------
# GRAPH BUILD
# -------------------------
def build_graph(checkpointer):
    g = StateGraph(SDLCState)

    g.add_node("requirement", _agent_node(_req))
    g.add_node("hitl_req", hitl_requirements)
    g.add_node("doc_requirements", _agent_node(_doc_requirements))

    g.add_node("architect", _agent_node(_arch))
    g.add_node("hitl_arch", hitl_architecture)
    g.add_node("doc_architecture", _agent_node(_doc_architecture))

    g.add_node("developer", _agent_node(_dev))
    g.add_node("hitl_developer", hitl_developer)

    g.add_node("code_review", _agent_node(_review))
    g.add_node("hitl_review", hitl_review)
    g.add_node("doc_developer", _agent_node(_doc_developer))

    g.add_node("qa", _agent_node(_qa))
    g.add_node("hitl_qa", hitl_qa)
    g.add_node("doc_qa", _agent_node(_doc_qa))

    g.add_node("hitl_deploy", hitl_deploy)
    g.add_node("devops", _agent_node(_ops))
    g.add_node("doc_devops", _agent_node(_doc_devops))

    # Flow
    g.add_edge(START, "requirement")
    g.add_edge("requirement", "hitl_req")
    g.add_conditional_edges("hitl_req", route_req,
                            {"doc_requirements": "doc_requirements", "requirement": "requirement"})

    g.add_edge("doc_requirements", "architect")
    g.add_edge("architect", "hitl_arch")
    g.add_conditional_edges("hitl_arch", route_arch,
                            {"doc_architecture": "doc_architecture", "architect": "architect"})

    g.add_edge("doc_architecture", "developer")
    g.add_edge("developer", "hitl_developer")
    g.add_conditional_edges("hitl_developer", route_dev_hitl,
                            {"code_review": "code_review", "developer": "developer"})

    g.add_conditional_edges("code_review", route_code_review,
                            {"hitl_review": "hitl_review", "developer": "developer"})

    g.add_conditional_edges("hitl_review", route_hitl_review,
                            {"doc_developer": "doc_developer", "developer": "developer"})

    g.add_edge("doc_developer", "qa")

    g.add_conditional_edges("qa", route_qa,
                            {"hitl_qa": "hitl_qa", "developer": "developer"})

    g.add_conditional_edges("hitl_qa", route_hitl_qa,
                            {"doc_qa": "doc_qa", "developer": "developer"})

    g.add_edge("doc_qa", "hitl_deploy")

    g.add_conditional_edges("hitl_deploy", route_hitl_deploy,
                            {"devops": "devops", "qa": "qa"})

    g.add_edge("devops", "doc_devops")
    g.add_edge("doc_devops", END)

    return g.compile(checkpointer=checkpointer)


def make_checkpointer():
    db_path = str(settings.CHECKPOINT_DIR / "sdlc.sqlite")
    return SqliteSaver.from_conn_string(db_path)

