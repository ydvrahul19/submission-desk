from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class Doc:
    name: str
    pages: List[str]  # one string per page / sheet / body

    @property
    def text(self) -> str:
        return "\n".join(self.pages)


@dataclass
class Candidate:
    value: Any
    source: str          # e.g. "SOV.pdf p2"
    quote: str           # verbatim evidence line
    method: str          # "llm" | "regex"


@dataclass
class FieldResult:
    key: str
    label: str
    status: str          # ok | missing | conflict
    value: Optional[Any] = None
    candidates: List[Candidate] = field(default_factory=list)

    @property
    def distinct(self):
        out = []
        for c in self.candidates:
            if c.value not in out:
                out.append(c.value)
        return out


@dataclass
class RuleResult:
    id: str
    name: str
    state: str           # pass | fail | needs_info
    reason: str
    fields: List[str]
