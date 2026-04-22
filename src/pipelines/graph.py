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


def _agent_node(agent):
    def node(state: SDLCState) -> dict:
        return agent.run(state)
    return node


def _make_hitl_node(phase: str, preview_key: str):
    def hitl_node(state: SDLCState) -> dict:
        preview = state.get(preview_key)
        decision = interrupt({
            'phase': phase,
            'preview': preview,
            'message': f'Review the {phase} output. Approve or reject with feedback.',
        })
        verdict = decision.get('verdict', 'approve')
        comment = decision.get('comment', '')
        logger.bind(agent='hitl').info(f'[{phase}] verdict = {verdict}')
        return {'feedback': [{'phase': phase, 'verdict': verdict, 'comment': comment}]}
    return hitl_node


hitl_requirements = _make_hitl_node('requirements', 'requirements')
hitl_architecture = _make_hitl_node('architecture', 'architecture')


def _codebase_preview(state: SDLCState) -> dict:
    codebase = state.get('codebase') or {}
    files = codebase.get('files') or []
    return {
        'project_dir': codebase.get('project_dir'),
        'file_count': len(files),
        'files': [f.get('path') for f in files],
        'notes': codebase.get('notes'),
    }


def hitl_developer(state: SDLCState) -> dict:
    decision = interrupt({
        'phase': 'developer',
        'preview': _codebase_preview(state),
        'message': (
            'Developer agent finished generating the codebase. Approve to run '
            'code review, or reject to regenerate with your feedback.'
        ),
    })
    verdict = decision.get('verdict', 'approve')
    comment = decision.get('comment', '')
    logger.bind(agent='hitl').info(f'[developer] verdict = {verdict}')
    return {'feedback': [{'phase': 'developer', 'verdict': verdict, 'comment': comment}]}


def hitl_review(state: SDLCState) -> dict:
    review = state.get('code_review') or {}
    preview = {
        'passed': review.get('passed'),
        'issues': review.get('issues') or [],
        'required_fixes': review.get('required_fixes') or [],
        'review_retries': state.get('review_retries', 0),
    }
    message = (
        'Code review passed. Approve to move on to QA, or reject to regenerate.'
        if review.get('passed')
        else 'Code review FAILED or hit the retry limit. Approve to QA anyway, '
             'or reject to send it back to the developer with your feedback.'
    )
    decision = interrupt({
        'phase': 'code_review',
        'preview': preview,
        'message': message,
    })
    verdict = decision.get('verdict', 'approve')
    comment = decision.get('comment', '')
    logger.bind(agent='hitl').info(f'[code_review] verdict = {verdict}')
    return {
        'feedback': [
            {'phase': 'code_review', 'verdict': verdict, 'comment': comment}
        ],
    }


def hitl_qa(state: SDLCState) -> dict:
    report = state.get('test_report') or {}
    preview = {
        'status': report.get('status'),
        'passed': report.get('passed'),
        'failed': report.get('failed'),
        'errors': (report.get('errors') or [])[:3],
        'qa_retries': state.get('qa_retries', 0),
    }
    if report.get('status') == 'pass':
        message = 'QA tests passed. Approve to document the QA phase and move toward deployment.'
    else:
        message = (
            'QA tests FAILED or errored (collection/import error). Approve to '
            'proceed anyway, or reject to regenerate the code with your feedback.'
        )
    decision = interrupt({
        'phase': 'qa',
        'preview': preview,
        'message': message,
    })
    verdict = decision.get('verdict', 'approve')
    comment = decision.get('comment', '')
    logger.bind(agent='hitl').info(f'[qa] verdict = {verdict}')
    return {'feedback': [{'phase': 'qa', 'verdict': verdict, 'comment': comment}]}


def hitl_deploy(state: SDLCState) -> dict:
    codebase = state.get('codebase') or {}
    test_report = state.get('test_report') or {}
    preview = {
        'project_name': codebase.get('project_name'),
        'project_dir': codebase.get('project_dir'),
        'files': [f.get('path') for f in (codebase.get('files') or [])],
        'test_status': test_report.get('status'),
        'tests_passed': test_report.get('passed'),
        'tests_failed': test_report.get('failed'),
    }
    decision = interrupt({
        'phase': 'deployment',
        'preview': preview,
        'message': 'Approve to push the generated code to GitHub, or reject to re-run QA.',
    })
    verdict = decision.get('verdict', 'approve')
    comment = decision.get('comment', '')
    logger.bind(agent='hitl').info(f'[deployment] verdict = {verdict}')
    return {'feedback': [{'phase': 'deployment', 'verdict': verdict, 'comment': comment}]}


def _latest_verdict_for(state: SDLCState, phase: str) -> str:
    for fb in reversed(state.get('feedback') or []):
        if fb.get('phase') == phase:
            return fb.get('verdict', 'approve')
    return 'approve'


