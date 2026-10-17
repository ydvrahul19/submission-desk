import re
from typing import Callable, Dict, List, Optional

from .fields import FIELDS, normalize
from .llm import extract_llm
from .models import Candidate, Doc, FieldResult


def extract_regex(docs: List[Doc]) -> Dict[str, List[Candidate]]:
    out: Dict[str, List[Candidate]] = {}
    for d in docs:
        for pi, page in enumerate(d.pages):
            src = d.name + (f" p{pi+1}" if len(d.pages) > 1 else "")
            for line in page.splitlines():
                for f in FIELDS:
                    m = re.search(f.pattern, line, re.I)
                    if m:
                        v = normalize(f.type, m.group(1))
                        if v is not None:
                            out.setdefault(f.key, []).append(Candidate(v, src, line.strip(), "regex"))
    return out


def extract(docs: List[Doc], client: Optional[Callable[[str], str]] = None):
    """Returns (results, mode, warning). LLM first; rule-based fills any field the LLM could not evidence."""
    rx, llm, mode, warn = extract_regex(docs), {}, "rule-based", ""
    if client:
        try:
            llm, mode = extract_llm(docs, client), "LLM + rule-based fallback"
        except Exception as e:
            warn = f"LLM call failed ({type(e).__name__}); used rule-based extraction."
    results = {}
    for f in FIELDS:
        cands = llm.get(f.key) or rx.get(f.key, [])
        distinct = []
        for c in cands:
            if c.value not in distinct:
                distinct.append(c.value)
        status = "missing" if not cands else "conflict" if len(distinct) > 1 else "ok"
        results[f.key] = FieldResult(f.key, f.label, status, cands[0].value if cands else None, cands)
    return results, mode, warn
