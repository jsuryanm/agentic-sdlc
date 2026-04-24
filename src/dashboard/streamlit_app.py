"""
AgentFlow — Enterprise SDLC Automation Platform
Professional Streamlit frontend for the multi-agent SDLC pipeline.
"""

import os
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx
import streamlit as st

from src.dashboard.sidebar_components import build_pipeline_html

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
POLL_INTERVAL_SEC = 2.0

st.set_page_config(
    page_title="AgentFlow",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&display=swap');

/* ---- Base ---- */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
}

/* ---- App background ---- */
.stApp {
    background-color: #080c14 !important;
}

/* ---- Hide default chrome ---- */
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"] { display: none; }
[data-testid="stToolbar"] { display: none; }

/* ---- Scrollbar ---- */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0b1120; }
::-webkit-scrollbar-thumb { background: #1e2d45; border-radius: 2px; }

/* ================================================================
   SIDEBAR
   ================================================================ */
[data-testid="stSidebar"] {
    background-color: #0b1120 !important;
    border-right: 1px solid #1a2540 !important;
    width: 300px !important;
    min-width: 300px !important;
    max-width: 300px !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding: 1.5rem 1.25rem 1.75rem !important;
    background-color: #0b1120 !important;
    box-sizing: border-box !important;
}

/* Sidebar collapse arrow button */
[data-testid="stSidebarCollapseButton"] {
    background: #0b1120 !important;
    border: 1px solid #1a2540 !important;
    color: #8da0bb !important;
}

/* ---- Sidebar title / spacing ---- */
.af-sidebar-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.95rem;
    font-weight: 800;
    color: #dbe7f5;
    letter-spacing: -0.01em;
    margin-bottom: 1.25rem;
}

.af-sidebar-spacer {
    height: 1.4rem;
}

/* ---- Sidebar section label ---- */
.af-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    font-weight: 500;
    color: #9bb0c9;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding-bottom: 0.6rem;
    margin-bottom: 0.75rem;
    border-bottom: 1px solid #131e30;
    display: block;
}

/* ---- Streamlit text area (sidebar) ---- */
[data-testid="stSidebar"] .stTextArea label {
    display: none !important;
}

[data-testid="stSidebar"] textarea {
    background: #080c14 !important;
    border: 1px solid #1e2d45 !important;
    border-radius: 3px !important;
    color: #e6eef8 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.84rem !important;
    line-height: 1.65 !important;
    caret-color: #c9933a !important;
    resize: vertical !important;
    padding: 0.65rem 0.85rem !important;
}

[data-testid="stSidebar"] textarea:focus {
    border-color: #c9933a !important;
    box-shadow: 0 0 0 2px rgba(201,147,58,0.12) !important;
    color: #e2e8f0 !important;
}

[data-testid="stSidebar"] textarea::placeholder {
    color: #8ea3bd !important;
}

/* ---- Sidebar primary button ---- */
[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    background: linear-gradient(135deg, #c9933a 0%, #b8822f 100%) !important;
    border: none !important;
    border-radius: 3px !important;
    color: #0b1120 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.84rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1rem !important;
    height: auto !important;
    line-height: 1.4 !important;
    white-space: nowrap !important;
    transition: all 0.15s ease !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: linear-gradient(135deg, #d4a04a 0%, #c9933a 100%) !important;
    box-shadow: 0 0 20px rgba(201,147,58,0.25) !important;
}

[data-testid="stSidebar"] .stButton > button:disabled {
    background: #1a2540 !important;
    color: #6f85a0 !important;
    cursor: not-allowed !important;
    box-shadow: none !important;
}

/* ================================================================
   MAIN AREA
   ================================================================ */
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ---- Main widgets ---- */
.stTextArea textarea {
    background: #080c14 !important;
    border: 1px solid #1e2d45 !important;
    border-radius: 3px !important;
    color: #e2e8f0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
}

.stTextArea textarea:focus {
    border-color: #c9933a !important;
    box-shadow: 0 0 0 2px rgba(201,147,58,0.12) !important;
}

.stTextInput > div > div > input {
    background: #080c14 !important;
    border: 1px solid #1e2d45 !important;
    border-radius: 3px !important;
    color: #e2e8f0 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.84rem !important;
}

.stTextInput > div > div > input:focus {
    border-color: #c9933a !important;
    box-shadow: 0 0 0 2px rgba(201,147,58,0.12) !important;
}

/* ---- Selectbox ---- */
.stSelectbox > div > div {
    background: #080c14 !important;
    border-color: #1e2d45 !important;
    color: #b8c7da !important;
    border-radius: 3px !important;
    font-size: 0.84rem !important;
}

/* ---- Main buttons ---- */
.main .stButton > button {
    background: #111827 !important;
    border: 1px solid #1e2d45 !important;
    border-radius: 3px !important;
    color: #b8c7da !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.84rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em !important;
    transition: all 0.15s !important;
}

.main .stButton > button:hover {
    background: #1a2540 !important;
    border-color: #2a3347 !important;
    color: #e2e8f0 !important;
}

.main .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #c9933a, #b8822f) !important;
    border: none !important;
    color: #0b1120 !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
}

.main .stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #d4a04a, #c9933a) !important;
    box-shadow: 0 0 20px rgba(201,147,58,0.25) !important;
}

