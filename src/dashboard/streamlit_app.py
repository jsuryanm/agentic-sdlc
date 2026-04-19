import uuid
import streamlit as st
from langgraph.types import Command

from src.pipelines.graph import build_graph, make_checkpointer
from src.pipelines.state import initial_state


st.set_page_config(page_title="Agentic SDLC", page_icon="🤖", layout="wide")
st.title("🤖 Agentic SDLC")

# --- Persist graph across reruns ---
if "cp_ctx" not in st.session_state:
    st.session_state.cp_ctx = make_checkpointer()
    st.session_state.checkpointer = st.session_state.cp_ctx.__enter__()
    st.session_state.graph = build_graph(st.session_state.checkpointer)
    st.session_state.thread_id = str(uuid.uuid4())[:8]
    st.session_state.stage = "idle"
    st.session_state.pending_interrupt = None

graph = st.session_state.graph
cfg = {"configurable": {"thread_id": st.session_state.thread_id}}


def advance(result):
    """Handle graph output: either interrupt payload or terminal state."""
    if "__interrupt__" in result:
        intr = result["__interrupt__"][0]
        st.session_state.pending_interrupt = intr.value
        st.session_state.stage = "awaiting_hitl"
    else:
        st.session_state.pending_interrupt = None
        st.session_state.stage = "done"
    st.session_state.latest_state = result


# --- Sidebar: start a new run ---
with st.sidebar:
    st.subheader("New run")
    idea = st.text_area("Your idea", value="A FastAPI TODO API with CRUD and in-memory storage")
    if st.button("▶ Start", type="primary", disabled=st.session_state.stage == "awaiting_hitl"):
        st.session_state.thread_id = str(uuid.uuid4())[:8]
        cfg = {"configurable": {"thread_id": st.session_state.thread_id}}
        init = initial_state(idea, st.session_state.thread_id)
        result = graph.invoke(init, config=cfg)
        advance(result)
        st.rerun()

    st.divider()
    st.caption(f"Thread: `{st.session_state.thread_id}`")
    st.caption(f"Stage: **{st.session_state.stage}**")


# --- Main: HITL prompt or final summary ---
if st.session_state.stage == "awaiting_hitl":
    intr = st.session_state.pending_interrupt
    phase = intr["phase"]
    st.subheader(f"🙋 Human review — {phase}")
    st.json(intr["preview"] or {}, expanded=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Approve", type="primary"):
            result = graph.invoke(
                Command(resume={"verdict": "approve", "comment": ""}),
                config=cfg,
            )
            advance(result); st.rerun()
    with col2:
        comment = st.text_input("Reject with feedback:", key=f"fb_{phase}")
        if st.button("Reject & retry"):
            result = graph.invoke(
                Command(resume={"verdict": "reject", "comment": comment or "Please revise."}),
                config=cfg,
            )
            advance(result); st.rerun()

elif st.session_state.stage == "done":
    st.success("✔ Run complete")
    final = st.session_state.latest_state
    if final.get("deployment", {}).get("pr_url"):
        st.link_button("🔗 Open PR", final["deployment"]["pr_url"])
    with st.expander("Final state", expanded=False):
        st.json(final)

else:
    st.info("Enter an idea in the sidebar and click Start.")