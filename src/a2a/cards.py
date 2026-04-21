from a2a.types import AgentCapabilities, AgentCard, AgentSkill

_PROTOCOL_VERSION = '0.3.0'
_BASE_URL = 'http://localhost:0/'
_DEFAULT_MODES = ['text', 'data']

_CAPS = AgentCapabilities(streaming=False, push_notifications=False)

def _card(
        name: str,
        description: str,
        skill_id: str,
        skill_name: str,
        skill_desc: str,
        tags: list[str],
        examples: list[str]
) -> AgentCard:
    return AgentCard(
        name=name,
        description=description,
        url=_BASE_URL,
        version='1.0.0',
        protocol_version=_PROTOCOL_VERSION,
        capabilities=_CAPS,
        default_input_modes=_DEFAULT_MODES,
        default_output_modes=_DEFAULT_MODES,
        skills=[AgentSkill(
            id=skill_id,
            name=skill_name,
            description=skill_desc,
            tags=tags,
            examples=examples
        )]
    )

REQUIREMENTS_CARD = _card(
    name="Requirements Agent",
    description="Converts a plain-English idea into structured user stories and NFRs.",
    skill_id="draft_requirements",
    skill_name="Draft software requirements",
    skill_desc="Produces 3-5 user stories with acceptance criteria for a small FastAPI service.",
    tags=["requirements", "product-management", "user-stories"],
    examples=["A FastAPI TODO API with CRUD and in-memory storage"]
)

ARCHITECT_CARD = _card(
    name="Architect Agent",
    description="DeAnsigns a minimal FastAPI + Pydantic project structure.",
    skill_id="design_architecture",
    skill_name="Design project architecture",
    skill_desc="Produces file list, stack choices, and entry point for a 5-10 file FastAPI service.",
    tages=["architecture", "fastapi", "pydantic"],
    examples=["Design a REST API with 4 endpoints and pytest tests"]
)

DEVELOPER_CARD = _card(
    name="Developer Agent",
    description="Generates production-grade Python code for every file in the architecture.",
    skill_id="generate_code",
    skill_name="Generate application code",
    skill_desc="Writes complete runnable Python files. Uses agentic RAG to consult current docs.",
    tags=["code-generation", "python", "fastapi"],
    examples=["Implement the architecture as FastAPI + Pydantic v2"],
)

QA_CARD = _card(
    name="QA Agent",
    description="Runs pytest against generated code and reports structured results.",
    skill_id="run_tests",
    skill_name="Execute test suite",
    skill_desc="Installs dependencies, runs pytest, parses pass/fail counts, extracts errors.",
    tags=["testing", "pytest", "qa"],
    examples=["Run tests in workspace/todo-api"],
)

DEVOPS_CARD = _card(
    name="DevOps Agent",
    description="Generates Dockerfile + CI, provisions GitHub repo, and opens a PR.",
    skill_id="deploy",
    skill_name="Deploy and open PR",
    skill_desc="Creates repo if missing, pushes code to a timestamped branch, opens PR to main.",
    tags=["devops", "github", "ci-cd", "docker"],
    examples=["Deploy todo-api to GitHub with a CI workflow"],
)

CARD_BY_NAME = {
    'requirement_agent': REQUIREMENTS_CARD,
    'architect_agent': ARCHITECT_CARD,
    'developer_agent': DEVELOPER_CARD,
    'qa_agent': QA_CARD,
    'devops_agent': DEVOPS_CARD
}

NEXT_AGENT = {
    'requirements_agent': 'architect_agent',
    'architect_agent': 'developer_agent',
    'developer_agent': 'qa_agent',
    'qa_agent': 'devops_agent',
    'devops_agent': 'human'
}

TASK_FOR_RECEIVER = {
    'architect_agent': 'design_architecture',
    'developer_agent': 'generate_code',
    'qa_agent': 'run_tests',
    'devops_agent': 'deploy',
    'human': 'review'
}