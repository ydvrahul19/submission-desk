"""Optional LLM extraction with evidence verification. The LLM only proposes; code verifies."""
import json
import os
import re
import urllib.request
from typing import Callable, Dict, List, Optional

from .fields import FIELDS, normalize
from .models import Candidate, Doc

PROMPT = """You extract facts from an insurance broker submission. Use ONLY the text below.
For each field return every distinct value you find, each with an exact, verbatim quote copied from the text
and the document name. If a field is not stated, return an empty list. Do not guess or infer.
Return JSON only, shaped like:
{{"fields": {{"<key>": [{{"value": "...", "quote": "...", "doc": "..."}}]}}}}

Fields:
{fields}

Submission:
{docs}
"""


def make_client() -> Optional[Callable[[str], str]]:
    provider = os.getenv("LLM_PROVIDER", "none").lower()
    if provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        import anthropic
        c = anthropic.Anthropic()
        model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")

        def call(prompt: str) -> str:
            r = c.messages.create(model=model, max_tokens=2000, temperature=0,
                                  messages=[{"role": "user", "content": prompt}])
            return "".join(b.text for b in r.content if b.type == "text")
        return call
    if provider == "ollama":
        url, model = os.getenv("OLLAMA_URL", "http://localhost:11434"), os.getenv("OLLAMA_MODEL", "llama3.2")

        def call(prompt: str) -> str:
            body = json.dumps({"model": model, "prompt": prompt, "stream": False, "format": "json"}).encode()
            req = urllib.request.Request(url + "/api/generate", body, {"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req, timeout=120))["response"]
        return call
    return None


def _squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def extract_llm(docs: List[Doc], client: Callable[[str], str]) -> Dict[str, List[Candidate]]:
    fields = "\n".join(f"- {f.key}: {f.hint}" for f in FIELDS)
    body = "\n\n".join(f"=== {d.name} ===\n" + "\n".join(f"[page {i+1}]\n{p}" for i, p in enumerate(d.pages)) for d in docs)
    raw = client(PROMPT.format(fields=fields, docs=body))
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    data = json.loads(raw).get("fields", {})
    by_name = {d.name: d for d in docs}
    out: Dict[str, List[Candidate]] = {}
    for f in FIELDS:
        for item in data.get(f.key, []) or []:
            quote, dname = str(item.get("quote", "")), str(item.get("doc", ""))
            doc = by_name.get(dname)
            haystack = _squash(doc.text) if doc else _squash(" ".join(d.text for d in docs))
            value = normalize(f.type, item.get("value"))
            # Evidence must literally exist in the source; otherwise discard (hallucination guard).
            if value is None or not quote or _squash(quote) not in haystack:
                continue
            page = ""
            if doc and len(doc.pages) > 1:
                for i, p in enumerate(doc.pages):
                    if _squash(quote) in _squash(p):
                        page = f" p{i+1}"
                        break
            out.setdefault(f.key, []).append(Candidate(value, dname + page, quote.strip(), "llm"))
    return out