/* ---- Expander ---- */
.streamlit-expanderHeader {
    background-color: #0d1526 !important;
    border: 1px solid #1a2540 !important;
    border-radius: 3px !important;
    color: #8fa4bf !important;
    font-size: 0.82rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
}

.streamlit-expanderContent {
    background-color: #080c14 !important;
    border: 1px solid #1a2540 !important;
    border-top: none !important;
}

/* ---- JSON viewer ---- */
.stJson {
    background: #080c14 !important;
    border: 1px solid #1a2540 !important;
    border-radius: 3px !important;
}

/* ---- Code blocks ---- */
.stCode, [data-testid="stCodeBlock"] {
    background: #05080f !important;
}

[data-testid="stCodeBlock"] pre {
    background: #05080f !important;
    border: 1px solid #1a2540 !important;
    border-radius: 3px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.76rem !important;
}

/* ---- Link button ---- */
.stLinkButton a {
    background: #111827 !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 3px !important;
    color: #60a5fa !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.76rem !important;
    text-decoration: none !important;
    padding: 0.45rem 0.9rem !important;
    transition: all 0.15s !important;
}

.stLinkButton a:hover {
    background: #1a2540 !important;
    border-color: #3b82f6 !important;
    color: #93c5fd !important;
}

/* ---- Label color overrides ---- */
.stTextArea label, .stTextInput label, .stSelectbox label {
    color: #8fa4bf !important;
    font-size: 0.76rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ---- Alert / info boxes ---- */
[data-testid="stAlert"] {
    border-radius: 3px !important;
    font-size: 0.82rem !important;
}

/* ================================================================
   CUSTOM COMPONENT STYLES
   ================================================================ */

/* ---- Navbar ---- */
.af-navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2rem;
    height: 56px;
    background: #0b1120;
    border-bottom: 1px solid #1a2540;
    margin-bottom: 0;
}

.af-logo {
    display: flex;
    align-items: center;
    gap: 0.7rem;
}

