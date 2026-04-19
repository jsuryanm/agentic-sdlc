# ARCHITECTURE.md — System Architecture

---

## Pipeline overview

```
START
  │
  ▼
[requirement] ──────────────────────────────────────────────────────┐
  │                                                                  │
  ▼                                                                  │
[hitl_req] ──reject──► loops back to [requirement] ◄────────────────┘
  │ approve
  ▼
[architect] ─────────────────────────────────────────────────────────┐
  │                                                                   │
  ▼                                                                   │
[hitl_arch] ──reject──► loops back to [architect] ◄──────────────────┘
  │ approve
  ▼
[developer] ◄──────────────────────────────────────────────┐
  │                                                         │
  ▼                                                         │
[qa] ──fail (retries < MAX)──────────────────────────────────┘
  │ pass  OR  retries >= MAX_QA_RETRIES
  ▼
[devops] ────────────────────────────────────────────────────┐
  │                                                           │
  ▼                                                           │
[hitl_deploy] ──reject──► loops back to [devops] ◄───────────┘
  │ approve
  ▼
END
```

---

## LangGraph state machine

The graph is defined in `src/pipelines/graph.py` and compiled via `build_graph(checkpointer)`.

**Nodes** are plain Python functions `(SDLCState) -> dict`. Each returns a partial state update — LangGraph merges it into the current state.

**Edges** are either fixed (`add_edge`) or conditional (`add_conditional_edges`). Conditional edges call a routing function that returns the next node name.

**HITL nodes** use `interrupt(payload)` to pause execution mid-graph. The Streamlit UI reads the interrupt payload, displays it, and resumes with `graph.invoke(Command(resume={...}), config=cfg)`.

**Checkpointing** is backed by SQLite at `.checkpoints/sdlc.sqlite`. Every step is checkpointed. If the process restarts, invoking with the same `thread_id` resumes from the last checkpoint — this is how the Streamlit page refresh works.

---

## SDLCState lifecycle

```python
class SDLCState(TypedDict):
    idea: str                          # set at start, never changes
    thread_id: str                     # set at start, never changes

    requirements: Optional[dict]       # set by RequirementAgent
    architecture: Optional[dict]       # set by ArchitectAgent
    codebase: Optional[dict]           # set by DeveloperAgent (+project_dir path)
    test_report: Optional[dict]        # set by QAAgent
    deployment: Optional[dict]         # set by DevOpsAgent

    feedback: Annotated[List[dict], add]   # appended by each HITL node
    qa_retries: int                        # incremented by QAAgent on fail

    errors: Annotated[List[str], add]      # appended by BaseAgent on exception
    status: str                            # last agent's status string
```

Fields marked `Annotated[List, add]` use LangGraph's reducer: new lists are **appended** to the existing list rather than replacing it. All other fields are replaced on update.

**Important:** All `Optional` fields start as `None`. Always use `state.get(key) or default` — not `state.get(key, default)` — because a `None` value in the dict bypasses the `dict.get` default.

---

## Module map

```
src/
├── agents/
│   ├── base_agent.py          # Abstract base: run() + _process() contract
│   ├── requirements_agent.py  # RequirementAgent
│   ├── architect_agent.py     # ArchitectAgent
│   ├── developer_agent.py     # DeveloperAgent — writes files to workspace/
│   ├── qa_agent.py            # QAAgent — runs pytest on generated code
│   └── devops_agent.py        # DevOpsAgent — generates Dockerfile + CI, pushes PR
│
├── core/
│   └── config.py              # Pydantic BaseSettings — all env vars + paths
│
├── dashboard/
│   └── streamlit_app.py       # UI: sidebar (start), main (HITL review), done state
│
├── exceptions/
│   └── custom_exceptions.py   # SDLCBaseException hierarchy
│
├── logger/
│   └── custom_logger.py       # Loguru setup, per-run file sink
│
├── models/
│   └── schemas.py             # All Pydantic v2 models for structured LLM output
│
├── pipelines/
│   ├── graph.py               # Node functions, routing functions, build_graph()
│   └── state.py               # SDLCState TypedDict, initial_state()
│
├── prompts/
│   ├── requirement_prompt.py
│   ├── architect_prompt.py
│   ├── developer_prompt.py
│   └── devops_prompt.py
│
└── tools/
    ├── llm_factory.py         # Cached ChatOpenAI factory
    ├── test_runner.py         # Subprocess pytest runner → TestReport
    └── mcp_client.py          # GitHub MCP client via langchain_mcp_adapters
```

---

## Data flow through the pipeline

```
initial_state(idea, thread_id)
        │
        ▼
RequirementAgent
  IN:  idea, feedback[]
  OUT: requirements = {project_name, summary, user_stories, non_functional}
        │
        ▼ (after HITL approve)
ArchitectAgent
  IN:  requirements, feedback[]
  OUT: architecture = {stack, components, files, entry_point}
        │
        ▼ (after HITL approve)
DeveloperAgent
  IN:  requirements, architecture, test_report (on retry)
  OUT: codebase = {files: [{path, content}], notes, project_dir}
       → writes files to workspace/<project_name>/
        │
        ▼
QAAgent
  IN:  codebase
  OUT: test_report = {status, passed, failed, errors, raw_output}
       qa_retries += 1 on fail
        │
        ▼ (pass or max retries)
DevOpsAgent
  IN:  architecture, requirements, codebase
  OUT: deployment = {dockerfile, ci_yaml, branch_name, pr_url}
       → writes Dockerfile + .github/workflows/ci.yml to project_dir
       → pushes to GitHub, opens PR
        │
        ▼ (after HITL approve)
END
```

---

## Checkpointing and resumability

LangGraph persists every state snapshot to `.checkpoints/sdlc.sqlite` after each node completes. The `thread_id` (an 8-char UUID prefix) is the key.

```python
# Start a new run
result = graph.invoke(initial_state(idea, thread_id), config={"configurable": {"thread_id": thread_id}})

# Resume after interrupt (HITL)
result = graph.invoke(Command(resume={...}), config={"configurable": {"thread_id": thread_id}})
```

The Streamlit app stores `thread_id` and the compiled `graph` in `st.session_state`, so page reruns reuse the same graph and thread — no re-initialization needed.

---

## Technology choices

| Concern | Choice | Why |
|---------|--------|-----|
| Orchestration | LangGraph | Native HITL, checkpointing, conditional routing |
| LLM provider | OpenAI (via LangChain) | Structured output, broad model support |
| UI | Streamlit | Rapid prototyping, stateful session |
| Checkpoint storage | SQLite | Zero-config, local, durable |
| Config | pydantic-settings | Type-safe `.env` loading |
| Logging | Loguru | Structured context binding, file sinks |
| Packaging | uv | Fast, reproducible dependency resolution |
