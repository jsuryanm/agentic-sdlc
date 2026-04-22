# Architecture

This document explains how the pieces of Agentic SDLC fit together: the request flow, the graph shape, the state model, and the side systems (A2A, RAG, memory, checkpointing).

---

## High-level diagram

```
┌─────────────┐    HTTP     ┌────────────────────────┐
│  Streamlit  │ ──────────► │  FastAPI  (/runs, ...) │
│  dashboard  │ ◄────────── │  src/api/app.py        │
└─────────────┘             └──────────┬─────────────┘
                                       │ graph.invoke / resume
                                       ▼
                        ┌───────────────────────────────────┐
                        │   LangGraph StateGraph            │
                        │   src/pipelines/graph.py          │
                        │                                   │
                        │   START → requirement → hitl_req  │
                        │   → doc_requirements → architect  │
                        │   → hitl_arch → doc_architecture  │
                        │   → developer ↔ code_review       │
                        │   → doc_developer → qa            │
                        │   → doc_qa → hitl_deploy          │
                        │   → devops → doc_devops → END     │
                        └──────────┬─────────────┬──────────┘
                                   │             │
                     SqliteSaver   │             │  A2A bus (SQLite)
                   .checkpoints/   │             │  src/a2a
                      sdlc.sqlite  │             │
                                   ▼             ▼
                          ┌────────────────────────────┐
                          │  Agents (src/agents/*)     │
                          │  ├─ RequirementAgent       │
                          │  ├─ ArchitectAgent         │
                          │  ├─ DeveloperAgent ──► RAG │
                          │  ├─ CodeReviewAgent        │
                          │  ├─ QAAgent     ──► pytest │
                          │  ├─ DevOpsAgent ──► GitHub │
                          │  └─ DocAgent    ──► md+pdf │
                          └────────────────────────────┘
```

---

## Request lifecycle

1. **User types an idea** in the Streamlit sidebar → POST `/runs`.
2. **FastAPI** looks up the singleton compiled graph (built at lifespan startup) and calls `graph.invoke(initial_state(idea, thread_id), config={'thread_id': ...})`.
3. The graph runs until it hits an `interrupt()` call inside an HITL node (or reaches `END`).
4. On interrupt, LangGraph returns a result with `__interrupt__` populated; the route serialises this and the client renders the approval UI.
5. **User clicks approve / reject** → POST `/runs/{thread_id}/resume` with a verdict. FastAPI calls `graph.invoke(Command(resume={...}))`.
6. LangGraph continues from the checkpoint until the next interrupt or `END`.
7. **End state** includes the generated code path, test report, PR URL, and a list of Markdown + PDF phase reports.

Every step is checkpointed to SQLite, so a run survives process restarts and can be **rewound** to any prior step via `POST /runs/{thread_id}/rewind`.

---

## Graph shape

File: `src/pipelines/graph.py`.

- **Agent singletons** are module-level (`_req`, `_arch`, …). They're constructed once, reused per run; they hold LLM clients and prompt chains.
- `build_graph(checkpointer)` wires nodes → edges → conditional routes → compiles.
- **Conditional edges** handle:
  - HITL approve / reject (loops requirements and architecture back)
  - Code-review pass / fail (loops developer, bounded by `MAX_REVIEW_RETRIES`)
  - QA pass / fail (loops developer, bounded by `MAX_QA_RETRIES`)
  - Deploy approve / reject (reject loops back to `qa`)
- **Interrupts** (HITL) are implemented via `langgraph.types.interrupt({...})`. The returned dict is provided by the resume payload.

---

## State

```python
class SDLCState(TypedDict, total=False):
    idea: str
    thread_id: str
    requirements: Optional[dict]
    architecture: Optional[dict]
    codebase: Optional[dict]       # includes project_dir + files
    code_review: Optional[dict]
    test_report: Optional[dict]
    deployment: Optional[dict]
    docs: Annotated[List[dict], add]          # appended by DocAgent
    feedback: Annotated[List[dict], add]      # appended by HITL nodes
    errors: Annotated[List[str], add]         # appended by BaseAgent on failure
    qa_retries: int
    review_retries: int
    status: str
    context_summary: str
    last_message: Optional[dict]
```

