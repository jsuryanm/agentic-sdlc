from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command, interrupt

from src.agents.architect_agent import ArchitectAgent
from src.agents.developer_agent import DeveloperAgent
from src.agents.devops_agent import DevOpsAgent
from src.agents.qa_agent import QAAgent
from src.agents.requirements_agent import RequirementAgent
from src.core.config import settings
from src.logger.custom_logger import logger
from src.pipelines.state import SDLCState

_req = RequirementAgent()
_arch = ArchitectAgent()
_dev = DeveloperAgent()
_qa = QAAgent()
_ops = DevOpsAgent()

def requirement_node(state: SDLCState) -> dict:
    return _req.run(state)

def architect_node(state: SDLCState) -> dict:
    return _arch.run(state)

def developer_node(state: SDLCState) -> dict:
    return _dev.run(state)

def qa_node(state: SDLCState) -> dict:
    return _qa.run(state)

def devops_node(state: SDLCState) -> dict: 
    return _ops.run(state)

def _make_hitl_node(phase: str, preview_key: str):
    def hitl_node(state: SDLCState) -> dict:
        preview = state.get(preview_key)
        decision = interrupt({
            'phase': phase,
            'preview': preview,
            'message': f'Review the {phase} output. Approve or reject with feedback.'
        })
        verdict = decision.get('verdict', 'approve')
        comment = decision.get('comment', '')
        logger.bind(agent='hitl').info(f'[{phase}] verdict = {verdict}')
        return {'feedback': [{'phase': phase, 'verdict': verdict, 'comment': comment}]}
    
    return hitl_node

hitl_requirements = _make_hitl_node('requirements', 'requirments')
hitl_architecture = _make_hitl_node('architecture', 'architecture')
hitl_deploy = _make_hitl_node('deployment', 'deployment')

def route_after_hitl_req(state: SDLCState) -> str:
    last = state['feedback'][-1]
    return 'architect' if last['verdict'] == 'approve' else 'requirement'

def route_after_hitl_arch(state: SDLCState) -> str:
    last = state['feedback'][-1]
    return 'developer' if last['verdict'] == 'approve' else 'architect'

def route_after_qa(state: SDLCState) -> str:
    report = state.get('test_report', {})
    if report.get('status') == 'pass':
        return 'devops'
    if state.get('qa_retries', 0) >= settings.MAX_QA_RETRIES:
        return 'devops'
    return 'developer'

def route_after_hitl_deploy(state: SDLCState) -> str:
    last = state['feedback'][-1]
    return END if last['verdict'] == 'approve' else 'devops'

def build_graph(checkpointer):
    g = StateGraph(SDLCState)

    g.add_node('requirement', requirement_node)
    g.add_node('hitl_req', hitl_requirements)
    g.add_node('architect', architect_node)
    g.add_node('hitl_arch', hitl_architecture)
    g.add_node('developer', developer_node)
    g.add_node('qa', qa_node)
    g.add_node('devops', devops_node)
    g.add_node('hitl_deploy', hitl_deploy)

    g.add_edge(START, 'requirement')
    g.add_edge('requirment', 'hitl_req')
    g.add_conditional_edges('hitl_req', route_after_hitl_req,
                            {'architect': 'architect', 'requirement': 'requirement'})
    g.add_edge('architect', 'hitl_arch')
    g.add_conditional_edges('hitl_arch', route_after_hitl_arch,
                            {'developer': 'developer', 'architect': 'architect'})
    g.add_edge('developer', 'qa')
    g.add_conditional_edges('qa', route_after_qa,
                            {'developer': 'developer', 'devops': 'devops'})
    g.add_edge('devops', 'hitl_deploy')
    g.add_conditional_edges('hitl_deploy', route_after_hitl_deploy,
                            {END: END, 'devops': 'devops'})
    
    return g.compile(checkpointer=checkpointer)

def make_checkpointer():
    db_path = str(settings.CHECKPOINT_DIR / 'sdlc.sqlite')
    return SqliteSaver.from_conn_string(db_path)