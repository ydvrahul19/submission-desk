import os
from pathlib import Path

import streamlit as st

from core.fields import BY_KEY, display
from core.ingest import read_file
from core.llm import make_client
from core.models import Doc
from core.pipeline import analyze

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def md(s):   # Streamlit markdown reads $...$ as maths; escape dollar signs
    return str(s).replace("$", "\\$")


def ht(s):   # same, for text placed inside HTML blocks
    return str(s).replace("$", "&#36;")


st.set_page_config(page_title="Submission Desk", page_icon="📋", layout="wide")
st.markdown("""<style>
.block-container{padding-top:2rem;max-width:1200px}
h1,h2,h3{font-family:Georgia,'Times New Roman',serif;letter-spacing:-.01em}
.verdict{padding:18px 22px;border-radius:10px;border-left:6px solid;margin-bottom:18px;background:#fff}
.v-pass{border-color:#17794a}.v-fail{border-color:#b42318}.v-hold{border-color:#9a5b00}
.verdict h2{margin:0;font-size:1.7rem}.verdict p{margin:.2rem 0 0;color:#5b6b82}
.rule{display:flex;gap:12px;padding:10px 14px;margin-bottom:8px;background:#fff;border:1px solid #d3dce6;border-radius:8px}
.pill{font-weight:600;font-size:.78rem;padding:3px 10px;border-radius:99px;min-width:86px;text-align:center;height:fit-content}
.p-pass{background:#e2f4ea;color:#17794a}.p-fail{background:#fde8e6;color:#b42318}.p-needs_info{background:#fdf0d5;color:#9a5b00}
.ev{font-family:ui-monospace,Menlo,monospace;font-size:.82rem;color:#5b6b82}
mark{background:#fff2a8;padding:0 2px;border-radius:3px}
</style>""", unsafe_allow_html=True)

st.title("Submission desk")
st.caption("Reads a broker email and its attachments (PDF, Word, Excel, CSV, .eml), extracts the facts with evidence, checks five rules, and drafts the reply.")

client = make_client()
mode_label = {"anthropic": "Claude API", "ollama": "local Ollama model"}.get(os.getenv("LLM_PROVIDER", "none").lower(), "rule-based only") if client else "rule-based only"

with st.sidebar:
    st.subheader("Submission")
    sample_dirs = sorted(p for p in (Path(__file__).parent / "samples").glob("*") if p.is_dir())
    pick = st.selectbox("Sample", ["(none)"] + [p.name for p in sample_dirs])
    files = st.file_uploader("Or upload files", accept_multiple_files=True, type=["eml", "pdf", "docx", "xlsx", "csv", "txt"])
    body = st.text_area("Or paste email text", height=140)
    st.caption(f"Extraction: {mode_label}")
    go = st.button("Analyze submission", type="primary", use_container_width=True)

if go:
    docs = []
    if pick != "(none)":
        for f in sorted((Path(__file__).parent / "samples" / pick).iterdir()):
            docs += read_file(f.name, f.read_bytes())
    for f in files or []:
        docs += read_file(f.name, f.getvalue())
    if body.strip():
        docs.append(Doc("pasted email", [body]))
    if not docs:
        st.warning("Choose a sample, upload files, or paste email text first.")
        st.stop()
    with st.spinner("Reading documents and checking rules"):
        res = analyze(docs, client)
    if res["warning"]:
        st.warning(res["warning"])
    st.markdown(f"<div class='verdict v-{res['state']}'><h2>{res['headline'].split(':')[0]}</h2><p>{res['headline'].split(': ',1)[-1]}</p></div>", unsafe_allow_html=True)
    L = {"pass": "Pass", "fail": "Fail", "needs_info": "Needs info"}
    left, right = st.columns([1, 1.4], gap="large")
    with left:
        st.subheader("Rule checks")
        for r in res["rules"]:
            st.markdown(f"<div class='rule'><span class='pill p-{r.state}'>{L[r.state]}</span><div><b>{ht(r.name)}</b><br><span style='color:#5b6b82'>{ht(r.reason)}</span></div></div>", unsafe_allow_html=True)
        st.subheader("Underwriter summary")
        st.markdown(md(res["summary"]))
    with right:
        st.subheader("Extracted fields and evidence")
        for x in res["fields"].values():
            f = BY_KEY[x.key]
            tag = {"ok": "", "missing": " - missing", "conflict": " - conflict"}[x.status]
            val = " / ".join(display(f, v) for v in x.distinct) if x.distinct else "-"
            with st.expander(md(f"{x.label}: {val}{tag}"), expanded=x.status != "ok"):
                if not x.candidates:
                    st.write("No evidence found in any document.")
                for c in x.candidates:
                    st.markdown(f"**{md(c.source)}** ({c.method})  \n<span class='ev'>{ht(c.quote)}</span>", unsafe_allow_html=True)
    st.subheader("Draft follow-up email")
    st.code(res["email"], language=None)
    with st.expander("Documents read"):
        for d in docs:
            st.markdown(f"**{d.name}** - {len(d.pages)} page(s), {len(d.text)} characters")
else:
    st.info("Pick a sample or upload a submission in the sidebar, then choose Analyze submission.")
