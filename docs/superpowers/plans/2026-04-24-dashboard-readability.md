# Dashboard Readability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase dashboard readability by slightly enlarging recurring UI text and brightening muted text colors while preserving the existing dark theme and layout.

**Architecture:** The implementation stays inside the existing `GLOBAL_CSS` string in `src/dashboard/streamlit_app.py`. We will update repeated font-size and color declarations in place, leaving rendering logic, layout structure, and accent-state semantics unchanged.

**Tech Stack:** Python, Streamlit, embedded CSS in `src/dashboard/streamlit_app.py`

---

## File Map

- Modify: `src/dashboard/streamlit_app.py`
  - Responsibility: holds the dashboard `GLOBAL_CSS` block that defines typography, muted text colors, badges, cards, alerts, and sidebar styles.
- Create: none
- Test: manual dashboard smoke check after CSS edits; optional syntax validation with Python compile check on the edited file.

### Task 1: Tune global readability styles

**Files:**
- Modify: `src/dashboard/streamlit_app.py`
- Test: manual verification in the running Streamlit dashboard

- [ ] **Step 1: Find the current readability-sensitive selectors inside `GLOBAL_CSS`**

Run:

```powershell
rg -n "font-size: 0\\.|color: #(?:334155|475569|64748b|667892|7186a0|7f93ae|8da0bb|94a3b8|bcc9db|cbd5e1)" src/dashboard/streamlit_app.py
```

Expected:

```text
Multiple matches inside the GLOBAL_CSS block for sidebar labels, form controls, pills, badges, pipeline labels, helper text, subtitles, and metadata rows.
```

- [ ] **Step 2: Update the smallest recurring font sizes and muted text colors in `GLOBAL_CSS`**

Edit the existing CSS declarations in `src/dashboard/streamlit_app.py` so that compact text becomes slightly larger and low-contrast text becomes easier to read without changing the dark surfaces or accent colors.

Use the following patch shape as the target content for the affected selectors:

```css
.af-label {
    font-size: 0.68rem;
    color: #9bb0c9;
}

[data-testid="stSidebar"] textarea {
    color: #e6eef8 !important;
    font-size: 0.84rem !important;
}

[data-testid="stSidebar"] textarea::placeholder {
    color: #8ea3bd !important;
}

[data-testid="stSidebar"] .stButton > button {
    font-size: 0.84rem !important;
}

.stTextArea textarea {
    font-size: 0.88rem !important;
}

.stTextInput > div > div > input {
    font-size: 0.84rem !important;
}

.stSelectbox > div > div {
    color: #b8c7da !important;
    font-size: 0.84rem !important;
}

.main .stButton > button {
    color: #b8c7da !important;
    font-size: 0.84rem !important;
}

.streamlit-expanderHeader {
    color: #8fa4bf !important;
    font-size: 0.82rem !important;
}

.stTextArea label, .stTextInput label, .stSelectbox label {
    color: #8fa4bf !important;
    font-size: 0.76rem !important;
}

.af-pill {
    font-size: 0.69rem;
    color: #8fa4bf;
}

.af-pill b {
    color: #c9d6e5;
}

.af-pipe-name {
    font-size: 0.8rem;
    color: #d0dceb;
}

.af-pipe-desc {
    font-size: 0.69rem;
    color: #97abc5;
}

.af-metric-lbl {
    font-size: 0.64rem;
    color: #6f85a0;
}

.af-metric-sub {
    font-size: 0.66rem;
    color: #7890ad;
}

.af-card-title {
    font-size: 0.8rem;
    color: #d8e2ee;
}

.af-hitl-phase {
    font-size: 0.66rem;
    color: #91a6c1;
}

.af-hitl-msg {
    font-size: 0.82rem;
    color: #bdd0e3;
}

.af-mono {
    font-size: 0.76rem;
    color: #93a9c2;
}

.af-term-title {
    font-size: 0.66rem;
    color: #8097b1;
}

.af-term-body {
    font-size: 0.74rem;
}

.af-art-row {
    font-size: 0.78rem;
}

.af-meta-k {
    font-size: 0.64rem;
    color: #7f95b0;
}

.af-meta-v {
    font-size: 0.72rem;
    color: #b7c7d9;
}

.af-issue {
    font-size: 0.78rem;
}

.af-issue-loc {
    font-size: 0.68rem;
}

.af-page-sub {
    font-size: 0.82rem;
    color: #91a6c1;
}

.af-hero-sub {
    font-size: 0.88rem;
    color: #90a6c1;
}

.af-hero-hint {
    font-size: 0.7rem;
    color: #8097b1;
}

.af-alert {
    font-size: 0.82rem;
}
```

Apply the same principle to nearby selectors in the same block that use equivalent muted text values, but do not change dark backgrounds, borders, or strong accent colors such as the gold primary action and semantic success/error states.

- [ ] **Step 3: Run a syntax check on the edited Python file**

Run:

```powershell
.\\.venv\\Scripts\\python.exe -m py_compile src/dashboard/streamlit_app.py
```

Expected:

```text
No output, which means the file compiled successfully.
```

- [ ] **Step 4: Start the dashboard locally and verify readability in the main UI regions**

Run:

```powershell
streamlit run src/dashboard/streamlit_app.py --server.headless true
```

Expected:

```text
A local Streamlit URL is printed and the app starts without a Python traceback.
```

Verify manually in the browser:

```text
1. Sidebar labels, textarea, and pipeline descriptions look slightly larger and easier to read.
2. Main-area subtitles, card headers, expanders, issue rows, and metadata text are brighter than before.
3. Gold, green, blue, and red status accents still stand out more than regular text.
4. No compact element looks crowded or wraps unexpectedly because of the font-size increases.
```

- [ ] **Step 5: Commit the readability pass**

Run:

```powershell
git add src/dashboard/streamlit_app.py
git commit -m "Adjust dashboard typography for readability"
```

Expected:

```text
A commit is created containing only the intended CSS readability changes.
```
