import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

import config

st.set_page_config(
    page_title="Ask Your Contracts · Contract Intelligence",
    page_icon="💬",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📄 Contract Intelligence")
    mode = "🟡 Mock Mode" if config.USE_MOCK_EXTRACTOR else "🟢 Live Mode"
    st.markdown(f"**{mode}**")
    st.divider()
    st.divider()
    st.caption("Built with Claude API · CUAD Dataset")
    st.markdown("**Collection stats**")
    try:
        from rag.embedder import ContractEmbedder
        @st.cache_resource
        def _embedder():
            return ContractEmbedder()
        e = _embedder()
        st.caption(f"{e.collection.count():,} chunks indexed")
    except Exception:
        st.caption("Embedder not initialised")


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


# ── QA resource ───────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading contract search engine…")
def _qa():
    from rag.qa_chain import ContractQA
    return ContractQA()


# ── Header ────────────────────────────────────────────────────────────────────
st.title("💬 Ask Your Contracts")
st.markdown(
    "Semantic search across all **31 contracts** powered by "
    "**ChromaDB** + **Claude**.  \n"
    "Ask anything about payment terms, penalties, renewal dates, or governing law."
)

if config.USE_MOCK_EXTRACTOR:
    st.warning(
        "⚡ Running in mock mode — answers are illustrative. "
        "Add your Anthropic API key to `config.py` and set "
        "`USE_MOCK_EXTRACTOR = False` for live Claude responses."
    )

st.divider()

# ── Suggested questions ───────────────────────────────────────────────────────
st.markdown("**Suggested questions:**")
sug1, sug2, sug3 = st.columns(3)

if sug1.button("Which contracts mention penalties?", use_container_width=True):
    st.session_state.pending_question = "Which contracts mention penalties for late delivery?"
    st.rerun()
if sug2.button("What payment terms exist?", use_container_width=True):
    st.session_state.pending_question = "What are the payment terms in the agreements?"
    st.rerun()
if sug3.button("Which contracts expire soon?", use_container_width=True):
    st.session_state.pending_question = "Which contracts are expiring or up for renewal?"
    st.rerun()

st.divider()

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "sources" in msg:
            with st.expander(
                f"Sources ({msg['chunks_retrieved']} chunks retrieved)", expanded=False
            ):
                sources_df = pd.DataFrame(msg["sources"])
                st.dataframe(
                    sources_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "filename":    st.column_config.TextColumn("File",      width="large"),
                        "page_number": st.column_config.NumberColumn("Page",    width="small"),
                        "chunk_id":    st.column_config.TextColumn("Chunk ID",  width="medium"),
                    },
                )

# ── Input handling ────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask a question about your contracts…")
question = prompt or st.session_state.pending_question

if question:
    st.session_state.pending_question = None

    # Add user message
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Generate answer
    with st.chat_message("assistant"):
        with st.spinner("Searching contracts…"):
            try:
                qa = _qa()
                result = qa.answer(question)
            except Exception as exc:
                st.error(f"Error: {exc}")
                st.stop()

        st.markdown(result["answer"])

        with st.expander(
            f"Sources ({result['chunks_retrieved']} chunks retrieved)", expanded=False
        ):
            sources_df = pd.DataFrame(result["sources"])
            st.dataframe(
                sources_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "filename":    st.column_config.TextColumn("File",      width="large"),
                    "page_number": st.column_config.NumberColumn("Page",    width="small"),
                    "chunk_id":    st.column_config.TextColumn("Chunk ID",  width="medium"),
                },
            )

    # Persist to session
    st.session_state.messages.append({
        "role":             "assistant",
        "content":          result["answer"],
        "sources":          result["sources"],
        "chunks_retrieved": result["chunks_retrieved"],
    })
