"""Lightweight agent-card metadata.

The upstream ``a2a.types.AgentCard`` is a protobuf message whose schema has
shifted across releases. This module keeps its own plain-dict cards so the
rest of the codebase can reference stable metadata without coupling to a
specific protobuf schema.
"""
from typing import Any, Dict, List


def _card(
    name: str,
    description: str,
    skill_id: str,
    skill_name: str,
    skill_desc: str,
    tags: List[str],
    examples: List[str],
) -> Dict[str, Any]:
    return {
        'name': name,
        'description': description,
        'version': '1.0.0',
        'skills': [
            {
                'id': skill_id,
                'name': skill_name,
                'description': skill_desc,
                'tags': tags,
                'examples': examples,
            }
        ],
    }


REQUIREMENTS_CARD = _card(
    name='Requirements Agent',
    description='Converts a plain-English idea into structured user stories and NFRs.',
    skill_id='draft_requirements',
    skill_name='Draft software requirements',
    skill_desc='Produces 3-5 user stories with acceptance criteria for a small FastAPI service.',
    tags=['requirements', 'product-management', 'user-stories'],
    examples=['A FastAPI TODO API with CRUD and in-memory storage'],
)

ARCHITECT_CARD = _card(
    name='Architect Agent',
    description='Designs a minimal FastAPI + Pydantic project structure.',
    skill_id='design_architecture',
    skill_name='Design project architecture',
    skill_desc='Produces file list, stack choices, and entry point for a 5-10 file FastAPI service.',
    tags=['architecture', 'fastapi', 'pydantic'],
    examples=['Design a REST API with 4 endpoints and pytest tests'],
)

DEVELOPER_CARD = _card(
    name='Developer Agent',
    description='Generates production-grade Python code for every file in the architecture.',
    skill_id='generate_code',
    skill_name='Generate application code',
    skill_desc='Writes complete runnable Python files. Uses agentic RAG to consult current docs.',
    tags=['code-generation', 'python', 'fastapi'],
    examples=['Implement the architecture as FastAPI + Pydantic v2'],
)

CODE_REVIEW_CARD = _card(
    name='Code Review Agent',
    description='Reviews generated code for correctness, security, and style; requests fixes.',
    skill_id='review_code',
    skill_name='Review generated codebase',
    skill_desc='Inspects each file and returns a structured review with required fixes.',
    tags=['code-review', 'quality', 'security'],
    examples=['Review the generated FastAPI TODO service'],
)

QA_CARD = _card(
    name='QA Agent',
    description='Runs pytest against generated code and reports structured results.',
    skill_id='run_tests',
    skill_name='Execute test suite',
    skill_desc='Installs dependencies, runs pytest, parses pass/fail counts, extracts errors.',
    tags=['testing', 'pytest', 'qa'],
    examples=['Run tests in workspace/todo-api'],
)

DEVOPS_CARD = _card(
    name='DevOps Agent',
    description='Generates Dockerfile + CI, provisions GitHub repo, and opens a PR.',
    skill_id='deploy',
    skill_name='Deploy and open PR',
    skill_desc='Creates repo if missing, pushes code to a timestamped branch, opens PR to main.',
    tags=['devops', 'github', 'ci-cd', 'docker'],
    examples=['Deploy todo-api to GitHub with a CI workflow'],
)

DOC_CARD = _card(
    name='Documentation Agent',
    description='Generates per-phase Markdown reports for the SDLC pipeline.',
    skill_id='generate_phase_doc',
    skill_name='Produce phase documentation',
    skill_desc="Writes a structured Markdown report summarizing one phase's artifacts.",
    tags=['documentation', 'reporting'],
    examples=['Produce requirements phase documentation'],
)

CARD_BY_NAME = {
    'requirement_agent': REQUIREMENTS_CARD,
    'architect_agent': ARCHITECT_CARD,
    'developer_agent': DEVELOPER_CARD,
    'code_review_agent': CODE_REVIEW_CARD,
    'qa_agent': QA_CARD,
    'devops_agent': DEVOPS_CARD,
    'doc_agent': DOC_CARD,
}

NEXT_AGENT = {
    'requirement_agent': 'architect_agent',
    'architect_agent': 'developer_agent',
    'developer_agent': 'code_review_agent',
    'code_review_agent': 'qa_agent',
    'qa_agent': 'devops_agent',
    'devops_agent': 'human',
    'doc_requirements_agent': 'human',
    'doc_architecture_agent': 'human',
    'doc_developer_agent': 'human',
    'doc_qa_agent': 'human',
    'doc_devops_agent': 'human',
}

TASK_FOR_RECEIVER = {
    'architect_agent': 'design_architecture',
    'developer_agent': 'generate_code',
    'code_review_agent': 'review_code',
    'qa_agent': 'run_tests',
    'devops_agent': 'deploy',
    'human': 'review',
}
