"""Score hardware results against the precommitted acceptance criteria.

The criteria live in ``hardware/acceptance.lock.yaml`` and are hashed. Results
must reference that hash, so a comparison run against a quietly edited set of
thresholds is detectable rather than invisible.

Absent results are not passes. A criterion with no measurement is reported as
unscored and blocks promotion exactly as a failure does.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ACCEPTANCE_PATH = Path(__file__).resolve().parents[1] / "hardware" / "acceptance.lock.yaml"


class HardwareError(RuntimeError):
    pass


@dataclass
class Criterion:
    key: str
    quantity: str
    band: str
    rationale: str
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Measurement:
    """One recorded hardware result."""

    key: str
    value: float
    uncertainty: float
    unit: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    note: str = ""


@dataclass
class Score:
    key: str
    scored: bool
    passed: Optional[bool]
    detail: str


@dataclass
class AcceptanceResult:
    protocol_hash: str
    scores: List[Score] = field(default_factory=list)

    @property
    def unscored(self) -> List[str]:
        return [s.key for s in self.scores if not s.scored]

    @property
    def failed(self) -> List[str]:
        return [s.key for s in self.scores if s.scored and not s.passed]

    @property
    def promoted(self) -> bool:
        """True only if every criterion was measured and every one passed."""
        return bool(self.scores) and not self.unscored and not self.failed

    def claim(self) -> str:
        if self.promoted:
            return "model-validated prototype"
        return "simulation-backed preliminary design"

    def summary(self) -> List[str]:
        lines = [f"acceptance protocol {self.protocol_hash[:16]}"]
        for score in self.scores:
            mark = "pass" if score.passed else ("FAIL" if score.scored else "????")
            lines.append(f"  [{mark}] {score.key}: {score.detail}")
        lines.append("")
        if self.promoted:
            lines.append("  every criterion measured and passing")
        else:
            if self.unscored:
                lines.append(f"  never measured: {', '.join(self.unscored)}")
            if self.failed:
                lines.append(f"  failed: {', '.join(self.failed)}")
        lines.append(f"  permitted claim: {self.claim()}")
        return lines


def load_criteria(path: Path | str = ACCEPTANCE_PATH) -> tuple[List[Criterion], str]:
    path = Path(path)
    raw = path.read_bytes()
    payload = yaml.safe_load(raw)
    criteria = []
    for entry in payload.get("criteria", []):
        known = {"key", "quantity", "band", "rationale"}
        criteria.append(Criterion(
            key=entry["key"], quantity=entry["quantity"], band=entry["band"],
            rationale=entry.get("rationale", ""),
            extra={k: v for k, v in entry.items() if k not in known},
        ))
    return criteria, hashlib.sha256(raw).hexdigest()


def score(
    measurements: Dict[str, Measurement],
    predictions: Dict[str, float],
    path: Path | str = ACCEPTANCE_PATH,
) -> AcceptanceResult:
    """Compare measurements against predictions under the frozen criteria."""
    criteria, protocol_hash = load_criteria(path)
    result = AcceptanceResult(protocol_hash=protocol_hash)

    for criterion in criteria:
        measured = measurements.get(criterion.key)
        predicted = predictions.get(criterion.key)
        if measured is None:
            result.scores.append(Score(
                criterion.key, False, None,
                "no measurement recorded; unscored criteria block promotion",
            ))
            continue
        if predicted is None:
            result.scores.append(Score(
                criterion.key, False, None,
                "measured, but the model made no prediction to compare against",
            ))
            continue

        tolerance = _tolerance_for(criterion, predicted, measured)
        error = abs(measured.value - predicted)
        passed = error <= tolerance
        result.scores.append(Score(
            criterion.key, True, passed,
            f"measured {measured.value:.4g} {measured.unit}, predicted "
            f"{predicted:.4g}, error {error:.4g} against a band of "
            f"{tolerance:.4g}",
        ))
    return result


def _tolerance_for(criterion: Criterion, predicted: float,
                   measured: Measurement) -> float:
    """Interpret the band text into a number.

    The bands are written in prose in the lock file so a human can read them.
    Rather than parse loosely, the handful of forms actually used are matched
    explicitly, and anything unrecognised raises instead of guessing.
    """
    band = criterion.band.lower()
    combined = max(measured.uncertainty, 0.0)

    if "10% relative" in band:
        return max(combined, 0.10 * abs(predicted))
    if "15% relative" in band:
        return max(combined, 0.15 * abs(predicted))
    if "20% relative" in band:
        return 0.20 * abs(predicted)
    if "0.5 percentage points" in band:
        return 0.005
    if "10 k" in band:
        return max(combined, 10.0)
    if "10% of the cell voltage" in band:
        return 0.10 * abs(predicted) if predicted else 10.0
    raise HardwareError(
        f"criterion '{criterion.key}' has band '{criterion.band}', which this "
        "scorer does not know how to interpret. Add it explicitly rather than "
        "letting it be approximated."
    )
