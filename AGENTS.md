# AGENTS.md — Agent Reference

This document describes every agent in the pipeline, the BaseAgent contract, HITL nodes, and routing logic.

---

## BaseAgent (`src/agents/base_agent.py`)

All agents extend `BaseAgent`. The contract is:

```
run(state: SDLCState) -> dict
  └─ calls _process(state) -> dict
       └─ must be implemented by subclass
```

- `run()` handles timing, logging, and exception catching. On any exception it returns `{'errors': [msg], 'status': f'{self.name}_failed'}` without raising.
- `_process()` is where the agent's logic lives. It receives the full `SDLCState` and returns a **partial dict** to merge into state.
- Each agent binds a logger: `self.logger = logger.bind(agent=self.name)`.

**Important:** Because `run()` catches all exceptions, downstream agents must handle the case where upstream fields are `None`. Check `state.get("codebase")` before using it.

---

## Pipeline agents

### RequirementAgent (`src/agents/requirements_agent.py`)

**Trigger:** First node after `START`  
**Input state fields:** `idea`, `feedback` (previous rejection comments)  
**Output:** `requirements` (dict matching `Requirements` schema), `status`

Takes the raw idea string and any previous HITL rejection feedback, calls the LLM with `REQUIREMENT_PROMPT`, and returns structured requirements including `project_name` (kebab-case), `summary`, `user_stories`, and `non_functional` constraints.

Loops back to itself if the HITL node rejects the output.

---

### ArchitectAgent (`src/agents/architect_agent.py`)

**Trigger:** After requirements HITL approves  
**Input state fields:** `requirements`, `feedback`  
**Output:** `architecture` (dict matching `Architecture` schema), `status`

Designs the project's technical architecture: stack choices, component list, file specifications (path + purpose), and the entry point command. Loops back on HITL rejection.

---

### DeveloperAgent (`src/agents/developer_agent.py`)

**Trigger:** After architecture HITL approves, or after QA fails (retry loop)  
**Input state fields:** `requirements`, `architecture`, `test_report` (on retry)  
**Output:** `codebase` (dict with all generated files + `project_dir`), `status`

- Invokes `DEV_PROMPT` with requirements, architecture, and any QA failure feedback
- Uses `with_structured_output(Codebase)` — gets back a list of `GeneratedFile` objects
- Writes every file to `workspace/<project_name>/`
- On a QA retry, `_build_qa_feedback()` extracts the failing test errors and injects them into the prompt

---

### QAAgent (`src/agents/qa_agent.py`)

**Trigger:** After DeveloperAgent  
**Input state fields:** `codebase`  
**Output:** `test_report` (dict matching `TestReport` schema), `qa_retries`, `status`

- Guards against `None` codebase (returns fail report immediately if developer failed)
- Installs `requirements.txt` from the generated project via `pip install`
- Delegates to `TestRunner` which runs `pytest` in the project directory
- Increments `qa_retries` on failure
- Returns `status` as `qa_pass` or `qa_fail`

---

### DevOpsAgent (`src/agents/devops_agent.py`)

**Trigger:** After QA passes, or after max QA retries are exhausted  
**Input state fields:** `architecture`, `requirements`, `codebase`  
**Output:** `deployment` (dict with Dockerfile, CI YAML, branch name, PR URL), `status`

- Generates a `Dockerfile` and `.github/workflows/ci.yml` using `DEVOPS_PROMPT`
- Writes those files into the generated project directory
- Uses `GitHubMCPClient` + a LangChain agent to commit the project to a new branch and open a PR
- The MCP push is non-fatal — if it fails, the run continues without a PR URL

---

## HITL nodes

Three human-in-the-loop nodes pause the graph and wait for a `Command(resume={...})`:

| Node | Phase key | Preview key | Appears after |
|------|-----------|-------------|---------------|
| `hitl_req` | `requirements` | `requirements` | RequirementAgent |
| `hitl_arch` | `architecture` | `architecture` | ArchitectAgent |
| `hitl_deploy` | `deployment` | `deployment` | DevOpsAgent |

Each HITL node calls `interrupt({phase, preview, message})` and expects a resume payload:
```python
{"verdict": "approve" | "reject", "comment": "optional feedback string"}
```

The verdict and comment are appended to `state["feedback"]` as `{phase, verdict, comment}`.

---

## Routing functions

### `route_after_hitl_req(state)`
- `approve` → `architect`
- `reject` → `requirement` (loops back with feedback)

### `route_after_hitl_arch(state)`
- `approve` → `developer`
- `reject` → `architect` (loops back with feedback)

### `route_after_qa(state)`
- `test_report.status == 'pass'` → `devops`
- `qa_retries >= MAX_QA_RETRIES` → `devops` (gives up, proceeds anyway)
- otherwise → `developer` (retry loop)

`MAX_QA_RETRIES` defaults to `2` and is set in `src/core/config.py`.

### `route_after_hitl_deploy(state)`
- `approve` → `END`
- `reject` → `devops` (regenerates deployment artifacts)

---

## QA retry loop

```
developer → qa ──pass──→ devops
              └──fail──→ developer (max 2 retries, then devops anyway)
```

The developer agent reads `state["test_report"]` on retries. `_build_qa_feedback()` returns `'none'` on first run or if tests passed, and returns the failure error list on retries.
