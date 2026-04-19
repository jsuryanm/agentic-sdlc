# CLAUDE.md — Agentic SDLC

This file gives Claude Code the context it needs to work effectively in this repo.

---

## What this project is

A LangGraph-based multi-agent pipeline that takes a plain-English idea and produces runnable code, tests, a Dockerfile, CI config, and a GitHub PR. A Streamlit dashboard drives the UI with human-in-the-loop approval gates.

---

## Key commands

| Task | Command |
|------|---------|
| Install dependencies | `uv sync` |
| Run the dashboard | `streamlit run src/dashboard/streamlit_app.py` |
| Run project tests | `pytest src/tests/` |
| Run a single test file | `pytest src/tests/test_graph_routing.py -v` |

---

## Project layout

```
src/
├── agents/         # Agent classes (one per SDLC stage + BaseAgent)
├── core/config.py  # All settings — read from .env via pydantic-settings
├── dashboard/      # Streamlit app (single file: streamlit_app.py)
├── exceptions/     # Custom exception hierarchy
├── logger/         # Loguru setup; use logger.bind(agent=name) everywhere
├── models/schemas.py  # All Pydantic models (Requirements, Architecture, Codebase, ...)
├── pipelines/
│   ├── graph.py    # LangGraph node + edge definitions; build_graph()
│   └── state.py    # SDLCState TypedDict + initial_state()
├── prompts/        # One ChatPromptTemplate file per agent
├── tests/          # Unit tests for this project (not the generated code)
└── tools/          # LLMFactory, TestRunner, GitHubMCPClient
workspace/          # Generated project directories land here (gitignored)
.checkpoints/       # LangGraph SQLite checkpoint DB (gitignored)
```

---

## How agents are structured

Every agent extends `BaseAgent` (`src/agents/base_agent.py`):

- `run(state)` — public entry point; wraps `_process` with timing + error handling
- `_process(state) -> dict` — must be implemented; returns state update dict

The returned dict is **merged** into `SDLCState` by LangGraph. Fields with `Annotated[List, add]` (e.g. `feedback`, `errors`) are appended, not replaced.

When an agent fails, `BaseAgent.run()` catches the exception and returns:
```python
{'errors': [msg], 'status': f'{self.name}_failed'}
```
This means downstream agents must guard against missing keys (e.g. `codebase` may be `None`).

---

## LangGraph graph

Defined in `src/pipelines/graph.py`. Key patterns:

- `build_graph(checkpointer)` compiles the graph
- `make_checkpointer()` opens an SQLite-backed checkpointer from `.checkpoints/sdlc.sqlite`
- HITL nodes use `interrupt({...})` to pause and `Command(resume={...})` to continue
- `thread_id` in `configurable` identifies a run; same thread_id resumes from checkpoint
- `SDLCState` fields initialized to `None` — always use `state.get(key) or default` pattern, not `state.get(key, default)`, since explicitly-`None` values don't trigger the default

---

## SDLCState fields

| Field | Type | Set by |
|-------|------|--------|
| `idea` | str | `initial_state()` |
| `thread_id` | str | `initial_state()` |
| `requirements` | Optional[dict] | RequirementAgent |
| `architecture` | Optional[dict] | ArchitectAgent |
| `codebase` | Optional[dict] | DeveloperAgent (includes `project_dir`) |
| `test_report` | Optional[dict] | QAAgent |
| `deployment` | Optional[dict] | DevOpsAgent |
| `feedback` | List[dict] (append) | HITL nodes |
| `qa_retries` | int | QAAgent |
| `errors` | List[str] (append) | BaseAgent on failure |
| `status` | str | Each agent |

---

## Adding a new agent

1. Create `src/agents/my_agent.py` extending `BaseAgent`
2. Add a prompt in `src/prompts/my_prompt.py`
3. Add a schema in `src/models/schemas.py` if needed
4. Add a node function and edges in `src/pipelines/graph.py`
5. Tests go in `src/tests/`

---

## LLM usage

Always use `LLMFactory.get(temperature=...)`. It caches by `(model, temperature)` so it won't create duplicate clients.

For structured output:
```python
chain = PROMPT | LLMFactory.get().with_structured_output(MySchema)
result: MySchema = chain.invoke({...})
```

---

## Configuration

All settings live in `src/core/config.py` as a `pydantic_settings.BaseSettings` class. Add new settings there; they auto-load from `.env`. Never hardcode paths — use `settings.WORKSPACE_DIR`, `settings.CHECKPOINT_DIR`, etc.

---

## Logging

```python
from src.logger.custom_logger import logger
self.logger = logger.bind(agent=self.name)
self.logger.info("message")
```

Logs go to console and `logs/sdlc_run_<timestamp>.log`.
