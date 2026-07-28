"""Insulation coordination basis for the ISOP stack.

The governing creepage and clearance tables live in IEC 60664-1 and
IEC 62368-1, which are sold under licence and may not be reproduced here. So
this module does not pretend to derive certified spacings. What it does is
make the design basis explicit, compute the quantities that are ours to
compute, and mark clearly which numbers a licensed reviewer still has to
confirm.

The point that a per-cell view misses: in an input-series stack, a cell's
*local* switching voltage is not its *working* voltage against the shared
secondary. The top cell's primary floats near the whole bus. Insulation must
be designed for that, and this module refuses to let the local figure be used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ReviewStatus(str, Enum):
    COMPUTED = "computed"              # ours to calculate, and calculated
    NEEDS_LICENSED_REVIEW = "needs_licensed_review"  # from a licensed table
    CONFIRMED = "confirmed"            # a reviewer has signed it off


@dataclass
class InsulationItem:
    key: str
    value: object
    unit: str
    status: str
    basis: str
    notes: str = ""

    @property
    def blocking(self) -> bool:
        return self.status == ReviewStatus.NEEDS_LICENSED_REVIEW.value


@dataclass
class InsulationBasis:
    """The frozen classification a barrier is designed against."""

    standards: List[str]
    equipment_class: str
    overvoltage_category: str
    pollution_degree: int
    material_group: str
    altitude_max_m: float
    insulation_grade: str
    working_voltage_v: float
    items: Dict[str, InsulationItem] = field(default_factory=dict)

    def add(self, item: InsulationItem) -> InsulationItem:
        self.items[item.key] = item
        return item

    def blocking_items(self) -> List[InsulationItem]:
        return [i for i in self.items.values() if i.blocking]

    @property
    def review_complete(self) -> bool:
        return not self.blocking_items()

    def altitude_correction(self, altitude_m: Optional[float] = None) -> float:
        """Clearance multiplier for reduced air density.

        IEC 60664-1 tabulates this; the tabulated points may not be reproduced,
        so this uses the standard barometric scaling as an engineering
        approximation and flags itself as needing confirmation. Below 2000 m no
        correction applies.
        """
        altitude = self.altitude_max_m if altitude_m is None else altitude_m
        if altitude <= 2000.0:
            return 1.0
        # Air density falls roughly exponentially with a scale height near
        # 8.4 km; clearance scales inversely with density.
        import math

        return math.exp((altitude - 2000.0) / 8400.0)

    def summary(self) -> str:
        lines = [
            f"standards: {', '.join(self.standards)}",
            f"equipment class: {self.equipment_class}",
            f"overvoltage category: {self.overvoltage_category}",
            f"pollution degree: {self.pollution_degree}",
            f"material group: {self.material_group}",
            f"insulation grade: {self.insulation_grade}",
            f"working voltage: {self.working_voltage_v:.1f} V",
            f"altitude: {self.altitude_max_m:.0f} m "
            f"(clearance x{self.altitude_correction():.2f})",
        ]
        blocking = self.blocking_items()
        if blocking:
            lines.append(
                f"awaiting licensed review: {', '.join(i.key for i in blocking)}"
            )
        return "\n".join(lines)


def stack_working_voltage(
    bus_voltage_v: float, cell_count: int, cell_index: int
) -> float:
    """Primary-to-secondary working voltage for one cell in an ISOP stack.

    ``cell_index`` is 0 for the cell nearest the return and ``cell_count - 1``
    for the top cell. The secondary of every cell is tied to the common output,
    so a cell's primary sits at the potential of everything below it plus its
    own share.
    """
    if not 0 <= cell_index < cell_count:
        raise ValueError(f"cell_index {cell_index} outside 0..{cell_count - 1}")
    return bus_voltage_v * (cell_index + 1) / cell_count


def worst_case_working_voltage(bus_voltage_v: float, cell_count: int) -> float:
    """The number that actually governs the barrier design."""
    return stack_working_voltage(bus_voltage_v, cell_count, cell_count - 1)


def build_basis(brief, diablo) -> InsulationBasis:
    """Assemble the insulation basis from the frozen requirement sets."""
    bus_transient = diablo.value("diablo.bus_800v_max_transient")
    cells = brief.value("conv.cell_count")
    working = worst_case_working_voltage(bus_transient, cells)

    basis = InsulationBasis(
        standards=list(brief.value("conv.insulation_standard")),
        equipment_class="ICT equipment, IEC 62368-1 scope",
        overvoltage_category=str(brief.value("conv.overvoltage_category")),
        pollution_degree=int(brief.value("conv.pollution_degree")),
        material_group=str(brief.value("conv.material_group")),
        altitude_max_m=float(brief.value("conv.altitude_max")),
        insulation_grade=str(brief.value("conv.insulation_grade")),
        working_voltage_v=working,
    )

    basis.add(InsulationItem(
        key="working_voltage",
        value=working,
        unit="V",
        status=ReviewStatus.COMPUTED.value,
        basis=(
            f"top cell of {cells} in series against the common secondary at "
            f"the worst-case transient bus of {bus_transient:.1f} V"
        ),
        notes=(
            "Not the per-cell switching voltage. Designing this barrier for "
            "the local cell voltage would understate it roughly eightfold."
        ),
    ))

    local = bus_transient / cells
    basis.add(InsulationItem(
        key="local_cell_voltage",
        value=local,
        unit="V",
        status=ReviewStatus.COMPUTED.value,
        basis="bus divided evenly across the stack",
        notes=(
            "Recorded only to document the contrast with the working voltage. "
            "It governs device selection, never the isolation barrier."
        ),
    ))

    for key, req_key, unit in [
        ("clearance", "conv.clearance_reinforced", "mm"),
        ("creepage", "conv.creepage_reinforced", "mm"),
        ("solid_insulation", "conv.solid_insulation_min", "mm"),
        ("hipot", "conv.hipot_test_voltage", "Vrms"),
    ]:
        basis.add(InsulationItem(
            key=key,
            value=brief.value(req_key),
            unit=unit,
            status=ReviewStatus.NEEDS_LICENSED_REVIEW.value,
            basis=(
                "conservative project placeholder; the governing table is in a "
                "licensed IEC document that may not be reproduced here"
            ),
        ))

    basis.add(InsulationItem(
        key="partial_discharge",
        value=bool(brief.value("conv.partial_discharge_required")),
        unit="",
        status=ReviewStatus.NEEDS_LICENSED_REVIEW.value,
        basis=(
            "thin solid insulation under repetitive high dv/dt can pass a "
            "hipot test and still erode by partial discharge"
        ),
    ))

    return basis
