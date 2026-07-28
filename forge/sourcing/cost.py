"""Turn quotes into a cost model, showing the holes rather than filling them.

A bill of materials with four of eight lines priced is not a cost. It is a
partial cost with a stated coverage, and the difference matters to anyone
deciding whether to build the thing. Every figure here reports how much of the
bill it actually covers, and unpriced lines are listed by name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .harvest import PartQuote

#: Silicon and magnetics are only part of a converter. These are the standard
#: adders a buyer applies on top of a component bill, expressed as fractions of
#: component cost. They are industry rules of thumb, not quotes, and are
#: labelled as such wherever they are shown.
DEFAULT_ADDERS = {
    "bare_pcb": 0.0,        # priced separately, it is a real quotable item
    "assembly": 0.18,
    "test_and_yield": 0.07,
    "scrap_and_rework": 0.03,
}


@dataclass
class PcbEstimate:
    """The transformer board is a purchased item too, and a costly one.

    A 14-layer board with heavy copper is not a commodity two-layer part. Cost
    scales with layer count, copper weight and area. This is a parametric
    estimate rather than a quote, and is flagged as such.
    """

    layers: int
    copper_oz: float
    area_mm2: float
    #: Rough industry scaling: cost per square decimetre per layer pair.
    usd_per_dm2_per_layer_pair: float = 1.15
    heavy_copper_multiplier_per_oz: float = 0.18
    #: Per-board floor, driven by layer count rather than area.
    #:
    #: A small board does not get proportionally cheap. Every board still needs
    #: its lamination cycles, drill hits, registration between layer pairs and
    #: electrical test, and those costs scale with layer count and barely with
    #: area. Without this floor, a 530 mm2 twelve-layer board prices out around
    #: 25 cents, which is off by an order of magnitude.
    usd_floor_per_layer: float = 0.45

    def unit_cost_usd(self, volume: int = 1000) -> float:
        area_dm2 = self.area_mm2 / 10000.0
        pairs = max(self.layers / 2.0, 1.0)
        base = area_dm2 * pairs * self.usd_per_dm2_per_layer_pair
        heavy = 1.0 + self.heavy_copper_multiplier_per_oz * max(
            self.copper_oz - 1.0, 0.0
        )
        floor = self.usd_floor_per_layer * self.layers * heavy
        # Volume discount flattens out around a few thousand.
        volume_factor = 1.0 if volume < 100 else (0.72 if volume < 1000 else 0.58)
        return max(base * heavy, floor) * volume_factor

    @property
    def is_estimate(self) -> bool:
        return True

    def describe(self) -> str:
        return (
            f"{self.layers}-layer, {self.copper_oz:g} oz copper, "
            f"{self.area_mm2:.0f} mm2"
        )


@dataclass
class CostLine:
    mpn: str
    role: str
    qty_per_converter: int
    unit_usd: Optional[float]
    extended_usd: Optional[float]
    status: str
    note: str = ""

    @property
    def priced(self) -> bool:
        return self.extended_usd is not None


@dataclass
class CostModel:
    volume: int
    cells: int
    lines: List[CostLine] = field(default_factory=list)
    pcb: Optional[PcbEstimate] = None
    pcb_cost_usd: Optional[float] = None
    adders: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_ADDERS))
    output_kw: float = 6.0

    @property
    def priced_lines(self) -> List[CostLine]:
        return [line for line in self.lines if line.priced]

    @property
    def unpriced_lines(self) -> List[CostLine]:
        return [line for line in self.lines if not line.priced]

    @property
    def component_cost_usd(self) -> float:
        return sum(line.extended_usd or 0.0 for line in self.priced_lines)

    @property
    def coverage(self) -> float:
        """Fraction of BOM lines that carry a real price."""
        if not self.lines:
            return 0.0
        return len(self.priced_lines) / len(self.lines)

    @property
    def adder_cost_usd(self) -> float:
        base = self.component_cost_usd + (self.pcb_cost_usd or 0.0)
        return base * sum(self.adders.values())

    @property
    def total_usd(self) -> float:
        return (
            self.component_cost_usd
            + (self.pcb_cost_usd or 0.0)
            + self.adder_cost_usd
        )

    @property
    def usd_per_kw(self) -> float:
        return self.total_usd / self.output_kw if self.output_kw else 0.0

    def summary(self) -> Dict[str, object]:
        return {
            "volume": self.volume,
            "component_cost_usd": self.component_cost_usd,
            "pcb_cost_usd": self.pcb_cost_usd,
            "adder_cost_usd": self.adder_cost_usd,
            "total_usd": self.total_usd,
            "usd_per_kw": self.usd_per_kw,
            "coverage": self.coverage,
            "priced": len(self.priced_lines),
            "unpriced": [line.mpn for line in self.unpriced_lines],
            "is_partial": self.coverage < 1.0,
            "caveat": (
                "Partial: "
                f"{len(self.unpriced_lines)} of {len(self.lines)} lines carry no "
                "retrievable price, so the total is a floor, not an estimate."
            ) if self.coverage < 1.0 else "All lines priced.",
        }


def build_cost_model(
    quotes: Sequence[PartQuote],
    volume: int = 1000,
    cells: int = 8,
    pcb: Optional[PcbEstimate] = None,
    output_kw: float = 6.0,
    shared_per_converter: Optional[Dict[str, int]] = None,
) -> CostModel:
    """Assemble a converter-level cost from per-part quotes.

    ``shared_per_converter`` names parts that appear once per converter rather
    than once per cell, such as the controller and the digital isolators.
    """
    shared = shared_per_converter or {
        "ISO7740": 2, "DSPIC33CK256MP605": 1,
    }
    model = CostModel(volume=volume, cells=cells, pcb=pcb, output_kw=output_kw)

    for quote in quotes:
        if quote.mpn in shared:
            qty = shared[quote.mpn]
        else:
            qty = quote.qty_per_cell * cells
        unit = quote.price_at(max(volume * qty, 1))
        extended = unit * qty if unit is not None else None
        model.lines.append(CostLine(
            mpn=quote.mpn, role=quote.role, qty_per_converter=qty,
            unit_usd=unit, extended_usd=extended, status=quote.status,
            note=quote.note,
        ))

    if pcb is not None:
        # One transformer board per cell.
        model.pcb_cost_usd = pcb.unit_cost_usd(volume) * cells
    return model


@dataclass
class SupplyRisk:
    part: str
    concern: str
    severity: str      # low | medium | high
    mitigation: str


def supply_risks(quotes: Sequence[PartQuote]) -> List[SupplyRisk]:
    """Risks visible from the quotes themselves, plus structural ones."""
    risks: List[SupplyRisk] = []
    for quote in quotes:
        if quote.status == "blocked":
            risks.append(SupplyRisk(
                quote.mpn,
                "No machine-readable price. The vendor blocks automated access, "
                "so cost cannot be tracked without a distributor API key.",
                "low",
                "Obtain a Mouser, Digi-Key or TI API key and re-run the harvest.",
            ))
        elif quote.status == "unavailable":
            risks.append(SupplyRisk(
                quote.mpn,
                "No published price ladder found, so this line is missing from "
                "the cost model entirely.",
                "medium",
                "Request a direct quote, or price an equivalent second source.",
            ))
        if quote.stock is not None and quote.stock < 5000:
            risks.append(SupplyRisk(
                quote.mpn,
                f"Only {quote.stock:,} units in stock at the source that "
                "published a price. A 6 kW converter needs "
                f"{quote.qty_per_cell * 8} per unit.",
                "high" if quote.stock < 1000 else "medium",
                "Qualify a second source, or place a scheduled order early.",
            ))
    return risks


STRUCTURAL_RISKS: List[SupplyRisk] = [
    SupplyRisk(
        "GaN transistors",
        "The primary and secondary switches are sole-sourced to one vendor. "
        "GaN parts are not drop-in interchangeable between manufacturers: "
        "footprint, gate drive requirement and output charge all differ.",
        "high",
        "Qualify a second GaN vendor early, accepting a board respin, or "
        "design the footprint to accept two suppliers from the start.",
    ),
    SupplyRisk(
        "Planar ferrite core",
        "Core geometry is standardised across vendors but the material is not. "
        "Substituting a nominally equivalent ferrite changes the loss and the "
        "temperature at which loss is minimised.",
        "medium",
        "Qualify materials from two vendors against measured loss, not "
        "datasheet equivalence.",
    ),
    SupplyRisk(
        "14-layer heavy-copper PCB",
        "The transformer is the board. Layer count, copper weight and layer "
        "registration are all tighter than commodity PCB work, which narrows "
        "the supplier list and makes cost sensitive to yield.",
        "medium",
        "Dual-source the fabricator and hold registration tolerance as a "
        "specified requirement, since leakage inductance depends on it.",
    ),
]
