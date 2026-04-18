# Architecture — Agentic SDLC Automation System

This document is the authoritative architectural reference. If implementation
contradicts this doc, either update the implementation or update this doc
(via an ADR) — not silently diverge.

---

## 1. System Purpose

A multi-agent AI system that takes a product idea and produces a deployed,
tested application through a phased SDLC workflow with mandatory human
approval gates. Agents specialize by role (Requirement, Architect, Developer,
QA, DevOps, Critic), communicate via A2A messages, act via MCP tools, and
reason with context retrieved from five domain-specific RAG corpora.

---

## 2. The Four Planes

### Control Plane — LangGraph
A `StateGraph` parameterized by `SDLCState`. Nodes are agents + special
`human_gate` nodes. Edges are conditional routers. Compile with
`interrupt_before=["human_gate"]` and a `PostgresSaver` checkpointer. Every
state transition is checkpointed.

### Agent Plane — Six Specialist Agents
Each agent: `plan_retrieval → fetch_retrieval → fetch_memory → build_prompt
→ call_llm → parse_output → emit_A2A_message → write_checkpoint`.
Agents never call each other directly; they read/write A2A messages in state.

### Tool Plane — Hosted MCP Servers
All real-world side effects route through MCP tools. `MCPClientManager` owns
client sessions; `ToolRegistry` maps agents → allowed tool subsets
(least privilege). Tools surface to agents as LangChain `BaseTool` instances
via `langchain-mcp-adapters`.

### Retrieval Plane — Five Corpora + RetrievalService
Five Qdrant collections, each with its own chunking, embeddings, refresh
cadence. Agents call `RetrievalService` methods (typed) — they don't know
about Qdrant. Every retrieval is logged to `RetrievalTrace` in state.

---

## 3. The Agents

| Agent | Writes To State | Retrieves From | MCP Tools |
|-------|-----------------|----------------|-----------|
| Requirement | `requirements` | `past_projects` (domain filter), `feedback` | none (read-only memory) |
| Architect | `design`, `active_libraries` | `past_projects`, `patterns`, `feedback` | none |
| Developer | `codebase` (ref) | `live_code`, `lib_docs`, `patterns` | `github.*`, `filesystem.*` |
| QA | `tests`, `test_results` | `live_code`, `lib_docs`, `patterns` | `filesystem.*`, `code_exec.*`, `github_actions.*` |
| DevOps | `deployment` | `lib_docs` (deploy tools), `patterns` | `github.*`, `deploy.*` |
| Critic | `critic_scores` | `patterns`, `feedback`, `past_projects` | none |

**Developer Agent is special:** it's a LangGraph sub-graph, not a single node.
Inside, it has a ReAct-style loop with retrieval exposed as LLM tools
(agentic retrieval).

---

## 4. The Five Corpora

| Corpus | Chunking | Embeddings | Refresh | Primary Consumer |
|--------|----------|------------|---------|------------------|
| `live_code` | AST via tree-sitter + contextual blurbs | `voyage-code-3` + BM25 | Incremental (on file write) | Developer |
| `past_projects` | Document-section semantic | `voyage-3-large` + `voyage-code-3` | On workflow completion | Architect |
| `lib_docs` | Hierarchical, 500–1000 tok, 15% overlap | `voyage-3-large` + BM25 | Weekly scheduled | Developer, QA |
| `patterns` | Manual per-pattern | `voyage-3-large` | Curator-driven | Critic, Architect |
| `feedback` | One chunk per rejection event | `voyage-3-large` | Real-time on HITL reject | All agents |

All corpora: **hybrid search** (dense + sparse) → **Cohere Rerank v3** →
top-K (default K=5).

---

## 5. A2A Protocol

```python
class A2AMessage(BaseModel):
    trace_id: UUID
    from_agent: AgentName
    to_agent: AgentName
    task: str
    context_summary: str       # ≤300 tokens, LLM-summarized
    artifacts: dict            # references only, not raw blobs
    instructions: str
    memory_refs: list[str]     # UUIDs into retrieval traces or vector store
    timestamp: datetime
```

**Rules:**
- Never pass raw full history — summarize first.
- Artifacts are references (URLs, commit SHAs, document IDs), not blobs.
- `memory_refs` point to RetrievalTrace entries or vector store IDs.

