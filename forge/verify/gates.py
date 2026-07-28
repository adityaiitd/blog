"""Release gates: what has to be true before anything leaves this tool.

Two levels, and the difference between them is the whole discipline.

A *research report* may contain unverified items. It may not contain
build-ready manufacturing files, and it may not call anything a candidate.

A *simulation-backed candidate package* requires every mandatory gate to pass.
An unverified gate blocks release exactly as a failed one does, because
"we did not check" and "we checked and it was fine" are not the same claim.

Neither level may use the word validated. That requires hardware measured
against the precommitted protocol in :mod:`forge.verify.hardware`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


class GateState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNVERIFIED = "UNVERIFIED"      # not checked; blocks release like a failure
    NOT_APPLICABLE = "N/A"


class ReleaseLevel(str, Enum):
    RESEARCH_REPORT = "research_report"
    CANDIDATE_PACKAGE = "simulation_backed_candidate"
    VALIDATED = "model_validated_prototype"    # hardware only
    PRODUCTION = "production_qualified"        # never granted by this tool


@dataclass
class GateRecord:
    """One gate, its evidence, and why it matters."""

    key: str
    title: str
    state: str
    detail: str
    mandatory: bool = True
    #: Safety-adjacent gates can never be overridden by configuration.
    safety_critical: bool = False
    evidence: Dict[str, Any] = field(default_factory=dict)

    @property
    def blocking(self) -> bool:
        if not self.mandatory or self.state == GateState.NOT_APPLICABLE.value:
            return False
        return self.state != GateState.PASS.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


MANDATORY_GATES = [
    ("requirements", "Requirements and provenance complete", True),
    ("energy_balance", "Analytic energy and loss consistency", False),
    ("material_domain", "Core flux inside the material's fitted domain", False),
    ("geometry_fit", "Windings fit the core window", False),
    ("drc", "Board passes design rule checks", False),
    ("field_2d", "Mesh-converged 2D field results", False),
    ("zvs", "Zero-voltage switching predicted at nominal and corners", False),
    ("isop_sharing", "Cell sharing under component mismatch", True),
    ("faults", "Fault cases within device derating", True),
    ("insulation", "Insulation coordination reviewed", True),
    ("common_mode", "Interwinding capacitance and common-mode current", True),
    ("thermal", "Temperature within limits across the cooling sweep", True),
    ("derating", "Component derating and availability", False),
    ("uncertainty", "Uncertainty budget and benchmark protocol recorded", False),
    ("licensing", "No restricted source material in published output", True),
]


@dataclass
class GateReport:
    gates: List[GateRecord] = field(default_factory=list)
    requirements_hash: str = ""
    protocol_hash: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat(
                timespec="seconds")

    def add(self, record: GateRecord) -> GateRecord:
        self.gates.append(record)
        return record

    def get(self, key: str) -> Optional[GateRecord]:
        return next((g for g in self.gates if g.key == key), None)

    @property
    def blocking(self) -> List[GateRecord]:
        return [g for g in self.gates if g.blocking]

    @property
    def missing(self) -> List[str]:
        present = {g.key for g in self.gates}
        return [k for k, _, _ in MANDATORY_GATES if k not in present]

    @property
    def safety_open(self) -> List[GateRecord]:
        return [g for g in self.gates if g.safety_critical and g.blocking]

    def level(self) -> ReleaseLevel:
        """The highest level this evidence supports. Never above candidate."""
        if self.blocking or self.missing:
            return ReleaseLevel.RESEARCH_REPORT
        return ReleaseLevel.CANDIDATE_PACKAGE

    def may_release_manufacturing_files(self) -> bool:
        return self.level() is ReleaseLevel.CANDIDATE_PACKAGE

    def refusal_reason(self) -> str:
        if self.missing:
            return (
                f"{len(self.missing)} mandatory gate(s) were never evaluated: "
                + ", ".join(self.missing)
            )
        if self.safety_open:
            return (
                "safety-critical gate(s) open: "
                + ", ".join(g.key for g in self.safety_open)
            )
        if self.blocking:
            return (
                f"{len(self.blocking)} gate(s) not passing: "
                + ", ".join(f"{g.key}={g.state}" for g in self.blocking)
            )
        return ""

    def summary(self) -> List[str]:
        lines = []
        for gate in self.gates:
            mark = {
                GateState.PASS.value: "pass",
                GateState.FAIL.value: "FAIL",
                GateState.UNVERIFIED.value: "????",
                GateState.NOT_APPLICABLE.value: "n/a ",
            }[gate.state]
            flag = " !" if gate.safety_critical else "  "
            lines.append(f"  [{mark}]{flag}{gate.title}: {gate.detail}")
        for key in self.missing:
            lines.append(f"  [????]  {key}: never evaluated")
        lines.append("")
        lines.append(f"  release level: {self.level().value}")
        reason = self.refusal_reason()
        if reason:
            lines.append(f"  blocked because {reason}")
        return lines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at,
            "requirements_hash": self.requirements_hash,
            "protocol_hash": self.protocol_hash,
            "gates": [g.to_dict() for g in self.gates],
            "missing": self.missing,
            "release_level": self.level().value,
            "may_release_manufacturing_files":
                self.may_release_manufacturing_files(),
            "refusal_reason": self.refusal_reason(),
        }

    def save(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_dict()
        payload["content_hash"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        path.write_text(json.dumps(payload, indent=1) + "\n")
        return path


class ClaimError(RuntimeError):
    """Raised when an artifact tries to claim more than its evidence supports."""


FORBIDDEN_WITHOUT_HARDWARE = (
    "validated", "qualified", "production-ready", "production ready",
    "proven", "certified",
)


#: Words that negate a claim. "Not production-qualified" is the disclaimer this
#: project requires everywhere, so a naive substring check would reject its own
#: mandated language.
_NEGATIONS = ("not", "never", "no", "without", "cannot", "isn't", "is not")


def _is_negated(lowered: str, position: int, lookback_words: int = 6) -> bool:
    """Was this word negated within its own clause?

    Scoped deliberately tightly. A negation in a previous sentence does not
    negate this one: "Not a prototype. This is a validated design." is a claim,
    not a disclaimer.
    """
    import re

    prefix = lowered[:position]
    # Stop at the nearest clause or sentence boundary.
    boundary = max(prefix.rfind(ch) for ch in ".;:,!?\n")
    clause = prefix[boundary + 1:] if boundary >= 0 else prefix
    words = re.findall(r"[a-z']+", clause)
    return any(word in _NEGATIONS for word in words[-lookback_words:])


def assert_claim_allowed(text: str, report: GateReport,
                         hardware_passed: bool = False) -> None:
    """Refuse language the evidence does not support.

    Called by the report generator on its own output. A document that says
    "validated" without hardware behind it is the single most damaging thing
    this project could produce.

    Negated uses are allowed, because the required disclaimer says "not
    production-qualified" and an assertion that rejects its own disclaimer is
    worse than useless.
    """
    import re

    lowered = text.lower()
    if not hardware_passed:
        for word in FORBIDDEN_WITHOUT_HARDWARE:
            # Word boundaries matter: without them "proven" fires inside
            # "provenance", which is a word this project uses constantly.
            for match in re.finditer(rf"\b{re.escape(word)}\b", lowered):
                if _is_negated(lowered, match.start()):
                    continue
                raise ClaimError(
                    f"the word '{word}' appears in output without negation, "
                    "but no hardware results satisfying the precommitted "
                    "protocol are present. This tool may claim at most a "
                    "simulation-backed preliminary design."
                )

    for phrase in ("production-qualified", "production qualified"):
        for match in re.finditer(rf"\b{re.escape(phrase)}\b", lowered):
            if _is_negated(lowered, match.start()):
                continue
            raise ClaimError(
                "production qualification is never granted by this tool; it "
                "requires independent regulatory, reliability and "
                "manufacturing qualification."
            )
