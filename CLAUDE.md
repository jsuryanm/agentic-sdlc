# CLAUDE.md — Agentic SDLC

This file gives Claude Code the context it needs to work effectively in this repo.

---

## What this project is

A LangGraph-based multi-agent pipeline that takes a plain-English idea and produces runnable code, tests, Markdown + PDF documentation, a Dockerfile, CI config, and a GitHub PR. A FastAPI service drives the graph; a Streamlit dashboard is the UI and handles human-in-the-loop (HITL) approval gates.

---

## Key commands

| Task | Command |
|------|---------|
| Install dependencies | `uv sync` |
| Run the API | `uvicorn src.api.app:app --reload --port 8000 --reload-dir src` |
| Run the dashboard | `streamlit run src/dashboard/streamlit_app.py` |
| Run project tests | `pytest src/tests/` |
| Run a single test file | `pytest src/tests/test_graph_routing.py -v` |

The dashboard talks to the API over HTTP (`API_BASE_URL`, default `http://localhost:8000`). Always start the API first.

---

## Project layout

```
src/
├── a2a/            # Agent-to-agent message bus (SQLite-backed) + agent cards
├── agents/         # One class per SDLC stage + BaseAgent + DocAgent (parameterized by phase)
├── api/            # FastAPI app, routes, lifespan + deps (graph singleton)
├── core/config.py  # pydantic-settings BaseSettings — reads .env
├── dashboard/      # Streamlit app (single file: streamlit_app.py)
├── exceptions/     # Custom exception hierarchy
├── tools/mcp_client.py  # Context7 MCP client for library-doc retrieval + GitHub MCP
├── logger/         # Loguru setup; use logger.bind(agent=name) everywhere
├── memory/         # Long-term memory (per-project episodic recall)
├── models/schemas.py  # All Pydantic models (Requirements, Architecture, Codebase, ...)
├── pipelines/
│   ├── context.py  # ContextManager: per-agent state projections + rolling summary
│   ├── graph.py    # LangGraph nodes + edges; build_graph(), make_checkpointer()
│   ├── rewind.py   # Checkpoint rewind helpers
│   └── state.py    # SDLCState TypedDict + initial_state()
├── prompts/        # One ChatPromptTemplate file per agent
├── tests/          # Unit tests for this project (not the generated code)
└── tools/          # LLMFactory, TestRunner, GitHubMCPClient
workspace/          # Generated project directories land here (gitignored)
.checkpoints/       # LangGraph + A2A + memory SQLite DBs (gitignored)
```

---

## Pipeline shape

```
requirement -> hitl_req -> doc_requirements -> architect -> hitl_arch -> doc_architecture
 -> developer -> hitl_developer -> code_review (auto-loop to developer while
    review_retries < MAX_REVIEW_RETRIES) -> hitl_review -> doc_developer
 -> qa (auto-loop to developer while qa_retries < MAX_QA_RETRIES) -> hitl_qa
 -> doc_qa -> hitl_deploy -> devops -> doc_devops -> END
```

Every major agent is followed by a human-in-the-loop gate (`hitl_*`). Nothing
advances to the next step without explicit approval. Rejecting any gate with a
comment loops back to the previous working agent (developer for dev/review/qa;
architect for arch; requirement for reqs). The automatic review/QA retry loops
still exist, but once they hit the retry ceiling the result is surfaced to the
human rather than silently proceeding.

---

## How agents are structured

Every agent extends `BaseAgent` (`src/agents/base_agent.py`):

- `run(state)` — public entry point; wraps `_process` with timing, context projection, and error handling
- `_process(state, projection) -> dict` — must be implemented; returns state update dict

The returned dict is **merged** into `SDLCState` by LangGraph. Fields with `Annotated[List, add]` (e.g. `feedback`, `errors`, `docs`) are appended, not replaced.

When an agent fails, `BaseAgent.run()` catches the exception and returns:
```python
{'errors': [msg], 'status': f'{self.name}_failed'}
```
Downstream agents must guard against missing keys (e.g. `codebase` may be `None`).

`DocAgent` is parameterized: `DocAgent('requirements')`, `DocAgent('architecture')`, etc. Doc output is written as both `.md` and `.pdf` under `workspace/<project>/docs/` once `project_dir` is known; earlier phases buffer in `state['docs']` and flush when the first project-dir-aware phase sees it.

---

## LangGraph graph

Defined in `src/pipelines/graph.py`. Key patterns:

- `build_graph(checkpointer)` compiles the graph (agent singletons are module-level)
- `make_checkpointer()` opens an SQLite-backed checkpointer at `.checkpoints/sdlc.sqlite`
- HITL nodes use `interrupt({...})` to pause and `Command(resume={...})` to continue
- `thread_id` in `configurable` identifies a run; the same `thread_id` resumes from checkpoint
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
| `code_review` | Optional[dict] | CodeReviewAgent |
| `test_report` | Optional[dict] | QAAgent |
| `deployment` | Optional[dict] | DevOpsAgent |
| `docs` | List[dict] (append) | DocAgent |
| `feedback` | List[dict] (append) | HITL nodes |
| `qa_retries` | int | QAAgent |
| `review_retries` | int | CodeReviewAgent |
| `errors` | List[str] (append) | BaseAgent on failure |
| `status` | str | Each agent |
| `context_summary` | str | ContextManager |

---

## Adding a new agent

1. Create `src/agents/my_agent.py` extending `BaseAgent`
2. Add a prompt in `src/prompts/my_prompt.py`
3. Add a schema in `src/models/schemas.py` if needed
4. Register an agent card in `src/a2a/cards.py` if it sends/receives A2A messages
5. Add a node function and edges in `src/pipelines/graph.py`
6. Tests go in `src/tests/`

---

## LLM usage

Always use `LLMFactory.get(temperature=...)`. It caches by `(model, temperature)` so it won't create duplicate clients.

For structured output:
```python
chain = PROMPT | LLMFactory.get().with_structured_output(MySchema)
result: MySchema = chain.invoke({...})
```

---

## API

`src/api/app.py` exposes `app = create_app()` so uvicorn can load it directly without `--factory`. Routes in `src/api/routes.py`:

- `POST /runs` — start a run (body: `{idea, thread_id?}`)
- `POST /runs/{thread_id}/resume` — resume from an interrupt (body: `{verdict, comment}`)
- `GET /runs/{thread_id}/state` — current state + pending interrupt
- `GET /runs/{thread_id}/checkpoints` — list checkpoints
- `POST /runs/{thread_id}/rewind` — rewind to a checkpoint

The graph is built once on FastAPI startup (`deps.startup()`) and reused across requests.

---

## Library documentation (Context7 MCP)

Before code generation and code review, the pipeline fetches canonical library docs from the Context7 MCP server via `src/tools/mcp_client.py` (`fetch_docs_for_stack` / `fetch_docs_for_stack_sync`). The developer agent also runs a short tool-calling ReAct loop over the same Context7 tools (`get_context7_tools`) so the LLM can request docs on demand. Controlled by `USE_CONTEXT7` and `CONTEXT7_MCP_COMMAND` / `CONTEXT7_MCP_ARGS` in `src/core/config.py`. The server itself is launched via stdio — no daemon to keep running.

## Long-term memory

`src/memory/store.py` stores per-project episodic memories in SQLite + Chroma. `recall.py` exposes helpers like `recall_for_architect()` used from individual agents.

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