.af-logo-hex {
    width: 28px;
    height: 28px;
    background: linear-gradient(135deg, #c9933a 0%, #e8b86d 100%);
    clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
    flex-shrink: 0;
}

.af-logo-text {
    font-family: 'Syne', sans-serif;
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #f1f5f9;
}

.af-logo-text em { color: #c9933a; font-style: normal; }

.af-nav-pills { display: flex; align-items: center; gap: 0.75rem; }

.af-pill {
    font-family: 'DM Mono', monospace;
    font-size: 0.69rem;
    color: #8fa4bf;
    background: #111827;
    border: 1px solid #1e2d45;
    padding: 0.25rem 0.65rem;
    border-radius: 2px;
    letter-spacing: 0.03em;
    white-space: nowrap;
}

.af-pill b { color: #c9d6e5; font-weight: 400; margin-left: 0.3rem; }

/* ---- Badge ---- */
.af-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.2rem 0.55rem;
    border-radius: 2px;
    font-family: 'DM Mono', monospace;
    font-size: 0.62rem;
    font-weight: 500;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    white-space: nowrap;
}

.af-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }

.af-badge-idle    { background:#111827; color:#7f95b0; border:1px solid #1e2d45; }
.af-badge-idle    .af-dot { background:#53657e; }
.af-badge-run     { background:#0c1f14; color:#4ade80; border:1px solid #166534; }
.af-badge-run     .af-dot { background:#22c55e; animation:blink 1.4s infinite; }
.af-badge-wait    { background:#1a1100; color:#fbbf24; border:1px solid #92400e; }
.af-badge-wait    .af-dot { background:#f59e0b; animation:blink 1s infinite; }
.af-badge-done    { background:#0f172a; color:#60a5fa; border:1px solid #1e3a5f; }
.af-badge-done    .af-dot { background:#3b82f6; }
.af-badge-error   { background:#1a0a0a; color:#f87171; border:1px solid #7f1d1d; }
.af-badge-error   .af-dot { background:#ef4444; }

@keyframes blink {
    0%,100% { opacity:1; }
    50%      { opacity:0.25; }
}

/* ---- Pipeline sidebar component ---- */
.af-pipe { display:flex; flex-direction:column; }

.af-pipe-row {
    display: flex;
    align-items: flex-start;
    gap: 0.7rem;
    min-height: 44px;
}

.af-pipe-track {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 16px;
    flex-shrink: 0;
}

.af-pipe-node {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid #1e2d45;
    background: #0b1120;
    margin-top: 4px;
    flex-shrink: 0;
    transition: all 0.3s;
}

.af-pipe-node.complete { background:#22c55e; border-color:#22c55e; box-shadow:0 0 8px rgba(34,197,94,.4); }
.af-pipe-node.active   { background:#c9933a; border-color:#c9933a; box-shadow:0 0 10px rgba(201,147,58,.5); animation:blink 1.4s infinite; }
.af-pipe-node.error    { background:#ef4444; border-color:#ef4444; }

.af-pipe-line {
    width: 2px;
    flex: 1;
    background: #131e30;
    min-height: 12px;
    margin-top: 2px;
}
.af-pipe-line.complete { background: rgba(34,197,94,.35); }

.af-pipe-info { flex:1; padding: 2px 0 10px 0; }

.af-pipe-name {
    font-size: 0.8rem;
    font-weight: 600;
    color: #d0dceb;
    line-height: 1.3;
}
.af-pipe-name.complete { color:#4ade80; }
.af-pipe-name.active   { color:#e2e8f0; }
.af-pipe-name.error    { color:#f87171; }

.af-pipe-desc {
    font-family: 'DM Mono', monospace;
    font-size: 0.69rem;
    color: #97abc5;
    margin-top: 0.15rem;
    line-height: 1.4;
}

/* ---- Metric cards ---- */
.af-metrics {
    display: grid;
    grid-template-columns: repeat(4,1fr);
    gap: 1px;
    background: #1a2540;
    border: 1px solid #1a2540;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 1.75rem;
}

.af-metric {
    background: #0b1120;
    padding: 1rem 1.15rem;
}

.af-metric-lbl {
    font-family: 'DM Mono', monospace;
    font-size: 0.64rem;
    color: #6f85a0;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.35rem;
}

.af-metric-val {
    font-family: 'Syne', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1;
}

.af-metric-val.gold   { color: #c9933a; }
.af-metric-val.green  { color: #22c55e; }
.af-metric-val.red    { color: #ef4444; }
.af-metric-val.blue   { color: #60a5fa; }

.af-metric-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.66rem;
    color: #7890ad;
    margin-top: 0.2rem;
}

/* ---- Generic card ---- */
.af-card {
    background: #0b1120;
    border: 1px solid #1a2540;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 1.25rem;
}

.af-card-hd {
    padding: 0.75rem 1.15rem;
    border-bottom: 1px solid #1a2540;
    background: #0d1526;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.af-card-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: #d8e2ee;
    letter-spacing: 0.01em;
}

.af-card-bd { padding: 1.15rem; }

/* ---- HITL panel ---- */
.af-hitl {
    background: #0b1120;
    border: 1px solid #92400e;
    border-left: 3px solid #c9933a;
    border-radius: 4px;
    padding: 1.35rem 1.35rem 1rem 1.35rem;
    margin-bottom: 1.75rem;
}

.af-hitl-hd {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin-bottom: 0.85rem;
}

.af-hitl-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #c9933a;
    animation: blink 1.2s infinite;
    flex-shrink: 0;
}

.af-hitl-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.95rem;
    font-weight: 700;
    color: #fbbf24;
}

.af-hitl-phase {
    font-family: 'DM Mono', monospace;
    font-size: 0.66rem;
    color: #91a6c1;
    margin-left: auto;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.af-hitl-msg {
    font-size: 0.82rem;
    color: #bdd0e3;
    line-height: 1.65;
    margin-bottom: 0.5rem;
}

/* ---- Mono block ---- */
.af-mono {
    font-family: 'DM Mono', monospace;
    font-size: 0.76rem;
    color: #93a9c2;
    background: #05080f;
    border: 1px solid #1a2540;
    padding: 0.75rem 0.9rem;
    border-radius: 3px;
    line-height: 1.75;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-x: auto;
}

/* ---- Terminal ---- */
.af-term {
    background: #05080f;
    border: 1px solid #1a2540;
    border-radius: 4px;
    overflow: hidden;
    margin-top: 0.5rem;
}

.af-term-bar {
    background: #0d1526;
    padding: 0.4rem 0.9rem;
    border-bottom: 1px solid #1a2540;
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

.af-term-dot { width:7px; height:7px; border-radius:50%; }

.af-term-title {
    font-family: 'DM Mono', monospace;
    font-size: 0.66rem;
    color: #8097b1;
    margin-left: 0.45rem;
    letter-spacing: 0.05em;
}

.af-term-body {
    font-family: 'DM Mono', monospace;
    font-size: 0.74rem;
    color: #4ade80;
    padding: 0.9rem 1rem;
    line-height: 1.75;
    max-height: 260px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
}

/* ---- Error item ---- */
.af-err {
    display: flex;
    gap: 0.65rem;
    padding: 0.6rem 0.85rem;
    background: #1a0a0a;
    border-left: 2px solid #ef4444;
    border-radius: 2px;
    margin-bottom: 0.4rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.67rem;
    color: #fca5a5;
    line-height: 1.55;
}

/* ---- Artifact row ---- */
.af-art-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0;
    border-bottom: 1px solid #0f1623;
    font-size: 0.78rem;
}

.af-art-row:last-child { border-bottom: none; }
.af-art-name { font-family: 'DM Mono', monospace; color: #bcc9db; }
.af-art-yes  { font-family:'DM Mono',monospace; font-size:0.66rem; padding:0.12rem 0.4rem; border-radius:2px; background:#0c1f14; color:#86efac; }
.af-art-no   { font-family:'DM Mono',monospace; font-size:0.66rem; padding:0.12rem 0.4rem; border-radius:2px; background:#111827; color:#9ab0c9; }

/* ---- Meta block ---- */
.af-meta {
    background: #05080f;
    border: 1px solid #131e30;
    border-radius: 3px;
    padding: 0.75rem 0.9rem;
}

.af-sidebar-meta {
    margin: 0;
}

.af-meta-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.2rem 0;
}

.af-meta-k {
    font-family:'DM Mono',monospace;
    font-size:0.64rem;
    color:#7f95b0;
    text-transform:uppercase;
    letter-spacing:0.1em;
}

.af-meta-v {
    font-family:'DM Mono',monospace;
    font-size:0.72rem;
    color:#b7c7d9;
}

.af-sidebar-meta .af-meta-k {
    color: #9ab0c9;
}

.af-sidebar-meta .af-meta-v {
    color: #d7e1ee;
}

/* ---- Issue row ---- */
.af-issue {
    padding: 0.6rem 0.85rem;
    border-left: 2px solid;
    border-radius: 2px;
    margin-bottom: 0.4rem;
    background: #080c14;
    font-size: 0.78rem;
}

.af-issue-loc {
    font-family:'DM Mono',monospace;
    font-size:0.68rem;
    margin-bottom:0.2rem;
}

/* ---- Page title ---- */
.af-page-hd {
    margin-bottom: 1.75rem;
}

.af-page-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    color: #f1f5f9;
    line-height: 1.2;
    margin-bottom: 0.3rem;
}

.af-page-sub {
    font-size: 0.82rem;
    color: #91a6c1;
    line-height: 1.5;
}

/* ---- Main content padding ---- */
.af-content { padding: 1.75rem 2.25rem; }

/* ---- Idle hero ---- */
.af-hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 65vh;
    text-align: center;
    gap: 1.5rem;
}

.af-hero-hex {
    width: 60px; height: 60px;
    background: linear-gradient(135deg,#c9933a,#b8822f);
    clip-path: polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%);
    opacity: 0.45;
}

.af-hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.9rem;
    font-weight: 800;
    color: #f1f5f9;
    margin-bottom: 0.4rem;
}

.af-hero-sub {
    font-size: 0.88rem;
    color: #90a6c1;
    max-width: 420px;
    line-height: 1.75;
    margin: 0 auto;
}

.af-hero-stats {
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap: 1px;
    background: #1a2540;
    border: 1px solid #1a2540;
    border-radius: 4px;
    overflow: hidden;
    width: 100%;
    max-width: 480px;
}

.af-hero-stat {
    background: #0b1120;
    padding: 0.9rem;
    text-align: center;
}

.af-hero-stat-n {
    font-family:'Syne',sans-serif;
    font-size:1.3rem;
    font-weight:700;
    color:#c9933a;
}

.af-hero-stat-l {
    font-family:'DM Mono',monospace;
    font-size:0.63rem;
    color:#7890ad;
    text-transform:uppercase;
    letter-spacing:0.1em;
    margin-top:0.2rem;
}

.af-hero-hint {
    font-family:'DM Mono',monospace;
    font-size:0.7rem;
    color:#8097b1;
    border:1px solid #131e30;
    padding:0.4rem 0.9rem;
    border-radius:2px;
}

/* ---- Info alert ---- */
.af-alert {
    padding: 0.7rem 1rem;
    border-radius: 3px;
    font-size: 0.82rem;
    margin-bottom: 1.25rem;
    display: flex;
    gap: 0.6rem;
    line-height: 1.6;
}

.af-alert.info    { background:#0f1e38; border:1px solid #1e3a5f; color:#93c5fd; }
.af-alert.success { background:#0c1f14; border:1px solid #166534; color:#86efac; }
.af-alert.warn    { background:#1a1100; border:1px solid #92400e; color:#fde68a; }
.af-alert.err     { background:#1a0a0a; border:1px solid #7f1d1d; color:#fca5a5; }

/* ---- Divider ---- */
.af-divider { height:1px; background:#131e30; margin:1.25rem 0; }

</style>
"""

# ---------------------------------------------------------------------------
# Pipeline definitions
# ---------------------------------------------------------------------------

PIPELINE_STAGES = [
    ("requirement",  "Requirements Agent",  "Product analysis, user stories"),
    ("architect",    "Architect Agent",      "System design, file structure"),
    ("developer",    "Developer Agent",      "Code generation, implementation"),
    ("code_review",  "Code Review Agent",    "Quality and correctness audit"),
    ("qa",           "QA / Test Agent",      "Test execution, validation"),
    ("devops",       "DevOps Agent",         "Dockerfile, CI/CD, deployment"),
]

STATUS_TO_IDX = {
    "initialized":           0,
    "requirements_drafted":  1,
    "architecture_designed": 2,
    "code_generated":        3,
    "review_passed":         4,
    "review_failed":         2,
    "qa_pass":               5,
    "qa_fail":               2,
    "qa_error":              2,
    "deployment_ready":      5,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE_URL, timeout=30.0)


def _handle(resp: httpx.Response) -> Optional[Dict[str, Any]]:
    return None if resp.status_code >= 400 else resp.json()


def _apply(data: Dict[str, Any]) -> None:
    st.session_state.thread_id = data.get("thread_id", st.session_state.thread_id)
    st.session_state.stage     = data.get("stage", "done")
    st.session_state.pending   = data.get("pending_interrupt")
    st.session_state.run_state = data.get("state", {})
    st.session_state.errors    = data.get("errors", []) or []
    st.session_state.status    = data.get("status", "unknown")


def _fetch() -> Optional[Dict[str, Any]]:
    try:
        with _client() as c:
            return _handle(c.get(f"/runs/{st.session_state.thread_id}/state"))
    except Exception:
        return None


def _dedupe_docs(docs: List[Dict]) -> List[Dict]:
    latest, order = {}, []
    for d in (docs or []):
        if not isinstance(d, dict):
            continue
        key = f"{d.get('phase','')}::{d.get('path','') or d.get('title','')}"
        if key not in latest:
            order.append(key)
        latest[key] = d
    return [latest[k] for k in order]


def _badge_html(stage: str) -> str:
    m = {
        "idle":          ("idle",  "IDLE"),
        "processing":    ("run",   "PROCESSING"),
        "awaiting_hitl": ("wait",  "AWAITING REVIEW"),
        "done":          ("done",  "COMPLETE"),
        "error":         ("error", "ERROR"),
        "rewound":       ("wait",  "REWOUND"),
    }
    cls, lbl = m.get(stage, ("idle", stage.upper()))
    return (f'<span class="af-badge af-badge-{cls}">'
            f'<span class="af-dot"></span>{lbl}</span>')


# ---------------------------------------------------------------------------
# Session init
# ---------------------------------------------------------------------------

if "thread_id" not in st.session_state:
    st.session_state.thread_id = uuid.uuid4().hex[:8]
    st.session_state.stage     = "idle"
    st.session_state.pending   = None
    st.session_state.run_state = {}
    st.session_state.errors    = []
    st.session_state.status    = "idle"

# ---------------------------------------------------------------------------
# Inject CSS
# ---------------------------------------------------------------------------

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Navbar  (rendered above both sidebar and main via st.markdown at top level)
# ---------------------------------------------------------------------------

st.markdown(f"""
<div class="af-navbar">
  <div class="af-logo">
    <div class="af-logo-hex"></div>
    <span class="af-logo-text">Agent<em>Flow</em></span>
  </div>
  <div class="af-nav-pills">
    {_badge_html(st.session_state.stage)}
    <div class="af-pill">Thread <b>{st.session_state.thread_id}</b></div>
    <div class="af-pill">Backend <b>{API_BASE_URL.replace('http://','')}</b></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

stage      = st.session_state.stage
run_state  = st.session_state.run_state or {}
cur_status = st.session_state.status or ""
busy       = stage in ("processing", "awaiting_hitl")
cur_idx    = STATUS_TO_IDX.get(cur_status, -1)

with st.sidebar:
    # Header
    st.markdown('<div class="af-sidebar-title">SDLC Automation</div>', unsafe_allow_html=True)

    # ---- LAUNCH SECTION ----
    st.markdown('<span class="af-label">New Run</span>', unsafe_allow_html=True)


    idea = st.text_area(
        "idea_input",
        value="A FastAPI TODO API with CRUD and in-memory storage",
        height=108,
        label_visibility="collapsed",
        placeholder="Describe the application you want to build...",
        key="idea_input",
    )

    if st.button(
        "Launch Pipeline",
        type="primary",
        disabled=busy,
        use_container_width=True,
        key="launch_btn",
    ):
        new_tid = uuid.uuid4().hex[:8]
        try:
            with _client() as c:
                r = c.post("/runs", json={"idea": idea, "thread_id": new_tid})
            data = _handle(r)
            if data:
                _apply(data)
                st.rerun()
            else:
                st.error("API rejected the request.")
        except Exception as e:
            st.error(f"Cannot reach {API_BASE_URL}")


    # ---- PIPELINE DIAGRAM ----
    st.markdown('<div class="af-sidebar-spacer"></div>', unsafe_allow_html=True)
    st.markdown('<span class="af-label">Pipeline</span>', unsafe_allow_html=True)
    st.markdown(
        build_pipeline_html(
            pipeline_stages=PIPELINE_STAGES,
            stage=stage,
            cur_idx=cur_idx,
        ),
        unsafe_allow_html=True,
    )

    # ---- SESSION META ----
    st.markdown('<div class="af-sidebar-spacer"></div>', unsafe_allow_html=True)
    st.markdown('<span class="af-label">Session</span>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="af-meta af-sidebar-meta">
        <div class="af-meta-row">
            <span class="af-meta-k">Thread</span>
            <span class="af-meta-v">{st.session_state.thread_id}</span>
        </div>
        <div class="af-meta-row">
            <span class="af-meta-k">Stage</span>
            <span class="af-meta-v">{stage}</span>
        </div>
        <div class="af-meta-row">
            <span class="af-meta-k">Status</span>
            <span class="af-meta-v">{cur_status or "—"}</span>
        </div>
        <div class="af-meta-row">
            <span class="af-meta-k">QA Retries</span>
            <span class="af-meta-v">{run_state.get("qa_retries", 0)}</span>
        </div>
        <div class="af-meta-row">
            <span class="af-meta-k">Rev Retries</span>
            <span class="af-meta-v">{run_state.get("review_retries", 0)}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- ARTIFACTS ----
    if run_state:
        st.markdown('<div class="af-sidebar-spacer"></div>', unsafe_allow_html=True)
        st.markdown('<span class="af-label">Artifacts</span>', unsafe_allow_html=True)
        arts = [
            ("requirements", "Requirements"),
            ("architecture",  "Architecture"),
            ("codebase",      "Codebase"),
            ("code_review",   "Code Review"),
            ("test_report",   "Test Report"),
            ("deployment",    "Deployment"),
        ]
        rows = ""
        for k, label in arts:
            ok = run_state.get(k) is not None
            rows += (
                '<div class="af-art-row">'
                f'<span class="af-art-name">{label}</span>'
                f'<span class="{"af-art-yes" if ok else "af-art-no"}">'
                f'{"READY" if ok else "PENDING"}</span>'
                "</div>"
            )
        st.markdown(rows, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# MAIN CONTENT
# ---------------------------------------------------------------------------

def render_metrics(state: Dict):
    qa      = state.get("test_report") or {}
    passed  = qa.get("passed", 0)
    failed  = qa.get("failed", 0)
    qa_ret  = state.get("qa_retries", 0)
    rev_ret = state.get("review_retries", 0)
    files   = len((state.get("codebase") or {}).get("files") or [])
    qa_st   = (qa.get("status") or "—").upper()
    qa_cls  = "green" if qa.get("status") == "pass" else ("red" if qa.get("status") in ("fail","error") else "")

    st.markdown(f"""
    <div class="af-metrics">
        <div class="af-metric">
            <div class="af-metric-lbl">Files Generated</div>
            <div class="af-metric-val gold">{files}</div>
            <div class="af-metric-sub">source files</div>
        </div>
        <div class="af-metric">
            <div class="af-metric-lbl">Tests Passed</div>
            <div class="af-metric-val green">{passed}</div>
            <div class="af-metric-sub">{failed} failed</div>
        </div>
        <div class="af-metric">
            <div class="af-metric-lbl">QA Status</div>
            <div class="af-metric-val {qa_cls}">{qa_st}</div>
            <div class="af-metric-sub">{qa_ret} retries</div>
        </div>
        <div class="af-metric">
            <div class="af-metric-lbl">Review Cycles</div>
            <div class="af-metric-val blue">{rev_ret}</div>
            <div class="af-metric-sub">code review loops</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_hitl(intr: Dict):
    phase   = (intr.get("phase") or "unknown").replace("_", " ").upper()
    message = intr.get("message") or "Review the output and approve or reject."
    preview = intr.get("preview") or {}

    st.markdown(f"""
    <div class="af-hitl">
        <div class="af-hitl-hd">
            <div class="af-hitl-dot"></div>
            <div class="af-hitl-title">Human Review Required</div>
            <div class="af-hitl-phase">{phase}</div>
        </div>
        <div class="af-hitl-msg">{message}</div>
    </div>
    """, unsafe_allow_html=True)

    if preview:
        with st.expander("Artifact preview", expanded=True):
            st.json(preview)

    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("Approve — Continue", type="primary", use_container_width=True):
            try:
                with _client() as c:
                    r = c.post(f"/runs/{st.session_state.thread_id}/resume",
                               json={"verdict": "approve", "comment": ""})
                d = _handle(r)
                if d:
                    _apply(d)
                    st.rerun()
            except Exception as e:
                st.error(str(e))

    with c2:
        comment = st.text_input(
            "Feedback",
            placeholder="Describe what should change...",
            key=f"fb_{phase}",
        )
        if st.button("Reject — Revise", use_container_width=True):
            try:
                with _client() as c:
                    r = c.post(f"/runs/{st.session_state.thread_id}/resume",
                               json={"verdict": "reject", "comment": comment or "Please revise."})
                d = _handle(r)
                if d:
                    _apply(d)
                    st.rerun()
            except Exception as e:
                st.error(str(e))


def render_codebase(cb: Dict):
    if not cb:
        return
    files       = cb.get("files") or []
    project_dir = cb.get("project_dir") or "—"
    notes       = cb.get("notes") or ""

    st.markdown(f"""
    <div class="af-card">
        <div class="af-card-hd">
            <span class="af-card-title">Generated Codebase</span>
            <span class="af-badge af-badge-done"><span class="af-dot"></span>{len(files)} FILES</span>
        </div>
        <div class="af-card-bd">
            <div class="af-mono">Project directory
{project_dir}</div>
            {f'<div class="af-mono" style="margin-top:0.5rem;">Notes\n{notes}</div>' if notes else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if files:
        with st.expander(f"Browse source files  ({len(files)})", expanded=False):
            opts = [f.get("path", f"file_{i}") for i, f in enumerate(files)]
            sel  = st.selectbox("File", opts, label_visibility="collapsed", key="file_sel")
            for f in files:
                if f.get("path") == sel:
                    ext  = sel.rsplit(".", 1)[-1].lower() if "." in sel else "text"
                    lang = {"py":"python","yml":"yaml","yaml":"yaml","toml":"toml",
                            "md":"markdown","json":"json","sh":"bash"}.get(ext, "text")
                    st.code(f.get("content", ""), language=lang)
                    break


def render_test_report(report: Dict):
    if not report:
        return
    status = report.get("status", "—")
    passed = report.get("passed", 0)
    failed = report.get("failed", 0)
    errors = report.get("errors") or []
    raw    = report.get("raw_output", "")
    b_cls  = "done" if status == "pass" else "error"

    st.markdown(f"""
    <div class="af-card">
        <div class="af-card-hd">
            <span class="af-card-title">Test Report</span>
            <span class="af-badge af-badge-{b_cls}"><span class="af-dot"></span>{status.upper()}</span>
        </div>
        <div class="af-card-bd">
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;">
                <div>
                    <div class="af-metric-lbl">Passed</div>
                    <div class="af-metric-val green" style="font-size:1.25rem">{passed}</div>
                </div>
                <div>
                    <div class="af-metric-lbl">Failed</div>
                    <div class="af-metric-val red" style="font-size:1.25rem">{failed}</div>
                </div>
                <div>
                    <div class="af-metric-lbl">Status</div>
                    <div class="af-metric-val" style="font-size:1.25rem">{status.upper()}</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for e in errors[:5]:
        st.markdown(f'<div class="af-err">{e}</div>', unsafe_allow_html=True)

    if raw:
        with st.expander("Raw pytest output", expanded=False):
            st.markdown(f"""
            <div class="af-term">
                <div class="af-term-bar">
                    <div class="af-term-dot" style="background:#ef4444"></div>
                    <div class="af-term-dot" style="background:#fbbf24"></div>
                    <div class="af-term-dot" style="background:#22c55e"></div>
                    <span class="af-term-title">pytest output</span>
                </div>
                <div class="af-term-body">{raw}</div>
            </div>
            """, unsafe_allow_html=True)


def render_code_review(review: Dict):
    if not review:
        return
    passed = review.get("passed", False)
    issues = review.get("issues") or []
    fixes  = review.get("required_fixes") or []
    b_cls  = "done" if passed else "error"
    b_lbl  = "PASSED" if passed else "FAILED"

    st.markdown(f"""
    <div class="af-card">
        <div class="af-card-hd">
            <span class="af-card-title">Code Review</span>
            <span class="af-badge af-badge-{b_cls}"><span class="af-dot"></span>{b_lbl}</span>
        </div>
        <div class="af-card-bd">
            <div style="font-family:'DM Mono',monospace;font-size:0.74rem;color:#7f95b0;">
                {len(issues)} issue(s) &nbsp;/&nbsp; {len(fixes)} required fix(es)
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if issues:
        with st.expander(f"Issues  ({len(issues)})", expanded=not passed):
            sev_color = {"HIGH": "#f87171", "MEDIUM": "#fbbf24", "LOW": "#7f95b0"}
            for iss in issues:
                sev  = (iss.get("severity") or "medium").upper()
                col  = sev_color.get(sev, "#7f95b0")
                loc  = iss.get("file", "?")
                if iss.get("line"):
                    loc += f":{iss['line']}"
                st.markdown(f"""
                <div class="af-issue" style="border-color:{col};">
                    <div class="af-issue-loc" style="color:{col};">
                        [{sev}] &nbsp; <span style="color:#9ab0c9;">{loc}</span>
                    </div>
                    <div style="color:#bdd0e3;">{iss.get("message","")}</div>
                </div>
                """, unsafe_allow_html=True)

    if fixes:
        with st.expander(f"Required Fixes  ({len(fixes)})", expanded=not passed):
            for i, fix in enumerate(fixes, 1):
                st.markdown(f"""
                <div style="padding:0.5rem 0.85rem;background:#080c14;border-left:2px solid #1e2d45;
                            border-radius:2px;margin-bottom:0.35rem;font-size:0.78rem;
                            color:#bdd0e3;line-height:1.6;">
                    <span style="font-family:'DM Mono',monospace;color:#91a6c1;">[{i:02d}]</span>
                    &nbsp; {fix}
                </div>
                """, unsafe_allow_html=True)


def render_deployment(dep: Dict):
    if not dep:
        return
    pr_url = dep.get("pr_url")
    branch = dep.get("branch_name") or "—"
    repo   = dep.get("repo_name") or "—"

    st.markdown(f"""
    <div class="af-card">
        <div class="af-card-hd">
            <span class="af-card-title">Deployment</span>
            <span class="af-badge af-badge-done"><span class="af-dot"></span>READY</span>
        </div>
        <div class="af-card-bd">
            <div class="af-meta">
                <div class="af-meta-row"><span class="af-meta-k">Repository</span><span class="af-meta-v">{repo}</span></div>
                <div class="af-meta-row"><span class="af-meta-k">Branch</span><span class="af-meta-v">{branch}</span></div>
                <div class="af-meta-row"><span class="af-meta-k">Pull Request</span><span class="af-meta-v">{"linked" if pr_url else "—"}</span></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if pr_url:
        st.link_button("Open Pull Request on GitHub", pr_url)

    c1, c2 = st.columns(2, gap="small")
    with c1:
        if dep.get("dockerfile"):
            with st.expander("Dockerfile", expanded=False):
                st.code(dep["dockerfile"], language="dockerfile")
    with c2:
        if dep.get("ci_yaml"):
            with st.expander("CI Workflow", expanded=False):
                st.code(dep["ci_yaml"], language="yaml")


def render_phase_docs(docs: List[Dict]):
    if not docs:
        return
    deduped = _dedupe_docs(docs)
    st.markdown('<div class="af-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'DM Mono\',monospace;font-size:0.66rem;color:#91a6c1;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:1rem;">Phase Documentation</div>', unsafe_allow_html=True)

    phase_col = {
        "requirements": "#60a5fa",
        "architecture": "#a78bfa",
        "developer":    "#4ade80",
        "qa":           "#fbbf24",
        "devops":       "#e879f9",
    }

    for doc in deduped:
        phase   = doc.get("phase", "report")
        title   = doc.get("title") or phase.title()
        col     = phase_col.get(phase, "#64748b")
        content = doc.get("content_markdown") or ""

        with st.expander(title, expanded=False):
            st.markdown(f"""
            <span style="display:inline-block;font-family:'DM Mono',monospace;font-size:0.58rem;
                         text-transform:uppercase;letter-spacing:0.09em;padding:0.12rem 0.45rem;
                         border-radius:2px;background:{col}1a;color:{col};border:1px solid {col}33;
                         margin-bottom:0.75rem;">{phase}</span>
            """, unsafe_allow_html=True)
            st.markdown(content)


# ---- Route to the right view -----------------------------------------------

with st.container():
    st.markdown('<div class="af-content">', unsafe_allow_html=True)

    errors = st.session_state.errors or []

    # ---- IDLE ----
    if stage == "idle":
        st.markdown("""
        <div class="af-hero">
            <div class="af-hero-hex"></div>
            <div>
                <div class="af-hero-title">AgentFlow</div>
                <div class="af-hero-sub">
                    Multi-agent SDLC automation. Describe your application idea in the
                    sidebar and launch the pipeline to generate production-grade code,
                    tests, and a GitHub pull request — autonomously.
                </div>
            </div>
            <div class="af-hero-stats">
                <div class="af-hero-stat">
                    <div class="af-hero-stat-n">6</div>
                    <div class="af-hero-stat-l">Agents</div>
                </div>
                <div class="af-hero-stat">
                    <div class="af-hero-stat-n">5</div>
                    <div class="af-hero-stat-l">HITL Gates</div>
                </div>
                <div class="af-hero-stat">
                    <div class="af-hero-stat-n">A2A</div>
                    <div class="af-hero-stat-l">Protocol</div>
                </div>
            </div>
            <div class="af-hero-hint">Configure and launch a pipeline run from the sidebar</div>
        </div>
        """, unsafe_allow_html=True)

    # ---- PROCESSING ----
    elif stage == "processing":
        active_name = next(
            (n for k, n, _ in PIPELINE_STAGES if k == list(STATUS_TO_IDX.keys())[
                list(STATUS_TO_IDX.values()).index(cur_idx)
                if cur_idx in STATUS_TO_IDX.values() else 0
            ]), cur_status
        )

        st.markdown(f"""
        <div class="af-page-hd">
            <div class="af-page-title">Pipeline Running</div>
            <div class="af-page-sub">
                Status: <span style="font-family:'DM Mono',monospace;color:#c9d6e5;">{cur_status}</span>
                &nbsp;&nbsp; The agents are working. This page refreshes automatically.
            </div>
        </div>
        """, unsafe_allow_html=True)

        render_metrics(run_state)

        if run_state.get("context_summary"):
            st.markdown(f"""
            <div class="af-card">
                <div class="af-card-hd"><span class="af-card-title">Context Summary</span></div>
                <div class="af-card-bd" style="font-size:0.82rem;color:#bdd0e3;line-height:1.75;">
                    {run_state["context_summary"]}
                </div>
            </div>
            """, unsafe_allow_html=True)

        if errors:
            for e in errors:
                st.markdown(f'<div class="af-err">{e}</div>', unsafe_allow_html=True)

        data = _fetch()
        if data:
            _apply(data)
        time.sleep(POLL_INTERVAL_SEC)
        st.rerun()

    # ---- HITL ----
    elif stage == "awaiting_hitl":
        intr        = st.session_state.pending or {}
        phase_label = (intr.get("phase") or "unknown").replace("_", " ").title()

        st.markdown(f"""
        <div class="af-page-hd">
            <div class="af-page-title">Human Review &mdash; {phase_label}</div>
            <div class="af-page-sub">
                The pipeline is paused at a checkpoint. Review the artifact and approve
                to continue, or reject with feedback to trigger a revision.
            </div>
        </div>
        """, unsafe_allow_html=True)

        render_metrics(run_state)
        render_hitl(intr)

        # Show relevant context
        if run_state.get("codebase"):
            render_codebase(run_state["codebase"])
        if run_state.get("code_review"):
            render_code_review(run_state["code_review"])
        if run_state.get("test_report"):
            render_test_report(run_state["test_report"])

    # ---- DONE ----
    elif stage == "done":
        st.markdown("""
        <div class="af-page-hd">
            <div class="af-page-title">Pipeline Complete</div>
            <div class="af-page-sub">
                All SDLC phases executed successfully. Review your generated artifacts,
                source files, test results, and phase documentation below.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="af-alert success">
            <span>+</span>
            All agents finished. The generated codebase has been pushed to GitHub.
        </div>
        """, unsafe_allow_html=True)

        render_metrics(run_state)

        if run_state.get("deployment"):
            render_deployment(run_state["deployment"])

        if run_state.get("codebase"):
            render_codebase(run_state["codebase"])

        cr = run_state.get("code_review")
        tr = run_state.get("test_report")
        if cr or tr:
            c1, c2 = st.columns(2, gap="small")
            with c1:
                render_code_review(cr)
            with c2:
                render_test_report(tr)

        if run_state.get("docs"):
            render_phase_docs(run_state["docs"])

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        with st.expander("Full state inspector", expanded=False):
            st.json(run_state)

    # ---- ERROR ----
    elif stage == "error":
        st.markdown("""
        <div class="af-page-hd">
            <div class="af-page-title" style="color:#f87171;">Pipeline Error</div>
            <div class="af-page-sub">
                A fatal error stopped the pipeline. Review the details below,
                then launch a new run from the sidebar.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if errors:
            for e in errors:
                st.markdown(f'<div class="af-err">{e}</div>', unsafe_allow_html=True)

        if run_state:
            with st.expander("State at failure", expanded=False):
                st.json(run_state)

    # ---- Persistent error tray (non-error stages) ----
    if errors and stage not in ("error", "processing"):
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        with st.expander(f"Errors  ({len(errors)})", expanded=False):
            for e in errors:
                st.markdown(f'<div class="af-err">{e}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
