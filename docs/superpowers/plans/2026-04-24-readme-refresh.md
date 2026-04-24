# README Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `README.md` so first-time users can understand what the project does, run it locally, and see the current limitations and future improvements in clear plain language.

**Architecture:** The work is limited to `README.md` and uses the existing repository structure, commands, and `sdlc_graph.png` image. The new README will be user-first at the top, then add a compact contributor-oriented overview further down, plus candid issue and future-improvement sections.

**Tech Stack:** Markdown, existing repository docs and source files, GitHub-flavored README rendering

---

## File Map

- Modify: `README.md`
  - Responsibility: explain the project, setup, outputs, workflow, issues, and next steps for first-time readers.
- Create: none
- Test: Markdown content review, image path verification, command accuracy review against repository files.

### Task 1: Rewrite the README for first-time users

**Files:**
- Modify: `README.md`
- Test: rendered-content review by reading the finished file in plain text and verifying referenced files/commands exist

- [ ] **Step 1: Review the current README and source-of-truth files**

Run:

```powershell
Get-Content README.md
Get-Content .env.example
Get-Content src/api/app.py
Get-Content src/api/routes.py
Get-Content src/pipelines/graph.py -TotalCount 260
```

Expected:

```text
The current README, environment variables, API startup shape, route list, and graph flow are visible so the rewrite can stay accurate.
```

- [ ] **Step 2: Replace `README.md` with a new user-first structure**

Write a new `README.md` with these sections in this general order:

```markdown
# Agentic SDLC

Short plain-language summary.

![SDLC Graph](sdlc_graph.png)

## What This Project Does

Explain that the platform turns an idea into requirements, architecture, code, tests, documents, and deployment artifacts with human approval gates.

## Why It Matters

Explain the value in simple language for someone who is not deeply technical.

## Quick Start

### 1. What you need
- Python 3.12+
- `uv`
- OpenAI API key
- Optional Tavily and GitHub tokens

### 2. Install
```bash
git clone <repo>
cd agentic-sdlc
uv sync
```

### 3. Configure
Explain `.env` from `.env.example` in simple language.

### 4. Run the project
```bash
uvicorn src.api.app:app --reload --port 8000 --reload-dir src
streamlit run src/dashboard/streamlit_app.py
```

### 5. Open the dashboard
Explain what the user should do in the browser.

## What Happens During a Run

Short plain-English stage summary.

## What the Project Creates

List generated outputs in `workspace/`, docs, checkpoints, logs, and PR artifacts.

## Main Project Areas

Short, readable folder overview for contributors.

## Top 3 Current Issues for Users

Three honest product limitations.

## Top 3 Current Issues for Contributors

Three honest engineering or maintenance issues.

## Future Improvements

Concrete next steps tied to reliability, usability, and maintainability.

## License

MIT
```

When writing the final text:

- Keep sentences short and direct.
- Avoid unexplained jargon near the top of the file.
- Use the exact image reference `![SDLC Graph](sdlc_graph.png)`.
- Keep contributor context short and lower in the README.

- [ ] **Step 3: Verify commands, file references, and limitations against the repo**

Run:

```powershell
Test-Path sdlc_graph.png
Test-Path src/dashboard/streamlit_app.py
Test-Path src/api/app.py
Test-Path src/api/routes.py
Test-Path workspace
```

Expected:

```text
All referenced files and folders return True.
```

- [ ] **Step 4: Review the finished README for clarity and scope**

Run:

```powershell
Get-Content README.md
```

Expected:

```text
The README reads clearly from top to bottom, starts with user-focused guidance, embeds the SDLC graph image, includes both issue lists, and ends with future improvements and license information.
```

- [ ] **Step 5: Commit the README refresh**

Run:

```powershell
git add README.md
git commit -m "Refresh README for first-time users"
```

Expected:

```text
A commit is created containing only the README rewrite.
```