---

## 6. MCP Integration

**Transport:** Streamable HTTP for hosted servers (fallback SSE).
**Discovery:** on startup, `MCPClientManager` calls `session.list_tools()` per
configured server.
**Adaptation:** `langchain_mcp_adapters.tools.load_mcp_tools(session)`
converts MCP tool definitions to LangChain `BaseTool`.
**Binding:** agents get tools via `llm.bind_tools(registry.tools_for(agent))`.
**Auth:** bearer tokens from `configs/mcp_servers.yaml` (secrets via env).
**Idempotency:** every mutating MCP call includes an idempotency key:
`f"{trace_id}:{phase}:{artifact_id}"`.

---

## 7. HITL — Human-in-the-Loop

Gate points: **after Requirements, after Design, before QA→DevOps transition
(post code+tests), before deployment.** Implemented as `human_gate` nodes
with `interrupt_before`.

At each gate, present to the human:
1. The raw output (design doc, PR link, etc.)
2. An auto-generated summary
3. The agent's reasoning trace (LangSmith link)
4. A form: approve / reject + feedback text

On reject:
- Append `FeedbackEntry` to `state.feedback`
- Write feedback to `feedback` corpus (real-time index)
- Loop back to the same agent with feedback in prompt
- Bounded by `max_hitl_rejections` per phase

Resume: `graph.invoke(None, config={"configurable": {"thread_id": ...}})`

---

## 8. State Schema

```python
class SDLCState(TypedDict):
    thread_id: str
    idea: str
    domain_tags: list[str]
    active_libraries: list[LibraryRef]       # set by Architect
    requirements: Requirements | None
    design: Design | None
    codebase: CodebaseRef | None
    tests: TestSuite | None
    test_results: TestResults | None
    deployment: DeploymentStatus | None
    messages: list[A2AMessage]
    feedback: list[FeedbackEntry]
    memory_refs: list[str]
    retrieval_traces: list[RetrievalTrace]
    critic_scores: dict[str, float]
    hitl_decisions: list[HITLDecision]
    retry_counts: dict[str, int]
    live_code_index_version: int
    current_phase: Phase
    status: WorkflowStatus
```

**Rules:**
- Artifacts stored by reference, never by value.
- List fields are append-only (full history for audit).
- State size capped — summarize before append if approaching limit.

---

## 9. Iteration & Retry Policies

| Trigger | Action | Max Retries |
|---------|--------|-------------|
| QA tests fail | Route to Developer with test output in A2A | 3 |
| HITL rejects | Re-run same agent with feedback in context | 5 |
| Critic score < 7/10 | Re-run phase with critique | 2 |

After max retries, graph routes to `escalation_gate` for manual human resolution.

---

## 10. Memory Tiers

1. **Short-term session:** `SDLCState` + A2A messages via LangGraph checkpointer (Postgres in prod, SQLite in dev)
2. **Long-term semantic:** 5 Qdrant collections (see corpora table)
3. **Artifact store:** file content, PR diffs, etc. — S3-compatible bucket or Postgres `bytea`; referenced by state

---

## 11. Observability Contract

- **Tracing:** LangSmith (`LANGSMITH_TRACING=true`); every LLM call, tool call, retrieval call is a span
- **Logging:** structlog JSON; every log line carries `trace_id`, `thread_id`, `agent`, `phase`
- **Metrics:** agent duration, retry counts, critic scores, retrieval latency, retrieval hit rate, HITL approval rates — Prometheus export
- **RetrievalTrace:** every retrieval written to state with query, corpus, chunks_returned (IDs only), scores, latency_ms

---

## 12. Security

- Secrets via env + `pydantic-settings`; never in code or logs
- Tool least-privilege: `ToolRegistry` enforces per-agent tool allow-lists
- Prompt-injection defense: summarizer sanitizes agent outputs before they become other agents' context
- Code execution (QA) runs in ephemeral containers via MCP code-execution server — never on the host
- HITL gates all destructive actions: deploy, merge-to-main, infra changes

---

## 13. Directory Structure

See `README.md` for the canonical tree. The src-layout is mandatory.

---

## 14. Decision Records

Material architectural decisions go in `docs/adr/NNNN-title.md` using the
classic Nygard ADR format. Update this file's tables when decisions change
downstream shape.