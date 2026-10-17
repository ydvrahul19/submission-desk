"""Field specification. Edit here to match a different field list."""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    type: str     # str | money | int | date | yesno
    pattern: str  # regex with one capture group, used by the rule-based extractor
    hint: str = ""


FIELDS = [
    Field("insured", "Insured", "str", r"(?:named insured|insured|applicant)\s*[:\-]\s*(.+)", "legal name of the insured"),
    Field("ops", "Operations", "str", r"(?:operations|occupancy|business type)\s*[:\-]\s*(.+)", "what the business does"),
    Field("tiv", "Total insured value", "money", r"(?:total insured value|tiv)\s*[:\-]?\s*\$?\s*([\d,.]+\s*(?:m\b|million)?)", "total insured value in dollars"),
    Field("year", "Year built", "int", r"(?:year built|built in|construction year)\s*[:\-]?\s*(\d{4})", "year the building was built"),
    Field("spr", "Sprinklers", "yesno", r"sprinkler\w*(?:\s*system)?\s*[:\-]\s*(yes|no|none|full|partial)", "yes/no: is the building sprinklered"),
    Field("loss", "Losses, last 5 years", "int", r"(?:losses|claims)[^:\n]*[:\-]\s*(\d+|none|zero|nil)", "number of losses/claims in the last 5 years"),
    Field("eff", "Effective date", "date", r"effective(?:\s*date)?\s*[:\-]\s*([\w ,/\-]+)", "requested policy effective date, YYYY-MM-DD"),
]
BY_KEY = {f.key: f for f in FIELDS}

DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%d %B %Y", "%b %d, %Y"]


def normalize(ftype: str, raw: Any) -> Optional[Any]:
    """Turn raw text into a comparable value. Returns None if unparseable."""
    if raw is None:
        return None
    s = str(raw).strip().rstrip(".;")
    if not s:
        return None
    try:
        if ftype == "money":
            m = re.match(r"\$?\s*([\d,]*\.?\d+)\s*(m\b|million)?", s, re.I)
            n = float(m.group(1).replace(",", ""))
            return int(round(n * 1e6)) if m.group(2) else int(round(n))
        if ftype == "int":
            return 0 if s.lower() in ("none", "zero", "nil") else int(re.search(r"\d+", s).group())
        if ftype == "yesno":
            return "no" if s.lower() in ("no", "none") else "yes" if re.match(r"yes|full|partial|true", s, re.I) else None
        if ftype == "date":
            for fmt in DATE_FORMATS:
                try:
                    return datetime.strptime(s, fmt).date().isoformat()
                except ValueError:
                    pass
            return None
    except (AttributeError, ValueError):
        return None
    return s


def display(f: Field, v: Any) -> str:
    if v is None:
        return "-"
    return f"${v:,}" if f.type == "money" else str(v)