def route_after_hitl_req(state: SDLCState) -> str:
    return 'doc_requirements' if _latest_verdict_for(state, 'requirements') == 'approve' else 'requirement'


def route_after_hitl_arch(state: SDLCState) -> str:
    return 'doc_architecture' if _latest_verdict_for(state, 'architecture') == 'approve' else 'architect'


def route_after_hitl_developer(state: SDLCState) -> str:
    return 'code_review' if _latest_verdict_for(state, 'developer') == 'approve' else 'developer'


def route_after_code_review(state: SDLCState) -> str:
    """Go to human review when review passes OR retries are exhausted;
    otherwise loop back to developer automatically."""
    review = state.get('code_review') or {}
    if review.get('passed'):
        return 'hitl_review'
    if state.get('review_retries', 0) >= settings.MAX_REVIEW_RETRIES:
        return 'hitl_review'
    return 'developer'


def route_after_hitl_review(state: SDLCState) -> str:
    return 'doc_developer' if _latest_verdict_for(state, 'code_review') == 'approve' else 'developer'


def route_after_qa(state: SDLCState) -> str:
    """Always surface QA result to a human before proceeding (on pass or at
    retry limit). Only auto-loop back to developer when retries remain."""
    report = state.get('test_report') or {}
    if report.get('status') == 'pass':
        return 'hitl_qa'
    if state.get('qa_retries', 0) >= settings.MAX_QA_RETRIES:
        return 'hitl_qa'
    return 'developer'


def route_after_hitl_qa(state: SDLCState) -> str:
    return 'doc_qa' if _latest_verdict_for(state, 'qa') == 'approve' else 'developer'


def route_after_hitl_deploy(state: SDLCState) -> str:
    return 'devops' if _latest_verdict_for(state, 'deployment') == 'approve' else 'qa'


def build_graph(checkpointer):
    g = StateGraph(SDLCState)

    g.add_node('requirement', _agent_node(_req))
    g.add_node('hitl_req', hitl_requirements)
    g.add_node('doc_requirements', _agent_node(_doc_requirements))
    g.add_node('architect', _agent_node(_arch))
    g.add_node('hitl_arch', hitl_architecture)
    g.add_node('doc_architecture', _agent_node(_doc_architecture))
    g.add_node('developer', _agent_node(_dev))
    g.add_node('hitl_developer', hitl_developer)
    g.add_node('code_review', _agent_node(_review))
    g.add_node('hitl_review', hitl_review)
    g.add_node('doc_developer', _agent_node(_doc_developer))
    g.add_node('qa', _agent_node(_qa))
    g.add_node('hitl_qa', hitl_qa)
    g.add_node('doc_qa', _agent_node(_doc_qa))
    g.add_node('hitl_deploy', hitl_deploy)
    g.add_node('devops', _agent_node(_ops))
    g.add_node('doc_devops', _agent_node(_doc_devops))

    g.add_edge(START, 'requirement')
    g.add_edge('requirement', 'hitl_req')
    g.add_conditional_edges(
        'hitl_req', route_after_hitl_req,
        {'doc_requirements': 'doc_requirements', 'requirement': 'requirement'},
    )
    g.add_edge('doc_requirements', 'architect')
    g.add_edge('architect', 'hitl_arch')
    g.add_conditional_edges(
        'hitl_arch', route_after_hitl_arch,
        {'doc_architecture': 'doc_architecture', 'architect': 'architect'},
    )
    g.add_edge('doc_architecture', 'developer')
    g.add_edge('developer', 'hitl_developer')
    g.add_conditional_edges(
        'hitl_developer', route_after_hitl_developer,
        {'code_review': 'code_review', 'developer': 'developer'},
    )
    g.add_conditional_edges(
        'code_review', route_after_code_review,
        {'hitl_review': 'hitl_review', 'developer': 'developer'},
    )
    g.add_conditional_edges(
        'hitl_review', route_after_hitl_review,
        {'doc_developer': 'doc_developer', 'developer': 'developer'},
    )
    g.add_edge('doc_developer', 'qa')
    g.add_conditional_edges(
        'qa', route_after_qa,
        {'hitl_qa': 'hitl_qa', 'developer': 'developer'},
    )
    g.add_conditional_edges(
        'hitl_qa', route_after_hitl_qa,
        {'doc_qa': 'doc_qa', 'developer': 'developer'},
    )
    g.add_edge('doc_qa', 'hitl_deploy')
    g.add_conditional_edges(
        'hitl_deploy', route_after_hitl_deploy,
        {'devops': 'devops', 'qa': 'qa'},
    )
    g.add_edge('devops', 'doc_devops')
    g.add_edge('doc_devops', END)

    return g.compile(checkpointer=checkpointer)


def make_checkpointer():
    db_path = str(settings.CHECKPOINT_DIR / 'sdlc.sqlite')
    return SqliteSaver.from_conn_string(db_path)
