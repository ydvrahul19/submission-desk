"""Deterministic rules. NOTE: these five are placeholders - replace with the rules from the assignment brief.
Each rule returns pass / fail / needs_info. Missing or conflicting inputs always give needs_info, never a guess."""
from datetime import date
from typing import Dict, List

from .fields import BY_KEY, display
from .models import FieldResult, RuleResult

TIV_LIMIT = 10_000_000
PROHIBITED = ("firework", "pyrotech", "explosive", "cannabis", "asbestos")
MAX_LOSSES = 2
MIN_YEAR = 1980
MIN_LEAD_DAYS = 14


def _gate(R: Dict[str, FieldResult], key: str):
    r = R[key]
    if r.status == "missing":
        return RuleResult("", "", "needs_info", f"{r.label} was not found in the submission.", [key])
    if r.status == "conflict":
        vals = " vs ".join(display(BY_KEY[key], v) for v in r.distinct)
        return RuleResult("", "", "needs_info", f"{r.label} conflicts between documents: {vals}.", [key])
    return None


def evaluate(R: Dict[str, FieldResult], today: date) -> List[RuleResult]:
    out = []

    def add(id_, name, keys, fn):
        for k in keys:
            g = _gate(R, k)
            if g:
                g.id, g.name, g.fields = id_, name, keys
                out.append(g)
                return
        state, why = fn()
        out.append(RuleResult(id_, name, state, why, keys))

    add("R1", f"Total insured value up to ${TIV_LIMIT:,}", ["tiv"], lambda: (
        ("pass", f"${R['tiv'].value:,} is within the limit.") if R["tiv"].value <= TIV_LIMIT
        else ("fail", f"${R['tiv'].value:,} exceeds ${TIV_LIMIT:,}.")))
    add("R2", "Operations not prohibited", ["ops"], lambda: (
        ("fail", f"'{R['ops'].value}' is a prohibited class.") if any(p in R["ops"].value.lower() for p in PROHIBITED)
        else ("pass", f"'{R['ops'].value}' is an accepted class.")))
    add("R3", f"At most {MAX_LOSSES} losses in 5 years", ["loss"], lambda: (
        ("pass", f"{R['loss'].value} reported.") if R["loss"].value <= MAX_LOSSES
        else ("fail", f"{R['loss'].value} reported, limit is {MAX_LOSSES}.")))

    name4 = f"Built {MIN_YEAR} or later, or sprinklered"
    g = _gate(R, "year")  # sprinkler data is only needed when the building is old
    if g:
        g.id, g.name, g.fields = "R4", name4, ["year", "spr"]
        out.append(g)
    elif R["year"].value >= MIN_YEAR:
        out.append(RuleResult("R4", name4, "pass", f"Built {R['year'].value}.", ["year"]))
    else:
        add("R4", name4, ["spr"], lambda: (
            ("pass", f"Built {R['year'].value}, but sprinklered.") if R["spr"].value == "yes"
            else ("fail", f"Built {R['year'].value} with no sprinklers.")))

    def r5():
        days = (date.fromisoformat(R["eff"].value) - today).days
        return ("pass", f"Starts in {days} days.") if days >= MIN_LEAD_DAYS else ("fail", f"Starts in {days} days, minimum is {MIN_LEAD_DAYS}.")
    add("R5", f"Effective date at least {MIN_LEAD_DAYS} days out", ["eff"], r5)
    return out
