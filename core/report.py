from typing import Dict, List, Tuple

from .fields import BY_KEY, display
from .models import FieldResult, RuleResult


def gaps(R: Dict[str, FieldResult], rules: List[RuleResult]) -> List[FieldResult]:
    """Fields worth chasing: any conflict, plus missing fields that a rule actually needed."""
    needed = {k for r in rules if r.state == "needs_info" for k in r.fields}
    return [x for x in R.values() if x.status == "conflict" or (x.status == "missing" and x.key in needed)]


def verdict(rules: List[RuleResult], R: Dict[str, FieldResult]) -> Tuple[str, str]:
    fails = [r for r in rules if r.state == "fail"]
    if fails:
        return "fail", f"Outside appetite: {len(fails)} rule(s) failed."
    if any(r.state == "needs_info" for r in rules) or gaps(R, rules):
        return "hold", "Hold for information: no rule failed, but some checks cannot finish."
    return "pass", "Ready to quote: all rules pass with consistent data."


def summary(R: Dict[str, FieldResult], rules: List[RuleResult]) -> str:
    n = lambda s: sum(r.state == s for r in rules)
    name = R["insured"].value or "Unknown insured"
    lines = [f"{name}: {R['ops'].value or 'operations not stated'}.",
             f"Rules: {n('pass')} pass, {n('fail')} fail, {n('needs_info')} need information."]
    lines += [f"FAIL {r.id} - {r.reason}" for r in rules if r.state == "fail"]
    lines += [f"{'MISSING' if x.status == 'missing' else 'CONFLICT'} - {x.label}" for x in gaps(R, rules)]
    return "\n".join("- " + l for l in lines)


def followup_email(R: Dict[str, FieldResult], rules: List[RuleResult]) -> str:
    name = R["insured"].value or "your client"
    asks = []
    for x in gaps(R, rules):
        if x.status == "missing":
            asks.append(f"- {x.label}: we could not find this in the documents. Please provide it.")
        elif x.status == "conflict":
            seen, parts = set(), []
            for c in x.candidates:
                if c.value not in seen:
                    seen.add(c.value)
                    parts.append(f"{display(BY_KEY[x.key], c.value)} ({c.source})")
            asks.append(f"- {x.label}: the documents disagree - {' and '.join(parts)}. Which is correct?")
    if not asks:
        return f"Subject: Re: {name} - submission received\n\nHi,\n\nThank you for sending {name}. We have what we need and will come back with a decision shortly.\n\nKind regards,\nUnderwriting team"
    return (f"Subject: Re: {name} - information needed to proceed\n\nHi,\n\nThank you for sending {name}. "
            "To finish our review, could you help with the following?\n\n" + "\n".join(asks) +
            "\n\nKind regards,\nUnderwriting team")
