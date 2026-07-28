"""Load, validate and freeze the requirement set.

``requirements.lock.yaml`` is the gate between "we are still deciding what to
build" and "we are optimising". It is refused if any mandatory category is
unpopulated, if an assumed numeric value has no sensitivity range, or if a
sourced value cites a document that is not in the evidence register.

The lock carries a content hash. Every later artifact records that hash, so a
result can always be traced to the exact requirements it was produced under.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

from ..evidence.register import EvidenceRegister
from .schema import (
    MANDATORY_CATEGORIES,
    Category,
    Provenance,
    Requirement,
    RequirementSet,
    Scope,
)

HERE = Path(__file__).resolve().parent


class RequirementError(RuntimeError):
    pass


def load_set(path: Path | str) -> RequirementSet:
    """Read one requirement YAML into a scoped RequirementSet."""
    path = Path(path)
    data = yaml.safe_load(path.read_text())
    scope = Scope(data["scope"])
    rset = RequirementSet(
        scope=scope,
        title=data.get("title", path.stem),
        description=data.get("description", ""),
    )
    for entry in data.get("requirements", []):
        payload = dict(entry)
        payload.setdefault("scope", scope.value)
        try:
            rset.add(Requirement(**payload))
        except TypeError as exc:
            raise RequirementError(
                f"{path.name}: requirement '{payload.get('key')}' has an "
                f"unexpected field: {exc}"
            ) from exc
        except ValueError as exc:
            raise RequirementError(f"{path.name}: {exc}") from exc
    return rset


@dataclass
class ValidationReport:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def describe(self) -> str:
        lines: List[str] = []
        for err in self.errors:
            lines.append(f"  ERROR   {err}")
        for warn in self.warnings:
            lines.append(f"  warning {warn}")
        return "\n".join(lines) if lines else "  (clean)"


def validate(
    diablo: RequirementSet,
    converter: RequirementSet,
    register: Optional[EvidenceRegister] = None,
) -> ValidationReport:
    report = ValidationReport()

    if diablo.scope is not Scope.DIABLO_INTERFACE:
        report.errors.append("the interface file does not declare diablo scope")
    if converter.scope is not Scope.CONVERTER_BRIEF:
        report.errors.append("the brief file does not declare converter scope")

    missing = converter.missing_categories(MANDATORY_CATEGORIES)
    for category in missing:
        report.errors.append(
            f"converter brief has no requirement in mandatory category "
            f"'{category}'"
        )

    for rset in (diablo, converter):
        for key in rset.assumptions_without_sweeps():
            report.errors.append(
                f"'{key}' is an assumed numeric value with no sensitivity "
                "range; assumed numbers must be swept, not asserted"
            )

    if register is not None:
        sources = {s.key: s for s in register.sources()}
        for rset in (diablo, converter):
            for req in rset.all():
                if req.provenance != Provenance.SOURCED.value:
                    continue
                source = sources.get(req.source_key or "")
                if source is None:
                    report.errors.append(
                        f"'{req.key}' cites source '{req.source_key}' "
                        "which is not in the evidence register"
                    )
                    continue
                # A citation the pipeline cannot currently re-fetch is still a
                # citation, but the report has to say so rather than imply the
                # value was verified this run.
                if source.status in ("blocked", "unavailable"):
                    report.warnings.append(
                        f"'{req.key}' cites '{req.source_key}' whose status is "
                        f"'{source.status}'; the value was read from an earlier "
                        "retrieval and cannot be re-verified automatically "
                        "until the manual gate is satisfied"
                    )

    # A derived requirement should explain its arithmetic, otherwise it is an
    # assumption wearing a better label.
    for rset in (diablo, converter):
        for req in rset.all():
            if req.provenance == Provenance.DERIVED.value and len(
                req.rationale.strip()
            ) < 20:
                report.warnings.append(
                    f"'{req.key}' is derived but barely explains how"
                )

    # The specific confusion this project exists to avoid.
    for req in converter.all():
        if req.provenance == Provenance.SOURCED.value and (
            req.source_key or ""
        ).startswith("ocp_diablo"):
            report.errors.append(
                f"'{req.key}' sources a converter requirement directly from "
                "Diablo. Diablo specifies the rack interface, not this "
                "converter. Route it through a derived requirement that shows "
                "its arithmetic."
            )

    insulation = converter.by_category(Category.INSULATION)
    if insulation and not any(
        r.key.endswith("working_voltage") for r in insulation
    ):
        report.errors.append(
            "insulation category defines no working voltage; creepage and "
            "clearance cannot be justified without one"
        )

    return report


@dataclass
class RequirementLock:
    diablo: RequirementSet
    converter: RequirementSet
    report: ValidationReport
    content_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forge_requirements_lock": 1,
            "diablo_interface": self.diablo.to_dict(),
            "converter_brief": self.converter.to_dict(),
            "validation": {
                "ok": self.report.ok,
                "errors": self.report.errors,
                "warnings": self.report.warnings,
            },
        }

    def compute_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()

    def value(self, key: str) -> Any:
        """Look a requirement up in whichever scope defines it."""
        if key in self.converter:
            return self.converter.value(key)
        return self.diablo.value(key)

    def save(self, path: Path | str) -> Path:
        if not self.report.ok:
            raise RequirementError(
                "refusing to write a requirements lock while validation "
                f"fails:\n{self.report.describe()}"
            )
        self.content_hash = self.compute_hash()
        payload = self.to_dict()
        payload["content_hash"] = self.content_hash
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(payload, sort_keys=False, width=100))
        return path


def build(
    diablo_path: Path | str = HERE / "diablo_interface.yaml",
    converter_path: Path | str = HERE / "converter_brief.yaml",
    register: Optional[EvidenceRegister] = None,
) -> RequirementLock:
    diablo = load_set(diablo_path)
    converter = load_set(converter_path)
    report = validate(diablo, converter, register)
    return RequirementLock(diablo=diablo, converter=converter, report=report)


def summarise(lock: RequirementLock) -> str:
    lines: List[str] = []
    for rset in (lock.diablo, lock.converter):
        counts = rset.by_provenance()
        lines.append(
            f"{rset.scope.value}: {len(rset)} requirements "
            f"({counts.get('sourced', 0)} sourced, "
            f"{counts.get('derived', 0)} derived, "
            f"{counts.get('assumed', 0)} assumed)"
        )
    missing = lock.converter.missing_categories()
    lines.append(
        "mandatory categories: "
        + (
            "all covered"
            if not missing
            else f"{len(missing)} missing -> {', '.join(missing)}"
        )
    )
    return "\n".join(lines)
