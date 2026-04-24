import os
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx
import streamlit as st

# --- Configuration ---
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
POLL_INTERVAL_SEC = 1.0 

st.set_page_config(
    page_title='AgentFlow',
    layout='wide',
    initial_sidebar_state='expanded'
)

# --- THE AGENTFLOW DESIGN SYSTEM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono&display=swap');
    
    :root {
        --bg-main: #020617;
        --card-bg: rgba(30, 41, 59, 0.5);
        --accent-glow: #3B82F6;
        --accent-secondary: #8B5CF6;
        --border: rgba(255, 255, 255, 0.1);
        --text-dim: #94A3B8;
    }

    .stApp {
        background-color: var(--bg-main);
        color: #F8FAFC;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Prominent Branding */
    .brand-hero {
        padding: 2rem 0;
        text-align: center;
        margin-bottom: 2rem;
        background: radial-gradient(circle at center, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
    }
    .brand-name {
        font-size: 4rem;
        font-weight: 800;
        letter-spacing: -2px;
        background: linear-gradient(135deg, #FFF 30%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .brand-tagline {
        color: var(--text-dim);
        font-size: 1.1rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        font-weight: 500;
    }

    /* Glass Cards */
    .saas-card {
        background: var(--card-bg);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 2rem;
        transition: transform 0.3s ease, border-color 0.3s ease;
    }
    .saas-card:hover {
        border-color: rgba(59, 130, 246, 0.4);
    }

    /* Status Indicator */
    .status-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        margin: 1.5rem 0;
    }
    .pulse-dot {
        height: 12px;
        width: 12px;
        background-color: #3B82F6;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 0 0 rgba(59, 130, 246, 1);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(59, 130, 246, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
    }

    /* Custom Navigation Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid var(--border);
    }

    /* Sidebar Buttons */
    div.stButton > button {
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        border: none;
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: white;
        width: 100%;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.4);
        transform: translateY(-2px);
    }

    /* Tabs Override */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent !important;
        border: none !important;
        color: var(--text-dim);
    }
    .stTabs [aria-selected="true"] {
        color: #3B82F6 !important;
        border-bottom: 2px solid #3B82F6 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- State Engine ---
if 'thread_id' not in st.session_state:
    st.session_state.update({
        'thread_id': uuid.uuid4().hex[:8],
        'stage': 'idle',
        'status': 'Engine Standby',
        'latest_state': {},
        'errors': [],
        'pending_interrupt': None
    })

def _call_backend(method: str, endpoint: str, data: dict = None) -> Optional[Dict[str, Any]]:
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
            resp = client.request(method, endpoint, json=data)
            return resp.json() if resp.status_code < 400 else None
    except Exception:
        return None

def sync_all():
    data = _call_backend('GET', f'/runs/{st.session_state.thread_id}/state')
    if data:
        st.session_state.stage = data.get('stage', 'done')
        st.session_state.status = data.get('status', 'Analyzing')
        st.session_state.latest_state = data.get('state', {})
        st.session_state.pending_interrupt = data.get('pending_interrupt')
        st.session_state.errors = data.get('errors', []) or []

# --- Sidebar ---
with st.sidebar:
    st.markdown("### Configuration")
    idea_input = st.text_area("What are we building today?", placeholder="Describe the app architecture...", height=200)
    
    is_working = st.session_state.stage in ('processing', 'awaiting_hitl')
    if st.button("Launch AgentFlow", disabled=is_working):
        new_tid = uuid.uuid4().hex[:8]
        res = _call_backend('POST', '/runs', {'idea': idea_input, 'thread_id': new_tid})
        if res:
            st.session_state.thread_id = new_tid
            sync_all()
            st.rerun()
            
    st.divider()
    st.caption(f"Session: `{st.session_state.thread_id}`")
    if st.button("New Environment", type="secondary"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# --- Main Workspace ---

# Header Branding
st.markdown("""
<div class="brand-hero">
    <h1 class="brand-name">AgentFlow</h1>
    <p class="brand-tagline">Agentic Software Development</p>
</div>
""", unsafe_allow_html=True)

# Status Bar
if st.session_state.stage != 'idle':
    st.markdown(f"""
    <div class="status-container">
        <span class="pulse-dot"></span>
        <span style="font-weight: 600; font-size: 1.2rem; color: #3B82F6;">{st.session_state.status.upper()}</span>
    </div>
    """, unsafe_allow_html=True)

# Main Logic
if st.session_state.stage == 'idle':
    st.markdown("""
    <div style="text-align: center; padding: 5rem 0;">
        <h2 style="color: #94A3B8;">Welcome to the future of Engineering.</h2>
        <p style="color: #64748B;">Enter your requirements in the left panel to begin your autonomous build.</p>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.stage == 'processing':
    # High-End Visualization of Work
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div class="saas-card" style="text-align: center;">
            <h3 style="margin-bottom: 1rem;">Architecting your Solution</h3>
            <p style="color: var(--text-dim);">Our agents are currently synthesizing requirements, 
            designing architecture, and drafting the implementation plan.</p>
            <br>
            <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 16px; border: 1px solid var(--border);">
                <code style="color: #60A5FA;">Current Thread: {st.session_state.thread_id}</code>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    time.sleep(POLL_INTERVAL_SEC)
    sync_all()
    st.rerun()

elif st.session_state.stage == 'awaiting_hitl':
    intr = st.session_state.pending_interrupt or {}
    
    st.markdown(f"""
    <div class="saas-card" style="border-left: 4px solid #F59E0B;">
        <h2 style="margin:0;">Review Required</h2>
        <p style="color: var(--text-dim);">Agent is requesting approval for phase: <b>{intr.get('phase', 'Processing')}</b></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["📋 Data Preview", "Feedback Loop"])
    with t1:
        st.json(intr.get('preview', {}))
    with t2:
        fb = st.text_area("Add specific instructions or changes...")
        
    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button("Approve & Deploy"):
        _call_backend('POST', f'/runs/{st.session_state.thread_id}/resume', {'verdict': 'approve', 'comment': ''})
        sync_all()
        st.rerun()
    if c2.button("Request Revision", type="secondary"):
        _call_backend('POST', f'/runs/{st.session_state.thread_id}/resume', {'verdict': 'reject', 'comment': fb or 'Please revise.'})
        sync_all()
        st.rerun()

elif st.session_state.stage == 'done':
    st.markdown("### Build Manifest")
    final = st.session_state.latest_state
    
    tab_doc, tab_git, tab_meta = st.tabs(["Documentation", "Deployment", "System Metadata"])
    
    with tab_doc:
        for d in final.get('docs', []):
            with st.expander(f"{d.get('title', 'Module')}", expanded=True):
                st.markdown(d.get('content_markdown', ''))
                
    with tab_git:
        dep = final.get('deployment', {})
        if dep.get('pr_url'):
            st.markdown(f"""
            <div class="saas-card" style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, transparent 100%); border-color: #10B981;">
                <h3>Code Repository Ready</h3>
                <p>The implementation has been successfully pushed and verified.</p>
                <a href="{dep['pr_url']}" target="_blank" style="text-decoration:none;">
                    <button style="width:100%; background:#10B981; color:white; border:none; padding:12px; border-radius:12px; font-weight:700; cursor:pointer;">
                        OPEN PULL REQUEST
                    </button>
                </a>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Artifacts generated in local ephemeral workspace.")

    with tab_meta:
        st.json(final)

# Error Toasts
if st.session_state.errors:
    for e in st.session_state.errors:
        st.toast(e, icon="⚠️")