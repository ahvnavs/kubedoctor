"""Small domain objects shared by collectors, rules, and renderers."""

from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Evidence:
    source: str
    detail: str


@dataclass(frozen=True, slots=True)
class Diagnosis:
    code: str
    title: str
    summary: str
    severity: Severity
    resource: str
    fix_command: str
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)

