# Agents

Every agent in the pipeline is a subclass of `BaseAgent` (`src/agents/base_agent.py`). The base class provides timing, logging (via `logger.bind(agent=<name>)`), exception capture, and context projection. Each agent is a single logical step in the graph and communicates with the next agent via the shared `SDLCState` (and optionally the A2A bus).

---

## Contract

```python
class MyAgent(BaseAgent):
    name = 'my_agent'          # used for logging + status strings
    card = MY_CARD             # a2a agent card, optional
    projection_fn = ContextManager.for_my_agent  # builds a trimmed view of state

    def _process(self, state: SDLCState, projection: dict) -> dict:
        ...
        return {'some_field': ..., 'status': 'my_agent_done'}
```

- `_process` must be pure-ish: no mutation of `state`, return a dict.
- Fields marked `Annotated[List, add]` in `SDLCState` (`feedback`, `errors`, `docs`) **append** instead of replacing.
- Raising an exception is fine — `BaseAgent.run()` catches it and writes `{'errors': [msg], 'status': f'{name}_failed'}`.

---

## Agent directory

### RequirementAgent (`requirements_agent.py`)

Takes the raw `idea` and produces a `Requirements` object: user stories, non-functional requirements, constraints, out-of-scope items.

- **Reads:** `state.idea`
- **Writes:** `state.requirements`
- **Prompt:** `src/prompts/requirement_prompt.py`
- **Schema:** `Requirements`

### ArchitectAgent (`architect_agent.py`)

Turns requirements into a concrete technical design: stack, file layout, entry point, data shapes.

- **Reads:** `state.requirements`, long-term memory (`recall_for_architect`)
- **Writes:** `state.architecture`
- **Prompt:** `src/prompts/architect_prompt.py`
- **Schema:** `Architecture`

### DeveloperAgent (`developer_agent.py`)

Generates the full source tree: code, tests, and a project name. Writes files directly to `workspace/<project_name>/`. Runs agentic RAG (Tavily + Chroma) first so generated code can reference current best practices.

- **Reads:** `state.requirements`, `state.architecture`, `state.code_review` (on retry), `state.test_report` (on retry)
- **Writes:** `state.codebase` (includes `project_dir`), files on disk
- **Prompt:** `src/prompts/developer_prompt.py`
- **Schema:** `Codebase`

### CodeReviewAgent (`code_review_agent.py`)

Static-review pass on the generated codebase. Returns a structured verdict: `passed`, `issues`, `suggested_fixes`. If `passed=False` and `review_retries < MAX_REVIEW_RETRIES`, the graph loops back to the developer with the feedback merged into the prompt.

- **Reads:** `state.codebase`
- **Writes:** `state.code_review`, increments `state.review_retries`
- **Prompt:** `src/prompts/code_review_prompt.py`

### QAAgent (`qa_agent.py`)

Runs `pytest` in the generated project via `TestRunner` (`src/tools/test_runner.py`, uses `sys.executable -m pytest` so the right interpreter is always used). Returns a `TestReport` with pass / fail / error status. Loops back to the developer on failure, bounded by `MAX_QA_RETRIES`.

- **Reads:** `state.codebase.project_dir`
- **Writes:** `state.test_report`, increments `state.qa_retries`
- **Prompt:** none — deterministic subprocess

### DevOpsAgent (`devops_agent.py`)

Generates a `Dockerfile` and `.github/workflows/ci.yml`, creates an isolated branch on the target GitHub repo, pushes every file via the GitHub MCP client, and opens a pull request. Idempotently skips files that are already there (uses blob SHAs when updating).

- **Reads:** `state.codebase`, `state.architecture`
- **Writes:** `state.deployment` (includes `pr_url`, `branch`)
- **Prompt:** `src/prompts/devops_prompt.py`
- **Tools:** `GitHubMCPClient` (`src/tools/github_mcp.py`)

### DocAgent (`doc_agent.py`)

Parameterized by phase — one instance per stage (`DocAgent('requirements')`, `DocAgent('architecture')`, etc.). Generates a Markdown phase report and renders it to PDF with `fpdf2`. When `state.codebase.project_dir` isn't known yet (early phases), it buffers entries in `state.docs` and flushes them to disk the first time a later phase has a `project_dir`.

- **Reads:** the corresponding phase artifact
- **Writes:** `state.docs` (append), files under `workspace/<project>/docs/<phase>.{md,pdf}`
- **Prompt:** `src/prompts/doc_prompt.py`
- **Schema:** `PhaseDocument`

---

## HITL nodes

Three human review gates use `langgraph.types.interrupt`:

| Node | Runs after | Preview contents | Routes on approve | Routes on reject |
|------|-----------|-----------------|-------------------|------------------|
| `hitl_req` | `requirement` | `state.requirements` | `doc_requirements` | back to `requirement` |
| `hitl_arch` | `architect` | `state.architecture` | `doc_architecture` | back to `architect` |
| `hitl_deploy` | `doc_qa` | `codebase` summary + `test_report` status | `devops` | back to `qa` |

`hitl_deploy` deliberately sits **before** `devops` so nothing is pushed to GitHub until the human has approved.

---

## A2A message bus

Agents also emit structured A2A messages (`src/a2a/bus.py`, SQLite-backed). Each sender/receiver pair declares a **card** in `src/a2a/cards.py` describing what tasks it accepts. Messages are persisted, fan-in / fan-out is possible, and the dashboard can tail them for debugging. Agents should:

1. Declare their card in `cards.py`.
2. Set `self.card = MY_CARD` on the subclass.
3. Call `self.a2a.send(...)` when producing an A2A event.

A2A is orthogonal to the LangGraph state-merge flow — think of it as a secondary channel for human-visible events (e.g., `doc_requirements -> human task=review`).

---

## Adding a new agent

1. Subclass `BaseAgent` in `src/agents/<name>_agent.py`.
2. Add a `ChatPromptTemplate` in `src/prompts/<name>_prompt.py`.
3. Add a Pydantic schema to `src/models/schemas.py` if the agent returns structured output.
4. Add an agent card to `src/a2a/cards.py` if the agent participates in A2A messaging.
5. Add a node function + edges in `src/pipelines/graph.py`.
6. Extend `SDLCState` in `src/pipelines/state.py` if the agent writes a new field.
7. Unit-test the agent and any new graph branch in `src/tests/`.

---

## Failure modes

- Any agent raising an exception flows into `state.errors` and routes continue — downstream agents must null-check.
- LLM structured-output failures bubble up as exceptions (by design — they almost always indicate a prompt bug).
- `DevOpsAgent` file-pushes are per-file: one failure doesn't abort the rest, but the `deployment.pr_url` may be missing if branch creation failed. Check `state.errors`.
- QA timeout is 90 seconds (`TestRunner`). Long-running generated suites will fail with `TestRunnerException`.
