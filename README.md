# Agentic SDLC

Turn a one-sentence idea into a working codebase with tests, docs, Docker, CI, and a GitHub PR — with a human in the loop at the moments that matter.

Built on **LangGraph**, **FastAPI**, **Streamlit**, **OpenAI**, and **Chroma** for retrieval-augmented generation.

---

## Pipeline

```
idea
  └─> requirements ─┐
                    ├─[HITL]─ approve ─┐
                    │                  │
                    └─[HITL]─ reject ──┘ (loop)
                                        │
                                        ▼
                               architecture ─┐
                                             ├─[HITL]─ approve ─┐
                                             └─[HITL]─ reject ──┘ (loop)
                                                                │
                                                                ▼
                                   developer ── code review ── (retry on fail)
                                                                │
                                                                ▼
                                                               qa ── (retry on fail)
                                                                │
                                                                ▼
                                                       [HITL deploy]
                                                                │
                                                     approve ──┼── reject → back to qa
                                                                ▼
                                                              devops
                                                                │
                                                                ▼
                                                          Dockerfile, CI, GitHub PR
```

At every stage the agent emits a structured artifact (Pydantic model) and writes a phase report as both Markdown and PDF under `workspace/<project>/docs/`.

---

## Components

| Layer | What it does |
|-------|--------------|
| **API** (`src/api`) | FastAPI app, lifespan-managed graph singleton, REST routes for start / resume / state / rewind |
| **Dashboard** (`src/dashboard`) | Streamlit UI: start runs, show the current HITL prompt, approve / reject with feedback |
| **Graph** (`src/pipelines/graph.py`) | LangGraph node + edge definitions, conditional routing, interrupt-based HITL |
| **Agents** (`src/agents`) | Requirements, Architect, Developer, CodeReviewer, QA, DevOps, Doc (one instance per phase) |
| **A2A bus** (`src/a2a`) | SQLite-backed agent-to-agent message bus with typed agent cards |
| **Knowledge / RAG** (`src/knowledge`) | Tavily web search, Chroma vector store, topic-scoped retrieval before codegen |
| **Memory** (`src/memory`) | Per-project episodic long-term memory |
| **Tools** (`src/tools`) | `LLMFactory`, `TestRunner` (pytest in the generated project), `GitHubMCPClient` |

---

## Quickstart

### Prerequisites

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv)
- OpenAI API key
- (Optional) Tavily API key — for web-retrieval-backed code generation
- (Optional) GitHub Personal Access Token — for DevOps push + PR

### Install

```bash
git clone <repo>
cd agentic-sdlc
uv sync
```

### Configure

Copy `.env.example` to `.env` and fill in your values. Required: `OPENAI_API_KEY`. Everything else is optional but unlocks capabilities.

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Chat completions for every agent |
| `LLM_MODEL` | Override the default model (`gpt-4o-mini`) |
| `LLM_TEMPERATURE` | Base temperature for the factory |
| `TAVILY_API_KEY` | Enables web-retrieval RAG before codegen |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | DevOps agent pushes code + opens PRs |
| `GITHUB_REPO_OWNER` / `GITHUB_REPO_NAME` | Target repo for the PR |
| `MAX_QA_RETRIES` | How many times QA can loop back to Developer |
| `MAX_REVIEW_RETRIES` | How many times the code reviewer can loop |
| `LOG_LEVEL` | `INFO` (default) or `DEBUG` |

### Run

In two terminals:

```bash
# 1. API
uvicorn src.api.app:app --reload --port 8000 --reload-dir src

# 2. Dashboard
streamlit run src/dashboard/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501), type an idea in the sidebar, click **Start**, and approve or reject at each HITL gate. The API URL can be overridden with `API_BASE_URL`.

---

## Output

Each run produces:

- `workspace/<project>/` — source files, tests, `Dockerfile`, `.github/workflows/ci.yml`
- `workspace/<project>/docs/{requirements,architecture,developer,qa,devops}.{md,pdf}` — phase reports
- `.checkpoints/sdlc.sqlite` — LangGraph run state (resumable by `thread_id`)
- `logs/sdlc_run_<timestamp>.log` — structured, per-agent logs
- A GitHub pull request on `GITHUB_REPO_OWNER/GITHUB_REPO_NAME` (if configured)

---

## API cheatsheet

```bash
# start a run
curl -X POST http://localhost:8000/runs \
  -H 'content-type: application/json' \
  -d '{"idea":"A FastAPI TODO API with CRUD and in-memory storage"}'

# resume a paused HITL interrupt
curl -X POST http://localhost:8000/runs/<thread_id>/resume \
  -H 'content-type: application/json' \
  -d '{"verdict":"approve","comment":""}'

# peek at current state
curl http://localhost:8000/runs/<thread_id>/state
```

Full route list is in `src/api/routes.py`.

---

## Tests

```bash
pytest src/tests/
```

Project-level tests live in `src/tests/`; they cover graph routing, agents, and schemas. They're separate from the tests the pipeline *generates* (those live in `workspace/<project>/tests/`).

---

## Documentation

- [`architecture.md`](architecture.md) — system design, graph shape, state shape, data flow
- [`agents.md`](agents.md) — reference for every agent: responsibilities, inputs, outputs, prompt, failure modes
- [`skills.md`](skills.md) — conventions and patterns you're expected to follow when extending this repo
- [`CLAUDE.md`](CLAUDE.md) — working notes for Claude Code / similar coding agents

---

## License

MIT.