Crucial gotcha: fields explicitly set to `None` by `initial_state()` don't trigger `state.get(key, default)` defaults. Use `state.get(key) or default` everywhere.

---

## ContextManager

`src/pipelines/context.py` builds per-agent **projections** of state — trimmed, task-specific views — plus a rolling **summary** string that carries the narrative forward between agents. This keeps agent prompts small and focused even as the graph grows.

Each agent declares a `projection_fn` (e.g. `ContextManager.for_architect`) that returns only what that agent needs.

---

## Agent-to-agent bus

`src/a2a/` is a small SQLite-backed message bus orthogonal to LangGraph state. Agents declare typed **cards** (`cards.py`) describing the tasks they send and accept. Each message is durable and tagged with `sender`, `receiver`, `task`, and `parts`. The dashboard tails these for a human-readable trace of the pipeline.

It does **not** move state between nodes (LangGraph does that). It's a narrative channel — useful for showing "what just happened" to a human, and for passing opaque artifacts between non-graph components.

---

## Knowledge layer (RAG)

`src/knowledge/` implements optional retrieval before code generation:

- `tavily_client.py` — thin wrapper over `tavily.AsyncTavilyClient` (the official SDK).
- `ingest.py` — fetches search results for one or more topics (`fastapi`, `pydantic`, `pytest`, …), chunks them with `RecursiveCharacterTextSplitter`, and writes to Chroma.
- `store.py` — Chroma-backed vector store per topic, persisted under `.checkpoints/chroma/`.
- `retriever.py` — topic-scoped retrieval for the DeveloperAgent.
- `agentic_rag.py` — orchestrator: picks topics, runs ingest if the store is empty, retrieves, returns formatted context.

Disabled transparently if `TAVILY_API_KEY` is not set — the agent falls back to its own knowledge.

---

## Long-term memory

`src/memory/store.py` stores per-project **episodic** memories in a SQLite + Chroma pair (`.checkpoints/long_term_memory.sqlite`). `recall.py` exposes `recall_for_architect(...)` and similar helpers so individual agents can pull relevant priors into their prompt.

Unlike checkpoints (which are run-scoped and replay state), memory is cross-run and semantic.

---

## Tools

- `LLMFactory` — thin cache around `ChatOpenAI` instances keyed by `(model, temperature)`. Always use this; never instantiate `ChatOpenAI` directly.
- `TestRunner` — spawns `sys.executable -m pytest -q --tb=short` in the generated project dir, parses counts from output, returns a `TestReport`.
- `GitHubMCPClient` — thin client over the GitHub MCP server for branch creation, file push (with SHA for updates), and PR creation.

---

## File layout recap

```
.checkpoints/
  sdlc.sqlite               # LangGraph run state
  a2a.sqlite                # A2A message bus
  long_term_memory.sqlite   # Episodic memories
  chroma/                   # Vector stores (RAG + memory)

logs/
  sdlc_run_<timestamp>.log  # Structured per-run logs

workspace/
  <project-name>/           # Generated project
    app/ ...                # Source files
    tests/ ...              # Generated tests
    docs/
      requirements.md + .pdf
      architecture.md  + .pdf
      developer.md     + .pdf
      qa.md            + .pdf
      devops.md        + .pdf
    Dockerfile
    requirements.txt
    .github/workflows/ci.yml

src/
  a2a/ agents/ api/ core/ dashboard/ exceptions/ knowledge/
  logger/ memory/ models/ pipelines/ prompts/ tests/ tools/
```

---

## Extending the system

Adding a new phase is a handful of touch points:

1. New agent in `src/agents/` (follow `BaseAgent` contract).
2. New prompt in `src/prompts/`.
3. New schema in `src/models/schemas.py`.
4. New field in `SDLCState` if the agent writes one.
5. New node + edges in `src/pipelines/graph.py`.
6. (Optional) new A2A card in `src/a2a/cards.py`.
7. (Optional) new projection method in `ContextManager`.
8. Tests in `src/tests/`.

The deliberate separation of concerns — agents know *what*, graph knows *when*, context knows *how much*, A2A knows *who tells whom* — is what keeps this small as it grows.
