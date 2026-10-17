from datetime import date
from typing import Callable, Optional

from .extract import extract
from .report import followup_email, summary, verdict
from .rules import evaluate


def analyze(docs, client: Optional[Callable[[str], str]] = None, today: Optional[date] = None):
    R, mode, warn = extract(docs, client)
    rules = evaluate(R, today or date.today())
    state, headline = verdict(rules, R)
    return dict(fields=R, rules=rules, state=state, headline=headline, mode=mode, warning=warn,
                summary=summary(R, rules), email=followup_email(R, rules))
