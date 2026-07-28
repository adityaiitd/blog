"""Manual gates: what happens when a source will not open itself.

When a publisher puts a managed challenge in front of a document, FORGE stops
and records why. The requirement that needed the document is marked
unavailable, and the pipeline continues with an explicit hole rather than an
invented number. A human can later satisfy the gate by supplying the file
through a licensed route and recording it in the evidence register.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class GateReason(str, Enum):
    MANAGED_CHALLENGE = "managed_challenge"
    CAPTCHA = "captcha"
    LOGIN_REQUIRED = "login_required"
    PAYWALL = "paywall"
    LICENSED_STANDARD = "licensed_standard"
    WITHDRAWN = "withdrawn"
    TRANSPORT_FAILURE = "transport_failure"


class GateState(str, Enum):
    OPEN = "open"           # still blocking
    SATISFIED = "satisfied"  # a human supplied the material lawfully
    WAIVED = "waived"        # requirement dropped, with justification


@dataclass
class ManualGate:
    key: str
    url: str
    reason: str
    what_it_blocks: str
    state: str = GateState.OPEN.value
    opened_at: str = ""
    resolved_at: str = ""
    resolution: str = ""
    alternate_source: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.opened_at:
            self.opened_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    @property
    def blocking(self) -> bool:
        return self.state == GateState.OPEN.value

    def satisfy(self, resolution: str, alternate_source: str = "") -> None:
        self.state = GateState.SATISFIED.value
        self.resolution = resolution
        self.alternate_source = alternate_source
        self.resolved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def waive(self, justification: str) -> None:
        self.state = GateState.WAIVED.value
        self.resolution = justification
        self.resolved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def describe(self) -> str:
        return (
            f"[{self.state}] {self.key}: {self.reason} at {self.url} — blocks "
            f"{self.what_it_blocks}"
        )


class ManualGateLog:
    """Persistent record of every source that refused to open."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.gates: Dict[str, ManualGate] = {}
        if self.path.exists():
            for row in json.loads(self.path.read_text()):
                gate = ManualGate(**row)
                self.gates[gate.key] = gate

    def record(self, gate: ManualGate) -> ManualGate:
        existing = self.gates.get(gate.key)
        if existing and not existing.blocking:
            return existing
        self.gates[gate.key] = gate
        self.save()
        return gate

    def get(self, key: str) -> Optional[ManualGate]:
        return self.gates.get(key)

    def blocking(self) -> List[ManualGate]:
        return [g for g in self.gates.values() if g.blocking]

    def save(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([asdict(g) for g in self.gates.values()], indent=2) + "\n"
        )
        return self.path

    def summary(self) -> Dict[str, object]:
        by_reason: Dict[str, int] = {}
        for gate in self.gates.values():
            if gate.blocking:
                by_reason[gate.reason] = by_reason.get(gate.reason, 0) + 1
        return {
            "total": len(self.gates),
            "blocking": len(self.blocking()),
            "by_reason": by_reason,
            "blocked_keys": [g.key for g in self.blocking()],
        }
