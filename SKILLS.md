# SKILLS.md — Tools & Capabilities Reference

Shared tools and utilities used across agents, with usage patterns.

---

## LLMFactory (`src/tools/llm_factory.py`)

A cached factory for `ChatOpenAI` instances. Prevents duplicate client creation across agents.

```python
from src.tools.llm_factory import LLMFactory

llm = LLMFactory.get()                          # default model + temperature from settings
llm = LLMFactory.get(temperature=0.1)           # override temperature only
llm = LLMFactory.get(model="gpt-4o", temperature=0.0)  # override both
```

- Cache key is `(model, temperature)` — same params always returns the same instance
- Raises `LLMToolException` if `OPENAI_API_KEY` is not set
- Model and temperature defaults come from `settings.LLM_MODEL` and `settings.LLM_TEMPERATURE`

### Structured output pattern

All agents use LangChain's `with_structured_output` to get typed responses:

```python
from src.models.schemas import MySchema
from src.prompts.my_prompt import MY_PROMPT

chain = MY_PROMPT | LLMFactory.get().with_structured_output(MySchema)
result: MySchema = chain.invoke({"key": value, ...})
```

The Pydantic schema drives the JSON schema sent to the LLM. Field descriptions in `Field(description=...)` are included in the schema and guide the model.

---

## TestRunner (`src/tools/test_runner.py`)

Runs `pytest` inside a generated project directory and returns a structured `TestReport`.

```python
from src.tools.test_runner import TestRunner
from pathlib import Path

runner = TestRunner(Path("/path/to/generated/project"))
report = runner.run()  # returns TestReport

print(report.status)   # TestStatus.PASS | TestStatus.FAIL | TestStatus.ERROR
print(report.passed)   # int
print(report.failed)   # int
print(report.errors)   # List[str] — error messages
print(report.raw_output)  # full pytest stdout
```

- Runs `pytest` as a subprocess inside the project dir
- Parses pass/fail counts from pytest output
- Returns a `TestReport` Pydantic model (can be `.model_dump()` for state storage)

---

## GitHubMCPClient (`src/tools/mcp_client.py`)

Wraps the GitHub MCP server (via `langchain_mcp_adapters`) to expose GitHub tools as LangChain tools.

```python
from src.tools.mcp_client import GitHubMCPClient

client = GitHubMCPClient()
tools = client.load_tools_sync()  # returns List[BaseTool]
```

Used by `DevOpsAgent` to commit files and open PRs. Requires:
- `GITHUB_PERSONAL_ACCESS_TOKEN` in `.env`
- `GITHUB_REPO_OWNER` and `GITHUB_REPO_NAME` in `.env`
- `GITHUB_MCP_URL` (defaults to `https://api.githubcopilot.com/mcp/`)

The DevOps agent wraps these tools in a LangChain agent and prompts it to commit + open a PR.

---

## Prompt templates (`src/prompts/`)

One file per agent, exporting a `ChatPromptTemplate`:

| File | Export | Used by |
|------|--------|---------|
| `requirement_prompt.py` | `REQUIREMENT_PROMPT` | RequirementAgent |
| `architect_prompt.py` | `ARCHITECT_PROMPT` | ArchitectAgent |
| `developer_prompt.py` | `DEV_PROMPT` | DeveloperAgent |
| `devops_prompt.py` | `DEVOPS_PROMPT` | DevOpsAgent |

Each prompt template includes placeholder variables that match the `.invoke({...})` dict keys passed by the agent. The system prompt for each agent is defined in `src/prompts/system_prompts.py` (referenced by the individual prompt files).

---

## Custom logger (`src/logger/custom_logger.py`)

Loguru-based logger with per-agent context binding:

```python
from src.logger.custom_logger import logger

# Bind agent context (done in BaseAgent.__init__)
self.logger = logger.bind(agent="my_agent")

# Use anywhere
self.logger.info("Started processing")
self.logger.warning("Something non-fatal happened")
self.logger.exception("Exception with traceback")
```

Outputs to both console (with color) and a timestamped log file at `logs/sdlc_run_<timestamp>.log`.

---

## Custom exceptions (`src/exceptions/custom_exceptions.py`)

Hierarchy:

```
SDLCBaseException
├── AgentException
│   └── (per-agent variants)
├── ToolException
│   └── LLMToolException   ← raised by LLMFactory on bad config
└── PipelineException
```

Raise the most specific exception available. `BaseAgent.run()` catches all exceptions generically, so these are primarily useful for debugging and for callers outside the agent framework.

---

## Pydantic schemas (`src/models/schemas.py`)

| Schema | Used for | Key fields |
|--------|----------|------------|
| `Requirements` | Requirements agent output | `project_name`, `summary`, `user_stories`, `non_functional` |
| `UserStory` | Nested in Requirements | `title`, `description`, `acceptance_criteria` |
| `Architecture` | Architect agent output | `stack`, `components`, `files`, `entry_point` |
| `FileSpec` | Nested in Architecture | `path`, `purpose` |
| `Codebase` | Developer agent output | `files` (List[GeneratedFile]), `notes` |
| `GeneratedFile` | Nested in Codebase | `path`, `content` |
| `TestReport` | QA agent output | `status` (TestStatus enum), `passed`, `failed`, `errors`, `raw_output` |
| `TestStatus` | Enum | `PASS`, `FAIL`, `ERROR` |
| `DeploymentArtifacts` | DevOps agent output | `dockerfile`, `ci_yaml`, `branch_name`, `pr_url` |

All schemas are Pydantic v2 `BaseModel` subclasses. Use `.model_dump()` when storing in state (state holds plain dicts).
