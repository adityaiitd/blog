"""Requirement objects and the categories a design must cover before optimising.

Two rules give this module its shape.

First, a requirement always carries its provenance class. A number read out of
a specification and a number somebody chose are both legitimate inputs, but
they are not the same kind of thing, and the report has to show which is which.

Second, the Diablo rack interface and the downstream converter brief are kept
in separate objects that never merge silently. Diablo says what arrives at the
rack; it does not specify a 12.5 V converter, a power level, or a tank. Reading
a downstream requirement out of Diablo is the specific mistake this structure
exists to prevent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


class Provenance(str, Enum):
    SOURCED = "sourced"   # read from a cited document
    DERIVED = "derived"   # computed from other requirements
    ASSUMED = "assumed"   # a project decision requiring review


class Scope(str, Enum):
    """Which specification a requirement belongs to. Never mixed."""

    DIABLO_INTERFACE = "diablo_interface"
    CONVERTER_BRIEF = "converter_brief"


class Category(str, Enum):
    """The mandatory coverage list. Optimisation is blocked until all appear."""

    INPUT_ARCHITECTURE = "input_architecture"
    OUTPUT_REGULATION = "output_regulation"
    POWER_AND_LOAD = "power_and_load"
    SEQUENCING = "sequencing"
    FAULTS = "faults"
    ISOP_MISMATCH = "isop_mismatch"
    COOLING_BOUNDARY = "cooling_boundary"
    EFFICIENCY_BOUNDARY = "efficiency_boundary"
    MANUFACTURING = "manufacturing"
    INSULATION = "insulation"
    EMI_COMMON_MODE = "emi_common_mode"
    DERATING_LIFETIME = "derating_lifetime"


#: Categories that must be populated in the converter brief before the
#: optimiser will run. The Diablo object is an interface description and is
#: not expected to cover downstream categories.
MANDATORY_CATEGORIES = tuple(Category)


@dataclass
class Requirement:
    key: str
    value: Any
    unit: str
    scope: str
    category: str
    provenance: str
    rationale: str
    source_key: Optional[str] = None
    locator: str = ""
    #: Range to sweep when the value is assumed rather than known.
    sensitivity: Optional[Sequence[float]] = None
    tolerance: Optional[Sequence[float]] = None
    #: Set for values that are classifications rather than continuous
    #: quantities. Pollution degree 2 has no meaningful value of 2.3.
    discrete: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if self.provenance == Provenance.SOURCED.value and not self.source_key:
            raise ValueError(
                f"requirement '{self.key}' is SOURCED but cites no document"
            )
        if self.provenance == Provenance.ASSUMED.value and not self.rationale:
            raise ValueError(
                f"requirement '{self.key}' is ASSUMED and must explain why"
            )

    @property
    def needs_sensitivity_sweep(self) -> bool:
        """An assumed number without a sweep range is an unquantified guess.

        Booleans and declared classifications are exempt: a pollution degree
        cannot be swept continuously, and sweeping a flag is meaningless.
        """
        if self.provenance != Provenance.ASSUMED.value:
            return False
        if self.discrete or isinstance(self.value, bool):
            return False
        if not isinstance(self.value, (int, float)):
            return False
        return self.sensitivity is None

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        return {k: v for k, v in out.items() if v not in (None, "", [])}


class RequirementSet:
    """A collection of requirements confined to one scope."""

    def __init__(self, scope: Scope, title: str, description: str = ""):
        self.scope = scope
        self.title = title
        self.description = description
        self._items: Dict[str, Requirement] = {}

    def add(self, requirement: Requirement) -> Requirement:
        if requirement.scope != self.scope.value:
            raise ValueError(
                f"requirement '{requirement.key}' has scope "
                f"'{requirement.scope}' but was added to '{self.scope.value}'. "
                "Rack-interface and converter requirements are kept apart on "
                "purpose."
            )
        if requirement.key in self._items:
            raise ValueError(f"duplicate requirement key '{requirement.key}'")
        self._items[requirement.key] = requirement
        return requirement

    def get(self, key: str) -> Requirement:
        if key not in self._items:
            raise KeyError(
                f"requirement '{key}' is not defined in {self.scope.value}"
            )
        return self._items[key]

    def value(self, key: str) -> Any:
        return self.get(key).value

    def __contains__(self, key: str) -> bool:
        return key in self._items

    def __len__(self) -> int:
        return len(self._items)

    def all(self) -> List[Requirement]:
        return list(self._items.values())

    def by_category(self, category: Category) -> List[Requirement]:
        return [r for r in self._items.values() if r.category == category.value]

    def categories_covered(self) -> set[str]:
        return {r.category for r in self._items.values()}

    def missing_categories(
        self, required: Sequence[Category] = MANDATORY_CATEGORIES
    ) -> List[str]:
        covered = self.categories_covered()
        return [c.value for c in required if c.value not in covered]

    def by_provenance(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for req in self._items.values():
            counts[req.provenance] = counts.get(req.provenance, 0) + 1
        return counts

    def assumptions_without_sweeps(self) -> List[str]:
        return [r.key for r in self._items.values() if r.needs_sensitivity_sweep]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope.value,
            "title": self.title,
            "description": self.description,
            "provenance_counts": self.by_provenance(),
            "requirements": [r.to_dict() for r in self._items.values()],
        }
