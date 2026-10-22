import streamlit as st
from dotenv import load_dotenv

from src.api.client import call

load_dotenv()
st.set_page_config(page_title="Conviction", page_icon="📄", layout="wide")
st.title("Conviction")
st.caption("A personal investor's decision-support agent grounded in cited SEC filings.")

DEFAULT_TICKERS = ["NVDA", "AMD", "MSFT", "GOOGL"]

with st.sidebar:
    user_key = st.text_input("Your API key (optional)", type="password",
                             help="Leave blank to use the shared demo key.")


def available_tickers():
    if "tickers" not in st.session_state:
        res = call("GET", "/tickers", user_key)
        if not res.ok:
            return DEFAULT_TICKERS
        st.session_state["tickers"] = res.data["tickers"]
    return st.session_state["tickers"]


def request_id_caption(res):
    if res.request_id:
        st.caption(f"request ID: {res.request_id}")


tickers = available_tickers()
tab_ask, tab_diff = st.tabs(["Ask", "Risk Diff"])

# ---------- Ask ----------
with tab_ask:
    with st.sidebar:
        st.header("Scope")
        ticker = st.selectbox("Ticker", ["(all)"]+tickers, index=0)
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
        # Reruns (e.g. opening the other tab) shouldn't re-ask and spend the key's quota.
        sig = (question, ticker, k, user_key)
        if st.session_state.get("ask_sig") != sig:
            with st.spinner("Retrieving results..."):
                st.session_state["ask_res"] = call(
                    "POST", "/ask", user_key,
                    json={"question": question, "k": k,
                          "ticker": None if ticker == "(all)" else ticker})
            st.session_state["ask_sig"] = sig
        result = st.session_state["ask_res"]

        if not result.ok:
            st.warning(result.error)
        else:
            st.markdown("### Answer")
            st.markdown(result.data["answer"])
        request_id_caption(result)

        sources = result.data["sources"] if result.ok else []
        if sources:
            st.markdown("### Sources")
            for s in sources:
                label = (f"[{s['n']}] {s['ticker']} 10-K {s['filing_date']} — "
                         f"{s['item']} · {s['item_title']}")
                with st.expander(label):
                    st.write(s["text"][:1500])

# ---------- Risk Diff ----------
with tab_diff:
    st.subheader("YoY risk factor changes")
    st.caption("Compares Item 1A across a company's two most recent 10-K filings.")

    dt = st.selectbox("Company", tickers, key="diff_ticker")
    if st.button("Show diff", type="primary"):
        res = call("GET", f"/risk-diff/{dt}", user_key, ok_statuses=(200, 404))
        if not res.ok:
            st.warning(res.error)
            request_id_caption(res)
        elif res.status == 404:
            st.info(f"No precomputed diff for {dt}. Run: python -m scripts.ingest_watchlist")
        else:
            d = res.data
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