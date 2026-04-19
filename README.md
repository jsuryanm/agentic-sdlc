# Agentic SDLC

A multi-agent pipeline that transforms a one-line project idea into production-ready code, tests, Dockerfile, and a GitHub PR — with human review gates at every major step.

Built with [LangGraph](https://github.com/langchain-ai/langgraph), OpenAI, and Streamlit.

---

## How it works

```
Idea → Requirements → [Review] → Architecture → [Review] → Developer → QA → Developer (retry) → DevOps → [Review] → PR
```

1. **Requirements** — LLM generates user stories and non-functional requirements
2. **Human review** — approve or reject with feedback (loops back on reject)
3. **Architecture** — LLM designs file structure, stack, and entry point
4. **Human review** — approve or reject
5. **Developer** — LLM generates all source files + tests, writes them to `workspace/<project>/`
6. **QA** — runs `pytest` inside the generated project; if tests fail, loops back to Developer (max 2 retries)
7. **DevOps** — generates Dockerfile and CI YAML, pushes to GitHub via MCP, opens a PR
8. **Human review** — approve to finish, reject to regenerate deployment config

---

## Setup

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- OpenAI API key
- (Optional) GitHub Personal Access Token for the DevOps agent

### Install

```bash
git clone <repo>
cd agentic-sdlc
uv sync
```

### Configure

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `LLM_MODEL` | No | Model name (default: `gpt-4o-mini`) |
| `LLM_TEMPERATURE` | No | Sampling temperature (default: `0.2`) |
| `LLM_MAX_TOKENS` | No | Max tokens per LLM call (default: `2000`) |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | No | For DevOps agent GitHub MCP push |
| `GITHUB_REPO_OWNER` | No | GitHub username/org for PR target |
| `GITHUB_REPO_NAME` | No | Repo name for PR target |
| `LOG_LEVEL` | No | `INFO` or `DEBUG` (default: `INFO`) |

### Run

```bash
streamlit run src/dashboard/streamlit_app.py
```

Opens at `http://localhost:8501`.

---

## Usage

1. Enter your project idea in the sidebar (e.g. "A FastAPI TODO API with CRUD and in-memory storage")
2. Click **Start**
3. The pipeline runs until the first human review gate — review the output in the main panel
4. Click **Approve** to continue or provide feedback and **Reject & retry**
5. Repeat at architecture and deployment gates
6. When the run completes, a link to the generated PR appears (if GitHub MCP is configured)

Generated code is written to `workspace/<project-name>/`.

---

## Project structure

```
src/
├── agents/         # One class per pipeline stage (base_agent + 5 agents)
├── core/           # Settings (pydantic-settings, reads .env)
├── dashboard/      # Streamlit UI
├── exceptions/     # Custom exception hierarchy
├── logger/         # Loguru-based structured logging
├── models/         # Pydantic schemas (Requirements, Architecture, Codebase, ...)
├── pipelines/      # LangGraph graph definition + SDLCState TypedDict
├── prompts/        # ChatPromptTemplate definitions per agent
├── tests/          # Project-level unit tests
└── tools/          # LLMFactory, TestRunner, GitHubMCPClient
workspace/          # Generated projects land here
logs/               # Per-run timestamped log files
.checkpoints/       # LangGraph SQLite checkpoint database
```

---

## Running tests

```bash
pytest src/tests/
```

---

## Logs

Each run writes a timestamped log to `logs/sdlc_run_<timestamp>.log`. Console output uses the same structured format with per-agent context binding.
