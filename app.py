import streamlit as st
from dotenv import load_dotenv

from src.pipeline import ask
from src.index.store import get_collection
from src.analyze.risk_diff import load_risk_diff

load_dotenv()
st.set_page_config(page_title="Conviction", page_icon="📄", layout="wide")
st.title("Conviction")
st.caption("A personal investor's decision-support agent grounded in cited SEC filings.")

@st.cache_data(show_spinner=False)
def available_tickers():
    try:
        col = get_collection()
        metas = col.get(include=["metadatas"], limit=5000)["metadatas"]
        return sorted({m["ticker"] for m in metas if m and "ticker" in m})
    except Exception as e:
        return ["NVDA", "AMD", "MSFT", "GOOGL"]

tickers = available_tickers()
tab_ask, tab_diff = st.tabs(["Ask", "Risk Diff"])

# ---------- Ask ----------
with tab_ask:
    with st.sidebar:
        st.header("Scope")
        ticker = st.selectbox("Ticker", ["(all)"]+tickers, index=0)
        doc_type = st.selectbox("Document type", ["(all)", "10-K"], index=1)
        k = st.slider("Chunks retrieved (k)", 3, 12, 8)
        st.caption("Scoping to one ticker prevents cross-company bleed in results.")

    examples = ["What are NVDA's primary risk factors?",
                "How does NVDA describe its data center business?",
                "What does NVDA say about export controls?",
                ]
    cols = st.columns(len(examples))
    for c, ex in zip(cols, examples):
        if c.button(ex, use_container_width=True):
            st.session_state["q"] = ex

    question = st.text_input("Ask a question about a filing", key="q")
    if question:
        with st.spinner("Retrieving results..."):
            result = ask(question,
                         k=k,
                         ticker=None if ticker == "(all)" else ticker,
                         doc_type=None if doc_type == "(all)" else doc_type,)

        if not result["ok"]:
            st.warning(result["answer"])
        else:
            st.markdown("### Answer")
            st.markdown(result["answer"])

        sources = result.get("sources_used", [])
        if sources:
            st.markdown("### Sources")
            for i, s in enumerate(sources, 1):
                m = s.get("metadata", {})
                label = (f"[{i}] {m.get('ticker', '?')} {m.get('filing_type', '?')} — "
                         f"{m.get('item', '?')} · {m.get('item_title', '')}")
                with st.expander(label):
                    d = s.get("distance")
                    if d is not None:
                        st.caption(f"distance = {d:.3f}")
                    st.write((s.get("text") or "")[:1500])

# ---------- Risk Diff ----------
with tab_diff:
    st.subheader("YoY risk factor changes")
    st.caption("Compares Item 1A across a company's two most recent 10-K filings.")

    dt = st.selectbox("Company", tickers, key="diff_ticker")
    if st.button("Show diff", type="primary"):
        d = load_risk_diff(dt)
        if d is None:
            st.info(f"No precomputed diff for {dt}. Run: python -m scripts.ingest_watchlist")
        else:
            st.caption(f"{d['prior_year']} → {d['current_year']}")
            diff = d.get("diff", {})
            new = diff.get("new",[])
            removed = diff.get("removed",[])
            changed = diff.get("changed",[])

            c1, c2, c3 = st.columns(3)
            c1.metric("New", len(new))
            c2.metric("Removed", len(removed))
            c3.metric("Changed", len(changed))

            for label, items in [("New risks", new),
                                 ("Dropped risks", removed),
                                 ("Changed risks", changed)]:
                st.markdown(f"### {label}")
                if not items:
                    st.caption(f"No items found for {label}")
                for it in items:
                    if isinstance(it, dict):
                        st.markdown(f"**{it.get('risk', '—')}**")
                        detail = it.get("what_changed") or it.get("evidence") or ""
                        if detail:
                            st.write(detail)
                    else:
                        st.write(it)
                    st.divider()