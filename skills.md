# Skills & Conventions

Patterns and practices for working in this codebase. If you're extending the pipeline, follow these.

---

## Design principles

1. **Agents know what; the graph knows when.** Agents contain domain logic, not routing. Routing lives in `src/pipelines/graph.py`.
2. **State is a message, not a scratchpad.** Every return value from `_process` is a *merge* into `SDLCState`. Don't mutate the passed-in state — return a dict.
3. **Typed everything.** Agent inputs and outputs are Pydantic models (`src/models/schemas.py`). If you add structured output, add a schema.
4. **Fail loudly, recover gracefully.** Agent exceptions become `state.errors`. Downstream code null-checks and the graph continues. Don't swallow errors inside `_process`.
5. **Small prompts, projected context.** Use `ContextManager` projections so prompts stay focused. Don't dump the whole state into a prompt.

---

## Writing a new agent

```python
# src/agents/my_agent.py
from src.agents.base_agent import BaseAgent
from src.pipelines.context import ContextManager
from src.pipelines.state import SDLCState
from src.prompts.my_prompt import MY_PROMPT
from src.models.schemas import MyResult
from src.tools.llm_factory import LLMFactory

class MyAgent(BaseAgent):
    name = 'my_agent'
    projection_fn = ContextManager.for_my_agent

    def __init__(self):
        super().__init__()
        self._chain = MY_PROMPT | LLMFactory.get(temperature=0.2).with_structured_output(MyResult)

    def _process(self, state: SDLCState, projection: dict) -> dict:
        result: MyResult = self._chain.invoke(projection)
        return {'my_field': result.model_dump(), 'status': 'my_agent_done'}
```

### Rules

- `name` must match the logger binding in downstream code.
- Keep `__init__` cheap — agents are instantiated at module import time.
- Build prompt chains once in `__init__`, not per invocation.
- Return fields, not the whole state.

---

## Prompts

- One file per agent under `src/prompts/`.
- Use `ChatPromptTemplate.from_messages([...])` with explicit `system` / `human` roles.
- Variables in the template must match projection keys exactly. Missing keys raise `INVALID_PROMPT_INPUT`.
- Escape literal curly braces as `{{` / `}}`. A `# {title}` in a system message is an input variable; `# {{title}}` is literal text.
- Keep prompts under ~400 words. Split into a system message (role + constraints) and a human message (inputs).
- No emojis in prompts or generated content unless the user explicitly requests them.

---

## Structured output

Always prefer `with_structured_output(Schema)` over parsing JSON from a string:

```python
chain = PROMPT | LLMFactory.get(temperature=0.2).with_structured_output(MySchema)
result: MySchema = chain.invoke({...})
```

If you need parallel calls, use `RunnableParallel`. If you need to stream, you need `.astream()` on the raw model, not the structured-output chain.

---

## LLM usage

- **Always** call `LLMFactory.get(temperature=...)`. Never `ChatOpenAI(...)` directly.
- Pick temperatures deliberately: `0.0` for deterministic tasks (parsing, extraction), `0.2` for most structured output, `0.4+` only for creative phases (requirements brainstorming).
- The factory caches by `(model, temperature)` — asking for the same pair returns the same client.

---

## Logging

```python
from src.logger.custom_logger import logger

self.logger = logger.bind(agent=self.name)
self.logger.info("...")
```

- Bind the agent name once in `__init__` (or `BaseAgent` does it for you).
- Don't print — use the logger so output ends up in `logs/sdlc_run_<timestamp>.log`.
- Log the *input* intention (`"building requirements for idea: ..."`) not the raw LLM response (that's in the checkpoint).

---

## Configuration

- All settings live in `src/core/config.py` (`Settings(BaseSettings)`).
- Add new fields there; they auto-load from `.env`.
- Never hardcode paths. Use `settings.WORKSPACE_DIR`, `settings.CHECKPOINT_DIR`, etc.
- Boolean flags should default to the safer value (disable-by-default for experimental features).

---

## Testing

- Project-level tests go in `src/tests/`.
- Generated-project tests live with the generated code in `workspace/<project>/tests/`, and are run by `TestRunner`.
- When testing graph routing, avoid hitting real LLMs — mock the agent class or its `_chain`.
- Use `langgraph.checkpoint.memory.InMemorySaver` for graph tests so you don't touch disk.

---

## HITL

Use `langgraph.types.interrupt({...})` inside a plain node function (see `_make_hitl_node` in `graph.py`). The returned value is whatever the resume `Command` provides.

- Every HITL node must include a `phase` key — the UI uses it to pick a renderer.
- Include a `preview` with only the fields a human needs. Don't dump the whole state.
- After the interrupt, append to `state.feedback` (`Annotated[List, add]`), don't replace it.

---

## A2A messaging

If your agent needs to tell another component "here's a milestone":

1. Declare a card in `src/a2a/cards.py` describing what the agent sends / accepts.
2. `self.card = MY_CARD` in the agent.
3. Call `self.a2a.send(to='other_agent', task='task_name', parts=[...])` from `_process`.

A2A is **not** a substitute for state merges — it's for narrative events surfaced to humans and cross-process consumers.

---

## Checkpoints, threads, rewind

- `thread_id` identifies a run. Same id → same checkpoint thread → resume.
- Don't reuse a `thread_id` across logically different runs.
- Use `POST /runs/{thread_id}/rewind` to go back to a checkpoint; the UI can show checkpoints via `GET /runs/{thread_id}/checkpoints`.
- `SqliteSaver` is opened as a context manager in `deps.startup()` and closed in `deps.shutdown()` — don't open a second one in agents.

---

## Generated projects

- Target dir is `settings.WORKSPACE_DIR / <project_name>`. Don't escape the workspace.
- The generated project's tests must be runnable with `pytest` from its root; `TestRunner` uses `sys.executable -m pytest -q --tb=short`.
- Generated `requirements.txt` drives what's installed for the generated project — but `TestRunner` runs in the *agentic-sdlc* interpreter, so any imports the tests need must also exist in this repo's `.venv`.
- Generated `Dockerfile` and `.github/workflows/ci.yml` are templated by `DevOpsAgent`, not the developer.

---

## Extending the graph

- New phases = new node + new edges. Prefer **conditional** edges for loops; linear edges for happy paths.
- Bound every retry loop with a counter field in `SDLCState` and a `MAX_*_RETRIES` setting.
- HITL nodes **must** run *before* any side effect that a human might want to block (pushing to GitHub, spending money, deleting files). See `hitl_deploy` as the canonical example.

---

## Security / secrets

- Secrets (`OPENAI_API_KEY`, `GITHUB_PERSONAL_ACCESS_TOKEN`, `TAVILY_API_KEY`) come from `.env` → `Settings`. Never commit them.
- Don't log secret values; `Settings` fields typed as `SecretStr` render as `**********`.
- GitHub pushes use an isolated branch per run — not main — and open a PR for human review.

---

## Common mistakes to avoid

- `state.get('foo', default)` when `foo` is explicitly `None`. Use `state.get('foo') or default`.
- Forgetting to escape `{` in prompts when you mean a literal brace.
- Mutating the input `state` instead of returning a dict.
- Instantiating heavy clients inside `_process` (the graph re-enters nodes — this would create duplicate clients and burn tokens).
- Hardcoding paths or model names. Route everything through `settings` and `LLMFactory`.
- Reusing a `thread_id` across unrelated runs.
