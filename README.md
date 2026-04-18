# SDLC Agents

> **An autonomous-but-supervised virtual engineering team.**
> Submit an idea, watch a pipeline of specialized AI agents produce requirements → design → code → tests → deployment, with human approval gates at every phase and a retrieval layer that lets the system learn from every run.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Types: mypy strict](https://img.shields.io/badge/types-mypy%20strict-blue.svg)](http://mypy-lang.org/)

---

## Table of Contents

- [What This Is](#what-this-is)
- [Why It Exists](#why-it-exists)
- [How It Works](#how-it-works)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [The Agents](#the-agents)
- [The Retrieval Layer (RAG)](#the-retrieval-layer-rag)
- [MCP Integration](#mcp-integration)
- [Human-in-the-Loop (HITL)](#human-in-the-loop-hitl)
- [Running a Workflow](#running-a-workflow)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Observability & Debugging](#observability--debugging)
- [Configuration Reference](#configuration-reference)
- [Build Roadmap](#build-roadmap)
- [Runbook](#runbook)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## What This Is

**SDLC Agents** is a multi-agent system that automates the full Software Development Life Cycle. Six specialized agents — Requirement, Architect, Developer, QA, DevOps, and Critic — collaborate through a typed message protocol, act via hosted MCP servers, reason over five domain-specific RAG corpora, and pause for human review at every phase gate.

It is not an "AI that writes code." It is a durable, stateful, supervised engineering pipeline with:

- **Real infrastructure** (Postgres for checkpoints, Qdrant for vectors, Redis for cache and streams)
- **Real side effects** (GitHub PRs, CI runs, deployments — via MCP)
- **Real guardrails** (HITL gates, least-privilege tool access, idempotent operations, retry policies)
- **Real learning** (every workflow writes back into past-projects and feedback corpora for next time)

This repository contains the **foundational scaffold and the Claude Code bootstrap prompt**. Claude Code builds the agent layer, retrieval pipelines, and HITL UI on top of these foundations in nine disciplined phases (see [Build Roadmap](#build-roadmap)).

---

## Why It Exists

Existing "AI codes your app" tools produce demos but fall over in real engineering contexts because they:

1. **Skip the SDLC phases that matter** — no requirements gathering, no architectural thinking, just code generation.
2. **Have no memory** — each request starts from zero, no learning across projects.
3. **Have no human oversight** — reviewers can't intervene mid-flight at the phases where intervention matters most.
4. **Can't recover from failure** — a mid-pipeline crash loses everything.
5. **Hallucinate tool calls and library APIs** — parametric LLM knowledge is always stale.

SDLC Agents addresses each of these:

| Problem | Solution |
|---------|----------|
| No phases | Explicit 6-agent pipeline mirroring a real engineering team |
| No memory | Five RAG corpora covering past projects, live code, library docs, patterns, feedback |
| No oversight | Mandatory HITL gates after Requirements, Design, Dev+QA, and Deploy |
| No recovery | LangGraph checkpointing — resume from any past state |
| Tool hallucination | MCP — tools are discovered dynamically, never invented |
| API hallucination | Library docs RAG filtered to the exact versions the Architect chose |

---

## How It Works

A run proceeds through five SDLC phases, each gated by a human approval:

```
User idea
    │
    ▼
┌─────────────────┐
│ Requirement     │ ──── retrieves: past_projects, feedback
│ Agent           │ ──── writes: Requirements
└────────┬────────┘
         │  ✋ HITL gate
         ▼
┌─────────────────┐
│ Architect       │ ──── retrieves: past_projects, patterns, feedback
│ Agent           │ ──── writes: Design, active_libraries
└────────┬────────┘
         │  ✋ HITL gate
         ▼
┌─────────────────┐
│ Developer       │ ──── retrieves: live_code, lib_docs, patterns
│ Agent (subgraph)│ ──── writes: CodebaseRef (via GitHub MCP)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ QA Agent        │ ──── retrieves: live_code, lib_docs, patterns
│                 │ ──── writes: TestResults
└────────┬────────┘
         │ fail? → back to Developer (≤3 retries)
         │  ✋ HITL gate
         ▼
┌─────────────────┐
│ DevOps Agent    │ ──── retrieves: lib_docs, patterns
│                 │ ──── writes: DeploymentStatus
└────────┬────────┘
         │  ✋ HITL gate
         ▼
    Deployed App
```

The **Critic Agent** runs alongside — not between — phases, scoring outputs and looping a phase back if the score falls below threshold. Every retrieval is logged to `RetrievalTrace` for evaluation. Every state transition is checkpointed so a crash or intentional pause loses nothing.

---

## Architecture at a Glance

The system is organized into four planes:

### 1. Control Plane — LangGraph
A `StateGraph` parameterized by `SDLCState`. Nodes are agents + `human_gate` nodes. Edges are conditional routers inspecting state. Compiled with `PostgresSaver` for checkpointing and `interrupt_before` for HITL.

### 2. Agent Plane — Six Specialists
Each agent follows the same anatomy: `plan_retrieval → fetch_retrieval → build_prompt → call_llm → parse_output → emit_A2A_message → write_checkpoint`. Agents never call each other directly — they read and write structured `A2AMessage` objects through shared state.

### 3. Tool Plane — Hosted MCP Servers
All real-world side effects route through MCP. `MCPClientManager` opens client sessions at startup; `ToolRegistry` enforces per-agent tool allow-lists. Tools appear to agents as LangChain `BaseTool` instances.

### 4. Retrieval Plane — Five RAG Corpora
Five Qdrant collections, each with its own chunking strategy, embedding model, and refresh cadence. Agents query a typed `RetrievalService`; they never see Qdrant directly.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design spec.

---

## Key Features

- **🎭 Six specialist agents** with distinct roles, tools, and retrieval sources
- **🗣️ A2A protocol** — typed JSON message envelope with mandatory context summarization (prevents token explosion)
- **🔌 MCP-first tool use** — every external action goes through a hosted MCP server; no tool hallucination
- **🧠 Five-corpus RAG** — live code, past projects, library docs, curated patterns, human feedback
- **🔀 Hybrid search** — dense (Voyage) + sparse (BM25) + Cohere Rerank v3 for top-tier retrieval quality
- **🌳 AST-aware code chunking** — tree-sitter keeps function boundaries intact in the `live_code` corpus
- **✋ Mandatory HITL gates** — four approval points; rejections flow back with feedback context
- **💾 Full checkpointing** — LangGraph + Postgres; pause, resume, replay, rollback any workflow
- **🔁 Bounded retry loops** — QA→Dev (3x), HITL rejection (5x), Critic low-score (2x); escalation beyond
- **🛡️ Prompt-injection defenses** — A2A summarizer sanitizes outputs before they become downstream context
- **🔐 Least-privilege tools** — `ToolRegistry` enforces per-agent allow-lists (Architect gets zero MCP tools)
- **📊 Built-in observability** — LangSmith traces, structlog JSON logs, per-retrieval telemetry
- **📏 RAG evaluation harness** — RAGAS metrics per corpus with curated test sets
- **⚡ Full async** — all I/O paths are async (MCP, Qdrant, LLMs, Redis, Postgres)
- **🧪 Strict typing** — mypy strict mode, full Pydantic v2 validation

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Language | Python 3.11+ |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| Orchestration | [LangGraph](https://langchain-ai.github.io/langgraph/) |
| LLM interface | LangChain + `langchain-anthropic` (primary), `langchain-openai` (fallback) |
| LLM providers | Claude (Opus/Sonnet), GPT-4 |
| Tool protocol | [MCP](https://modelcontextprotocol.io/) via `mcp` SDK + `langchain-mcp-adapters` |
| Vector DB | [Qdrant](https://qdrant.tech/) (hybrid search native) |
| Embeddings | [Voyage AI](https://www.voyageai.com/) (`voyage-code-3`, `voyage-3-large`) |
| Reranker | [Cohere Rerank v3](https://cohere.com/rerank) |
| Code chunking | [tree-sitter](https://tree-sitter.github.io/) + `tree-sitter-languages` |
| Doc parsing | `unstructured`, `markdownify` |
| Checkpointer | `langgraph-checkpoint-postgres` (prod) / `-sqlite` (dev) |
| HITL API | FastAPI + `sse-starlette` |
| Dashboard | Streamlit (MVP) / Next.js (prod) |
| Validation | Pydantic v2 |
| Config | `pydantic-settings` + YAML |
| Cache | Redis |
| Logging | `structlog` (JSON) |
| Tracing | LangSmith |
| Retries | `tenacity` |
| CLI | `click` / `typer` |
| Testing | `pytest`, `pytest-asyncio`, `pytest-cov` |
| Evaluation | `ragas` |
| Lint / format | `ruff` |
| Types | `mypy` strict |

---

## Prerequisites

### System
- **Python 3.11 or newer** — `python3 --version`
- **Docker & Docker Compose** — for Postgres, Qdrant, Redis
- **[uv](https://github.com/astral-sh/uv)** — install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Git** — for version control and the GitHub MCP integration

### API Keys (required)
- **[Anthropic](https://console.anthropic.com/)** — for Claude models
- **[Voyage AI](https://dash.voyageai.com/)** — for embeddings (free tier covers development)
- **[Cohere](https://dashboard.cohere.com/)** — for rerank-v3 (free tier covers development)

### API Keys (optional but recommended)
- **[OpenAI](https://platform.openai.com/)** — fallback LLM provider
- **[LangSmith](https://smith.langchain.com/)** — agent tracing (invaluable for debugging)
- **[GitHub Personal Access Token](https://github.com/settings/tokens)** — for the GitHub MCP server

---

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <your-repo-url> sdlc-agents
cd sdlc-agents

# 2. Copy the env template and fill in your API keys
cp .env.example .env
$EDITOR .env
#   Required: ANTHROPIC_API_KEY, VOYAGE_API_KEY, COHERE_API_KEY
#   Recommended: LANGSMITH_API_KEY, MCP_GITHUB_TOKEN

# 3. Install dependencies
make install
#   Equivalent to: uv sync --all-extras

# 4. Start infrastructure (Postgres + Qdrant + Redis)
make infra-up

# 5. Verify everything is reachable
make healthcheck
#   You should see three green checkmarks.

# 6. Hand the bootstrap prompt to Claude Code
#    Open Claude Code in this directory, then paste CLAUDE_CODE_PROMPT.md
#    as your first message. Follow the phased build plan from there.
```

If `make healthcheck` fails, **stop and fix it before proceeding.** You cannot debug agent loops against broken infrastructure.

---

## Project Structure

```
sdlc-agents/
├── CLAUDE_CODE_PROMPT.md         # Bootstrap prompt for Claude Code
├── ARCHITECTURE.md               # Authoritative system design
├── README.md                     # This file
├── pyproject.toml                # Deps + ruff/mypy/pytest config
├── Makefile                      # Common dev commands
├── docker-compose.yml            # Postgres + Qdrant + Redis
├── .env.example                  # Env var template
├── .gitignore
│
├── configs/                      # YAML runtime configs
│   ├── mcp_servers.yaml          # Hosted MCP servers + per-agent allow-lists
│   └── retrieval.yaml            # Per-corpus retrieval config
│
├── src/sdlc_agents/
│   ├── __init__.py
│   ├── main.py                   # CLI entrypoint (click)
│   ├── config.py                 # pydantic-settings loader
│   │
│   ├── state/                    # Global state schema
│   │   ├── schema.py             # SDLCState TypedDict + nested models
│   │   └── enums.py              # Phase, WorkflowStatus, AgentName
│   │
│   ├── a2a/                      # Agent-to-Agent protocol
│   │   ├── message.py            # A2AMessage envelope
│   │   └── summarizer.py         # Context compressor (injection-hardened)
│   │
│   ├── mcp_clients/              # MCP plumbing
│   │   ├── manager.py            # MCPClientManager (session lifecycle)
│   │   ├── registry.py           # ToolRegistry (least-privilege allow-lists)
│   │   └── transports.py         # StreamableHTTP / SSE helpers
│   │
│   ├── retrieval/                # RAG layer
│   │   ├── service.py            # Agent-facing RetrievalService
│   │   ├── corpora/              # One file per corpus
│   │   ├── embeddings/           # Voyage + OpenAI providers
│   │   ├── chunking/             # AST, semantic, hierarchical
│   │   ├── retrievers/           # Hybrid + reranker + query expansion
│   │   ├── store/                # Qdrant wrapper
│   │   └── cache.py              # Redis query cache
│   │
│   ├── indexing/                 # Corpus pipelines
│   │   ├── pipelines/            # Per-corpus indexing jobs
│   │   ├── events.py             # Redis Streams consumer
│   │   └── scheduler.py          # Prefect / Dagster entry
│   │
│   ├── agents/                   # The six specialists
│   │   ├── base.py               # BaseAgent abstract class
│   │   ├── requirement_agent.py
│   │   ├── architect_agent.py
│   │   ├── developer_agent.py    # Implemented as a sub-graph
│   │   ├── qa_agent.py
│   │   ├── devops_agent.py
│   │   └── critic_agent.py
│   │
│   ├── prompts/                  # Markdown agent prompts (versioned)
│   │   ├── requirement.md
│   │   ├── architect.md
│   │   └── ...
│   │
│   ├── memory/                   # Session + artifact stores
│   │   ├── short_term.py         # Checkpointer setup
│   │   └── artifacts.py          # Artifact store abstraction
│   │
│   ├── orchestration/            # LangGraph wiring
│   │   ├── graph.py              # StateGraph builder
│   │   ├── edges.py              # Conditional routers
│   │   ├── nodes.py              # Node wrappers
│   │   ├── interrupts.py         # HITL interrupt logic
│   │   └── subgraphs/            # Developer sub-graph (agentic retrieval)
│   │
│   ├── hitl/                     # Human approval API + UI
│   │   ├── api.py                # FastAPI routes
│   │   ├── schemas.py            # Request/response models
│   │   ├── events.py             # SSE streaming
│   │   └── dashboard/            # Streamlit app
│   │
│   ├── evaluation/               # Eval harnesses
│   │   ├── retrieval/            # RAGAS runners per corpus
│   │   └── end_to_end/
│   │
│   ├── observability/            # Tracing + logging
│   │   ├── tracing.py            # LangSmith setup
│   │   ├── logging.py            # structlog config
│   │   └── retrieval_telemetry.py
│   │
│   └── utils/
│       ├── retries.py            # tenacity policies
│       └── idempotency.py
│
├── tests/
│   ├── unit/
│   ├── integration/              # Requires `make infra-up`
│   └── e2e/                      # Full pipeline runs
│
├── scripts/
│   ├── healthcheck.py            # Verify infra is reachable
│   ├── seed_patterns.py          # Load curated patterns
│   ├── rebuild_lib_docs.py       # Manual lib docs reindex
│   ├── replay_workflow.py        # Replay from checkpoint
│   └── run_retrieval_eval.py     # Full eval suite
│
└── docs/
    ├── adr/                      # Architecture decision records
    ├── patterns/                 # Source markdown for patterns corpus
    └── runbook.md                # Ops procedures
```

---

## The Agents

Each agent has a clearly defined role, input/output contract, and retrieval/tool access.

### 1. Requirement Agent (Product Manager)
- **Input:** Raw user idea
- **Output:** `Requirements` (user stories, acceptance criteria, NFRs, constraints)
- **Retrieval:** `past_projects` (domain-filtered), `feedback`
- **MCP tools:** None (read-only reasoning)

### 2. Architect Agent
- **Input:** Approved `Requirements`
- **Output:** `Design` (components, tech stack, data models, API contracts, ADRs) + `active_libraries`
- **Retrieval:** `past_projects`, `patterns`, `feedback`
- **MCP tools:** None

### 3. Developer Agent ⭐
- **Input:** Approved `Design`
- **Output:** `CodebaseRef` (repo URL, branch, commit SHA, PR number, file list)
- **Retrieval:** `live_code` (own output so far), `lib_docs` (version-filtered), `patterns`
- **MCP tools:** `github.*`, `filesystem.*`
- **Implementation:** A LangGraph sub-graph with a ReAct loop exposing retrieval as tools (**agentic retrieval**)

### 4. QA Agent
- **Input:** `CodebaseRef`
- **Output:** `TestSuite`, `TestResults`
- **Retrieval:** `live_code`, `lib_docs`, `patterns` (tagged `testing`)
- **MCP tools:** `filesystem.*`, `code_exec.*`, `github_actions.*`
- **On failure:** emits A2A message back to Developer with structured failure details (up to 3 retries)

### 5. DevOps Agent
- **Input:** Passing `TestResults` + `CodebaseRef`
- **Output:** `DeploymentStatus`
- **Retrieval:** `lib_docs` (Docker/CI), `patterns` (tagged `deployment`)
- **MCP tools:** `github.*` (workflow files), `deploy.*`
- **Approach:** Template-heavy; MCP triggers deployment and validates health check

### 6. Critic Agent (Cross-Phase Reviewer)
- **Runs:** After every agent output (in parallel with the next agent where possible)
- **Output:** `CriticScore` (0–10) + structured findings
- **Retrieval:** `patterns`, `feedback`, `past_projects` (success_score > 8)
- **MCP tools:** None
- **On low score:** Triggers phase rerun with critique appended to feedback

---

## The Retrieval Layer (RAG)

Five independent Qdrant collections, each with its own pipeline:

| Corpus | Purpose | Chunking | Embedding | Refresh | Consumers |
|--------|---------|----------|-----------|---------|-----------|
| `live_code` | Consistency across files the Developer writes | AST (tree-sitter) + contextual blurbs | `voyage-code-3` + BM25 | Incremental on file-write event | Developer (primary), QA, Critic |
| `past_projects` | Learn from completed workflows | Document-section semantic | `voyage-3-large` | On workflow completion | Architect, Critic |
| `lib_docs` | Current library/framework APIs (version-aware) | Hierarchical, 500–1000 tokens | `voyage-3-large` + BM25 | Weekly scheduled | Developer, QA |
| `patterns` | Curated best practices, anti-patterns, checklists | One chunk per pattern | `voyage-3-large` | Manual / git-driven | Critic, Architect |
| `feedback` | HITL rejections + Critic findings | Whole entries | `voyage-3-large` | Real-time | All agents |

All retrievals use: **hybrid (dense + sparse) → Cohere Rerank v3 → top-K (default 5)**.

**Advanced techniques applied:**
- **Contextual Retrieval** (`live_code`, `past_projects`): LLM-generated situating blurbs prepended to chunks before embedding
- **Query Expansion** (`lib_docs`): rewrite the agent's raw query into library-likely terms before retrieval
- **Agentic Retrieval** (Developer): retrieval exposed as a tool inside the Developer sub-graph's ReAct loop
- **Recency Boost** (`feedback`): recent feedback out-ranks old (team preferences drift)

Every retrieval is logged to `state.retrieval_traces` with query, corpus, scores, and latency — feeding the RAGAS evaluation harness.

---

## MCP Integration

### How agents use tools

1. At startup, `MCPClientManager` reads `configs/mcp_servers.yaml` and opens a persistent Streamable HTTP session to each enabled server.
2. For each session, it calls `session.list_tools()` to discover available tools.
3. `langchain_mcp_adapters.tools.load_mcp_tools(session)` converts MCP tool definitions into LangChain `BaseTool` instances.
4. `ToolRegistry` filters tools per agent based on `agent_tool_permissions` (least privilege).
5. Agents bind their allowed tools via `llm.bind_tools(tools)`.

### Configuration

Edit `configs/mcp_servers.yaml`:

```yaml
servers:
  - name: github
    url: https://api.githubcopilot.com/mcp/
    transport: streamable_http
    auth_env: MCP_GITHUB_TOKEN
    enabled: true

agent_tool_permissions:
  developer:
    - github
    - filesystem
  qa:
    - filesystem
    - code_exec
    - github
  # Agents NOT listed get ZERO tools.
```

### Guarantees

- **No tool hallucination** — only tools surfaced by `session.list_tools()` are callable
- **Least privilege** — Architect, Requirement, and Critic have zero MCP tools
- **Idempotency** — every mutating call includes a key: `f"{trace_id}:{phase}:{artifact_id}"`
- **HITL gates upstream** — destructive actions (deploy, force-push) are always preceded by a human approval

---

## Human-in-the-Loop (HITL)

HITL gates fire after:

1. **Requirements** — before the Architect starts
2. **Design** — before the Developer starts
3. **Dev + QA** — before DevOps starts (code and tests both pass)
4. **Deploy confirmation** — before production promotion

### At each gate the human sees

- The raw output (design doc, PR link, test report, …)
- An LLM-generated summary
- The agent's reasoning trace (LangSmith link)
- An approve / reject + feedback form

### Flow

- **Approve:** graph resumes at the next node
- **Reject:** feedback appended to `state.feedback` + written to the `feedback` corpus in real-time + graph loops back to the same agent with feedback context (bounded to 5 rejections per phase)

### Interface

- **CLI** (dev): `sdlc run "your idea"` presents approval prompts on stdout
- **FastAPI + SSE** (prod): `POST /workflows`, `GET /workflows/{id}/pending`, `POST /workflows/{id}/decide`, SSE on `/workflows/{id}/events`
- **Streamlit dashboard**: polls or subscribes to the SSE stream

---

## Running a Workflow

```bash
# Start a new workflow from an idea
uv run sdlc run "Build a URL shortener with click analytics"
# → prints thread_id, pauses at first HITL gate

# List active workflows
uv run sdlc list

# Check status
uv run sdlc status <thread_id>

# Approve the current gate
uv run sdlc approve <thread_id>

# Reject with feedback
uv run sdlc reject <thread_id> --feedback "Need to support custom domains"

# Resume after a process restart
uv run sdlc resume <thread_id>

# Replay from a past checkpoint
uv run sdlc replay <thread_id> --from-step 3

# Inspect state history
uv run sdlc history <thread_id>
```

### HTTP API (once Phase 8 is built)

```bash
# Kickoff
curl -XPOST localhost:8000/workflows -d '{"idea": "URL shortener with analytics"}'

# Pending gate
curl localhost:8000/workflows/<thread_id>/pending

# Decide
curl -XPOST localhost:8000/workflows/<thread_id>/decide \
  -d '{"decision": "approve"}'

# Live event stream
curl -N localhost:8000/workflows/<thread_id>/events
```

---

## Development Workflow

### Common commands

```bash
make install          # uv sync --all-extras
make infra-up         # start Postgres + Qdrant + Redis
make infra-down       # stop infra
make infra-logs       # tail infra logs
make healthcheck      # verify all three services reachable

make format           # ruff format + autofix
make lint             # ruff check
make typecheck        # mypy strict
make test             # all tests
make test-unit        # unit only
make test-integration # integration (requires infra)
make eval             # RAGAS retrieval eval
make clean            # remove caches
```

### Pre-commit checklist

```bash
make format && make lint && make typecheck && make test-unit
```

All four must pass before committing. Configure your editor to run `ruff format` on save.

### Conventional commits

Use `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` prefixes. Example:

```
feat(retrieval): add contextual blurb generator for live_code corpus

Prepends an LLM-generated 1-2 sentence situating blurb to each code
chunk before embedding. Improves retrieval accuracy on intent-based
queries. Uses the cheap model for cost control.
```

---

## Testing

### Layers

| Layer | Location | Runs | Requires |
|-------|----------|------|----------|
| Unit | `tests/unit/` | Pure logic, no I/O | Nothing |
| Integration | `tests/integration/` | One subsystem + real infra | `make infra-up` |
| End-to-end | `tests/e2e/` | Full pipeline runs | Infra + API keys |

### Running

```bash
make test-unit                              # fast, always runs
make test-integration                       # needs infra up
uv run pytest -m "not e2e" -v               # everything except e2e
uv run pytest tests/unit/test_state/ -v     # target a specific module
uv run pytest -k "retrieval and not slow"   # keyword filter
```

### Coverage

Unit test coverage target is **≥80%**. Coverage report appears after every `make test`:

```
---------- coverage: platform linux, python 3.11.x ----------
Name                                     Stmts   Miss  Cover   Missing
----------------------------------------------------------------------
src/sdlc_agents/state/schema.py            142      0   100%
src/sdlc_agents/a2a/summarizer.py           38      2    95%   67-68
...
```

### Retrieval evaluation

The system ships with curated test sets in `src/sdlc_agents/evaluation/retrieval/test_sets/`. RAGAS computes:

- **Context precision** — of retrieved chunks, fraction relevant
- **Context recall** — of relevant chunks that exist, fraction retrieved
- **Faithfulness** — is the generated answer grounded in retrieved context

```bash
make eval
# →
# Corpus          Precision  Recall  Faithfulness  Latency (p50)
# live_code       0.87       0.82    0.94          142 ms
# past_projects   0.79       0.88    0.91          118 ms
# lib_docs        0.91       0.84    0.96          156 ms
# patterns        0.93       0.90    0.97           98 ms
# feedback        0.88       0.85    0.93           72 ms
```

Run this on every retrieval-layer change; fail the build if any metric drops >5% from baseline.

---

## Observability & Debugging

### LangSmith Tracing (strongly recommended)

Set in `.env`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=sdlc-agents-dev
```

Every LLM call, tool call, retrieval call, and graph transition appears at [smith.langchain.com](https://smith.langchain.com/). When an agent does something weird, LangSmith is usually the fastest path to understanding why.

### Structured logging

All logs are JSON via `structlog`. Every log line carries `trace_id`, `thread_id`, `agent`, `phase` so you can filter across agents:

```bash
# Tail logs for a specific workflow
uv run sdlc logs <thread_id>

# Filter by agent
uv run sdlc logs <thread_id> --agent developer

# Filter by phase
uv run sdlc logs <thread_id> --phase qa
```

### Retrieval telemetry

Every retrieval is logged to `state.retrieval_traces` (query, corpus, chunks returned, scores, latency). Inspect via:

```bash
uv run sdlc retrievals <thread_id>
# → table of every retrieval: agent, corpus, query, top score, latency
```

### Metrics (Prometheus export)

- `sdlc_agent_duration_seconds{agent, phase}`
- `sdlc_retry_count{phase, reason}`
- `sdlc_critic_score{phase}`
- `sdlc_retrieval_latency_seconds{corpus, quantile}`
- `sdlc_retrieval_hit_rate{corpus}`
- `sdlc_hitl_approval_rate{phase}`

---

## Configuration Reference

### Environment variables (`.env`)

See `.env.example` for the full list with documentation. Required keys:

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude models |
| `VOYAGE_API_KEY` | Embeddings |
| `COHERE_API_KEY` | Rerank |
| `QDRANT_URL` | Vector DB (default `http://localhost:6333`) |
| `POSTGRES_URL` | Checkpoint store |
| `REDIS_URL` | Cache + streams |

Optional:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SDLC_DEFAULT_MODEL` | `claude-sonnet-4-5` | Main agent model |
| `SDLC_CHEAP_MODEL` | `claude-haiku-4-5` | Summarizer / query expansion |
| `SDLC_CHECKPOINTER` | `sqlite` | `sqlite` (dev) or `postgres` (prod) |
| `RETRIEVAL_TOP_K` | `5` | Final K after rerank |
| `RETRIEVAL_INITIAL_K` | `20` | K before rerank |
| `RETRIEVAL_MAX_CONTEXT_TOKENS` | `4000` | Budget per retrieval call |
| `RETRIEVAL_CACHE_TTL_SECONDS` | `3600` | Redis cache TTL |

### YAML configs

- **`configs/mcp_servers.yaml`** — hosted MCP servers + per-agent permissions
- **`configs/retrieval.yaml`** — per-corpus chunking, embeddings, retrieval params

Both are hot-reloadable in dev (via `sdlc config reload`) and immutable in prod.

---

## Build Roadmap

The project builds in **nine strict phases**. Do not skip ahead.

| Phase | What | Checkpoint |
|-------|------|------------|
| **0** | Environment bootstrap | `make healthcheck` passes |
| **1** | State schema + A2A protocol | Unit tests pass |
| **2** | MCP client plumbing | Can list + call a tool from a real MCP server |
| **3** | Retrieval service + `patterns` corpus | Seed and query returns sensible chunks |
| **4** | First 2 agents + graph + CLI HITL | `sdlc run "..."` flows Requirement → HITL → Architect → HITL → exit |
| **5** | Developer agent + `live_code` corpus + indexing | Developer writes a 3-file app with consistent style |
| **6** | QA + DevOps + Critic | Full happy path end-to-end integration test passes |
| **7** | Remaining corpora + evaluation | `make eval` reports metrics per corpus |
| **8** | FastAPI HITL + Streamlit dashboard | Run a workflow entirely from the web UI |
| **9** | Hardening | Idempotency, retries, security audit, Docker image |

Each phase ends with a **✋ checkpoint** — a concrete verification command. Do not start phase N+1 until N's checkpoint passes.

See [`CLAUDE_CODE_PROMPT.md`](CLAUDE_CODE_PROMPT.md) for the full prompt with per-phase file manifests and instructions for Claude Code.

---

## Runbook

### Reset everything (dev)

```bash
docker compose down -v     # also drops volumes
make infra-up
make healthcheck
```

### Inspect a checkpoint

```python
from sdlc_agents.orchestration.graph import build_graph
graph = build_graph()
state = graph.get_state({"configurable": {"thread_id": "<id>"}})
print(state.values["current_phase"], state.next)
```

### Replay from a past step

```bash
uv run sdlc history <thread_id>              # see all checkpoints
uv run sdlc replay <thread_id> --step 3      # restart from step 3
```

### Reindex the `lib_docs` corpus

```bash
uv run python scripts/rebuild_lib_docs.py --library fastapi --version 0.115
```

### Backup checkpoints (Postgres)

```bash
pg_dump postgresql://sdlc:sdlc@localhost:5432/sdlc_agents > backup.sql
```

### Add a new library to `lib_docs`

1. Add an entry to `configs/libraries.yaml` (name, version, docs URL)
2. Run `uv run python scripts/rebuild_lib_docs.py --library <name>`
3. Verify with `make eval` — new corpus metrics should be reported

---

## Troubleshooting

### `make healthcheck` fails

- **Postgres:** `docker compose logs postgres` — often a port conflict on 5432
- **Qdrant:** check `docker compose ps` that it's healthy; Qdrant takes ~10s to become ready on first boot
- **Redis:** confirm `REDIS_URL` in `.env` matches the exposed port

### `AsyncQdrantClient` hangs

Sync/async mix-up. Every call must be `await`-ed. Use `AsyncQdrantClient`, never the sync `QdrantClient`, from agent code.

### MCP session closes unexpectedly

MCP sessions must live inside the `async with` context manager. Do not cache sessions across unrelated async tasks.

```python
async with streamablehttp_client(url, headers={...}) as (read, write, close):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        # use tools here, not outside this block
```

### LangGraph state isn't updating

Node functions must **return** a partial state dict — not mutate the input. LangGraph merges the returned dict into state:

```python
# WRONG
def node(state):
    state["requirements"] = req  # mutation won't stick

# RIGHT
def node(state):
    return {"requirements": req}  # merged into state
```

### LangGraph interrupt doesn't fire

Compile with both a checkpointer AND `interrupt_before`:

```python
graph = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_gate"],
)
```

Without a checkpointer, interrupts are silently ignored.

### Resume fails

To resume after an interrupt, pass `None` as the input (not new state):

```python
graph.invoke(None, config={"configurable": {"thread_id": tid}})
```

### `tree-sitter-languages` fails to build on macOS M-series

Known issue. Try the alternative:

```bash
uv remove tree-sitter-languages
uv add tree-sitter-language-pack
```

### Cohere rerank returns 429

Rate-limited. Two fixes:

1. Add tenacity retries with exponential backoff (baseline)
2. Reduce `RETRIEVAL_INITIAL_K` from 20 to 10 during dev

### LangSmith traces are empty

Environment variables must be set **before** Python imports LangChain. Since `.env` is loaded via `pydantic-settings`, make sure the import order is:

```python
from sdlc_agents.config import get_settings  # triggers .env load
get_settings()                                 # forces materialization
# then
from langchain_anthropic import ChatAnthropic  # picks up env
```

Or simply export the vars in your shell before `uv run`.

### Retrieval returns irrelevant chunks

1. Check embedding dimension matches collection (a model swap without re-indexing breaks everything)
2. Verify `rerank: true` in `configs/retrieval.yaml` for that corpus
3. Run `make eval` against the test set — if metrics dropped, bisect on recent chunking/embedding changes
4. Inspect `state.retrieval_traces` for the problematic run to see exact queries and scores

### Qdrant collection dimension mismatch

If you switch embedding models, collections must be recreated:

```bash
uv run python scripts/reset_corpus.py --corpus live_code
# re-seeds with new embeddings
```

---

## Contributing

This is an early-stage project. Contributions welcome — please open an issue before submitting a large PR.

### Before submitting a PR

1. `make format && make lint && make typecheck && make test` all pass
2. New code has unit tests (coverage ≥80% on changed files)
3. Public APIs have docstrings
4. If you changed architecture, update `ARCHITECTURE.md` and add an ADR under `docs/adr/`

### Architecture Decision Records

Material decisions go in `docs/adr/NNNN-title.md` using the [Nygard ADR format](https://github.com/joelparkerhenderson/architecture-decision-record). Example:

```markdown
# 0005. Use Voyage code-3 for live_code embeddings

## Status
Accepted

## Context
Benchmarks on our test set show voyage-code-3 outperforms text-embedding-3-large
by 34% MRR on code-intent queries.

## Decision
All code embeddings use voyage-code-3. Prose corpora continue using voyage-3-large.

## Consequences
- Two embedding providers to manage
- live_code collection dimension is 1024 (fixed)
- Switching requires full re-index
```

---

## License

MIT. See `LICENSE`.

---

## Further Reading

- **[`ARCHITECTURE.md`](ARCHITECTURE.md)** — full system design specification
- **[LangGraph docs](https://langchain-ai.github.io/langgraph/)** — orchestration engine
- **[MCP specification](https://modelcontextprotocol.io/)** — tool protocol
- **[Qdrant docs](https://qdrant.tech/documentation/)** — vector DB
- **[RAGAS docs](https://docs.ragas.io/)** — retrieval evaluation

---

## Acknowledgements

This project stands on the shoulders of:

- **LangChain & LangGraph** teams for the orchestration foundation
- **Anthropic** for MCP and Claude
- **Qdrant** for the hybrid-search-capable vector DB
- **Voyage AI** for the code-specialized embeddings
- **Cohere** for the rerank API

Built to be reviewed by senior engineers. If you wouldn't ship it, don't write it.