"""PolicyForge Streamlit demo — policy in → rules → flagged providers."""

import streamlit as st

st.set_page_config(page_title="PolicyForge", page_icon="🏥", layout="wide")

st.title("PolicyForge")
st.caption("Agentic Policy-to-Edit Engine for Medicare Payment Integrity")

st.info(
    "Pipeline scaffold ready. Next steps: pull anchor policy (NCD 150.3), "
    "wire LangGraph agents, and connect CMS Part B data."
)

with st.sidebar:
    st.header("Configuration")
    policy_id = st.selectbox(
        "Policy",
        ["NCD 150.3 — Bone Mass Measurement"],
    )
    run = st.button("Run Pipeline", type="primary")

if run:
    st.warning("Pipeline not yet implemented — see src/graph.py")

st.markdown("---")
st.subheader("Architecture")
st.markdown(
    """
    1. **Retriever** — hybrid RAG over policy corpus
    2. **Extractor** — policy → structured JSON criteria
    3. **Critic** — span-level citation grounding
    4. **Compiler** — criteria → executable edit
    5. **Adjudicator** — apply edit to CMS Part B data
    6. **Explainer** — cited rationale for flagged providers
    """
)
