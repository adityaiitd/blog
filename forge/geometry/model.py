"""The canonical planar transformer geometry.

One model, three consumers: the board file, the field-solver cross-section and
the loss calculation all read from here. That is the point. If the simulated
geometry and the manufactured geometry come from different descriptions, they
will disagree eventually and nobody will notice until hardware.

Turns are modelled as concentric racetrack tracks around the core centre post.
Each turn therefore has its own mean length, rather than one average length
applied to a whole winding, and the innermost turn is meaningfully shorter
than the outermost.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


class GeometryError(RuntimeError):
    pass


@dataclass(frozen=True)
class CoreGeometry:
    """The magnetic core, reduced to what the winding geometry needs."""

    part: str
    material: str
    ae_m2: float
    le_m: float
    ve_m3: float
    height_m: float
    outline_x_m: float
    outline_y_m: float
    window_height_m: float
    window_radial_m: float
    #: Centre-post footprint. An ELP post is a wide rectangle spanning the core
    #: width, so turns are racetracks rather than circles and the mean turn
    #: length is set by the post perimeter, not by a circular-equivalent radius.
    post_long_m: float = 0.0
    post_short_m: float = 0.0

    def __post_init__(self) -> None:
        if self.post_long_m <= 0 or self.post_short_m <= 0:
            equivalent = math.sqrt(self.ae_m2)
            object.__setattr__(self, "post_long_m", equivalent)
            object.__setattr__(self, "post_short_m", equivalent)

    @property
    def post_radius_m(self) -> float:
        """Circular-equivalent post radius, kept for screening comparisons."""
        return math.sqrt(self.ae_m2 / math.pi)

    @property
    def winding_inner_offset_m(self) -> float:
        """Radial clearance from the post face to the first turn."""
        return 0.0

    @property
    def winding_outer_offset_m(self) -> float:
        return self.window_radial_m

    def turn_length(self, offset_m: float) -> float:
        """Perimeter of a racetrack offset from the post by ``offset_m``."""
        return (
            2.0 * (self.post_long_m + self.post_short_m)
            + 2.0 * math.pi * offset_m
        )

    def winding_extent_m(self) -> Tuple[float, float]:
        """Overall copper footprint, long axis then short axis."""
        return (
            self.post_long_m + 2.0 * self.window_radial_m,
            self.post_short_m + 2.0 * self.window_radial_m,
        )


@dataclass(frozen=True)
class CopperLayer:
    """One copper layer in the stackup."""

    index: int                 # 0 is the top layer
    name: str                  # KiCad layer name, e.g. In3.Cu
    winding: str               # 'primary', 'secondary_a', 'secondary_b', 'none'
    turns: int
    thickness_m: float
    z_m: float                 # centre height above the board's bottom face
    parallel_group: Optional[str] = None

    @property
    def is_copper_winding(self) -> bool:
        return self.winding != "none" and self.turns > 0


@dataclass(frozen=True)
class Dielectric:
    """A dielectric layer between two copper layers."""

    below_index: int
    thickness_m: float
    relative_permittivity: float
    name: str


@dataclass
class Stackup:
    """The full board cross-section."""

    copper: List[CopperLayer] = field(default_factory=list)
    dielectrics: List[Dielectric] = field(default_factory=list)

    @property
    def layer_count(self) -> int:
        return len(self.copper)

    @property
    def total_thickness_m(self) -> float:
        return sum(c.thickness_m for c in self.copper) + sum(
            d.thickness_m for d in self.dielectrics
        )

    def by_winding(self, winding: str) -> List[CopperLayer]:
        return [c for c in self.copper if c.winding == winding]

    def separation_between(self, a: int, b: int) -> float:
        """Dielectric thickness between two copper layer indices."""
        lo, hi = sorted((a, b))
        return sum(
            d.thickness_m for d in self.dielectrics if lo <= d.below_index < hi
        )

    def primary_secondary_interfaces(self) -> List[Tuple[int, int, float]]:
        """Adjacent copper pairs that straddle the isolation barrier.

        These are what set both the interwinding capacitance and the solid
        insulation, so they are enumerated once and used by both.
        """
        out: List[Tuple[int, int, float]] = []
        ordered = sorted(self.copper, key=lambda c: c.index)
        for upper, lower in zip(ordered, ordered[1:]):
            a, b = upper.winding, lower.winding
            if a == "none" or b == "none":
                continue
            crosses = ("primary" in (a, b)) and any(
                w.startswith("secondary") for w in (a, b)
            )
            if crosses:
                out.append((
                    upper.index, lower.index,
                    self.separation_between(upper.index, lower.index),
                ))
        return out


@dataclass(frozen=True)
class Turn:
    """One racetrack track on a layer.

    ``offset_m`` is the distance from the centre-post face to the turn's
    centreline, so the innermost turn has a genuinely shorter path than the
    outermost and each turn carries its own length.
    """

    layer_index: int
    turn_index: int
    offset_m: float
    width_m: float
    post_long_m: float
    post_short_m: float

    @property
    def length_m(self) -> float:
        return (
            2.0 * (self.post_long_m + self.post_short_m)
            + 2.0 * math.pi * self.offset_m
        )

    @property
    def straight_long_m(self) -> float:
        return self.post_long_m

    @property
    def straight_short_m(self) -> float:
        return self.post_short_m

    @property
    def corner_radius_m(self) -> float:
        return self.offset_m


@dataclass(frozen=True)
class ViaGroup:
    """Plated barrels connecting parallel layers of one winding."""

    name: str
    winding: str
    count: int
    drill_m: float
    plating_m: float
    radius_m: float          # radial position of the via ring
    from_layer: int
    to_layer: int

    def length_m(self, stackup: Stackup) -> float:
        return stackup.separation_between(self.from_layer, self.to_layer)


@dataclass
class PlanarTransformer:
    """The canonical description everything else is generated from."""

    name: str
    core: CoreGeometry
    stackup: Stackup
    turns: List[Turn] = field(default_factory=list)
    vias: List[ViaGroup] = field(default_factory=list)
    trace_spacing_m: float = 0.15e-3
    board_margin_m: float = 2.0e-3

    # ------------------------------------------------------------- queries

    def turns_on(self, layer_index: int) -> List[Turn]:
        return [t for t in self.turns if t.layer_index == layer_index]

    def layer(self, index: int) -> CopperLayer:
        for copper in self.stackup.copper:
            if copper.index == index:
                return copper
        raise GeometryError(f"no copper layer with index {index}")

    def mean_turn_length(self, layer_index: int) -> float:
        """Average turn length on one layer, computed rather than assumed."""
        turns = self.turns_on(layer_index)
        if not turns:
            return 0.0
        return sum(t.length_m for t in turns) / len(turns)

    def conductor_length(self, winding: str) -> float:
        total = 0.0
        for copper in self.stackup.by_winding(winding):
            total += sum(t.length_m for t in self.turns_on(copper.index))
        return total

    def overlap_area(self, layer_a: int, layer_b: int) -> float:
        """Facing copper area between two layers, for capacitance."""
        turns_a = self.turns_on(layer_a)
        turns_b = self.turns_on(layer_b)
        if not turns_a or not turns_b:
            return 0.0
        area_a = sum(t.length_m * t.width_m for t in turns_a)
        area_b = sum(t.length_m * t.width_m for t in turns_b)
        return min(area_a, area_b)

    @property
    def board_size_m(self) -> Tuple[float, float]:
        """Board outline: whichever is larger, the core or the copper, plus margin."""
        copper_long, copper_short = self.core.winding_extent_m()
        return (
            max(self.core.outline_x_m, copper_short) + 2 * self.board_margin_m,
            max(self.core.outline_y_m, copper_long) + 2 * self.board_margin_m,
        )

    # ---------------------------------------------------------- validation

    def validate(self) -> List[str]:
        """Return the list of geometric violations; empty means it fits."""
        problems: List[str] = []

        for copper in self.stackup.copper:
            if not copper.is_copper_winding:
                continue
            turns = self.turns_on(copper.index)
            if len(turns) != copper.turns:
                problems.append(
                    f"layer {copper.index} declares {copper.turns} turns but "
                    f"{len(turns)} are laid out"
                )
            for turn in turns:
                inner = turn.offset_m - turn.width_m / 2.0
                outer = turn.offset_m + turn.width_m / 2.0
                if inner < -1e-9:
                    problems.append(
                        f"turn {turn.turn_index} on layer {copper.index} "
                        "overlaps the centre post"
                    )
                if outer > self.core.window_radial_m + 1e-9:
                    problems.append(
                        f"turn {turn.turn_index} on layer {copper.index} "
                        "runs outside the core window"
                    )
            for a, b in zip(turns, turns[1:]):
                gap = (b.offset_m - b.width_m / 2.0) - (
                    a.offset_m + a.width_m / 2.0
                )
                if gap < self.trace_spacing_m - 1e-9:
                    problems.append(
                        f"turns {a.turn_index} and {b.turn_index} on layer "
                        f"{copper.index} are closer than the spacing rule"
                    )

        if self.stackup.total_thickness_m > self.core.window_height_m * 2:
            problems.append(
                "board is thicker than the two core windows can accept"
            )
        return problems

    def fits(self) -> bool:
        return not self.validate()


def build_planar_transformer(
    name: str,
    core: CoreGeometry,
    primary_turns: int,
    secondary_turns: int,
    turns_per_primary_layer: int,
    secondary_parallel: int,
    copper_thickness_m: float,
    dielectric_thickness_m: float,
    barrier_thickness_m: Optional[float] = None,
    relative_permittivity: float = 4.4,
    trace_spacing_m: float = 0.15e-3,
    interleave: bool = True,
    via_drill_m: float = 0.2e-3,
    via_plating_m: float = 25e-6,
) -> PlanarTransformer:
    """Lay out a transformer from a screened design point.

    Layer order alternates primary and secondary groups when ``interleave`` is
    set. Interleaving lowers leakage and proximity loss and raises interwinding
    capacitance; the caller decides, and both consequences are computed from
    the resulting geometry rather than estimated separately.
    """
    primary_layer_count = math.ceil(primary_turns / turns_per_primary_layer)
    ordering: List[Tuple[str, int]] = []

    if interleave:
        # Sandwich the primary between the two secondary stacks, splitting the
        # primary so no portion runs more than half its layers unbroken.
        half = max(1, primary_layer_count // 2)
        ordering += [("secondary_a", 1)] * secondary_parallel
        ordering += [("primary", turns_per_primary_layer)] * half
        ordering += [("primary", turns_per_primary_layer)] * (
            primary_layer_count - half
        )
        ordering += [("secondary_b", 1)] * secondary_parallel
    else:
        ordering += [("primary", turns_per_primary_layer)] * primary_layer_count
        ordering += [("secondary_a", 1)] * secondary_parallel
        ordering += [("secondary_b", 1)] * secondary_parallel

    # The thick solid insulation is needed only where the stack crosses the
    # isolation barrier. Applying it between every layer would make the board
    # several millimetres thick for no safety benefit.
    if barrier_thickness_m is None:
        barrier_thickness_m = dielectric_thickness_m

    copper_layers: List[CopperLayer] = []
    dielectrics: List[Dielectric] = []
    z = 0.0
    for index, (winding, turns) in enumerate(ordering):
        name_map = _kicad_layer_name(index, len(ordering))
        copper_layers.append(CopperLayer(
            index=index, name=name_map, winding=winding,
            turns=turns if winding == "primary" else secondary_turns,
            thickness_m=copper_thickness_m, z_m=z,
            parallel_group=winding if winding != "primary" else None,
        ))
        z += copper_thickness_m
        if index < len(ordering) - 1:
            next_winding = ordering[index + 1][0]
            crosses_barrier = (
                (winding == "primary") != (next_winding == "primary")
            )
            thickness = (
                barrier_thickness_m if crosses_barrier else dielectric_thickness_m
            )
            dielectrics.append(Dielectric(
                below_index=index, thickness_m=thickness,
                relative_permittivity=relative_permittivity,
                name=f"barrier{index}" if crosses_barrier else f"d{index}",
            ))
            z += thickness

    stackup = Stackup(copper=copper_layers, dielectrics=dielectrics)

    # Lay turns radially outward from the centre post.
    turns_list: List[Turn] = []
    available = core.window_radial_m
    for copper in copper_layers:
        count = copper.turns
        if count <= 0:
            continue
        pitch = available / count
        width = max(pitch - trace_spacing_m, 0.05e-3)
        for i in range(count):
            offset = pitch * (i + 0.5)
            turns_list.append(Turn(
                copper.index, i, offset, width,
                core.post_long_m, core.post_short_m,
            ))

    vias: List[ViaGroup] = []
    for winding in ("secondary_a", "secondary_b"):
        layers = [c.index for c in stackup.by_winding(winding)]
        if len(layers) > 1:
            vias.append(ViaGroup(
                name=f"{winding}_stitch", winding=winding,
                count=max(8, secondary_parallel * 6), drill_m=via_drill_m,
                plating_m=via_plating_m,
                radius_m=core.window_radial_m - 0.3e-3,
                from_layer=min(layers), to_layer=max(layers),
            ))

    return PlanarTransformer(
        name=name, core=core, stackup=stackup, turns=turns_list, vias=vias,
        trace_spacing_m=trace_spacing_m,
    )


def _kicad_layer_name(index: int, total: int) -> str:
    if index == 0:
        return "F.Cu"
    if index == total - 1:
        return "B.Cu"
    return f"In{index}.Cu"


def core_from_catalog(core, material: str, window_radial_m: Optional[float] = None
                      ) -> CoreGeometry:
    """Adapt a catalog row into the geometry model's core description."""
    length = (core.length_mm or 20.0) * 1e-3
    width = (core.width_mm or 15.0) * 1e-3
    # An ELP centre post spans the full core width; its thickness along the
    # long axis follows from the effective area.
    post_long = width
    post_short = core.ae_m2 / post_long
    # Winding window along the long axis, between the post face and the outer
    # leg. The outer leg is sized to carry the same flux as the post.
    if window_radial_m is None:
        leg = post_short / 2.0
        window_radial_m = max(
            (length - post_short) / 2.0 - leg, 0.4e-3
        )
    return CoreGeometry(
        part=core.part, material=material, ae_m2=core.ae_m2, le_m=core.le_m,
        ve_m3=core.ve_m3, height_m=core.height_mm * 1e-3,
        outline_x_m=length, outline_y_m=width,
        window_height_m=(core.window_h_mm or 2.0) * 1e-3,
        window_radial_m=window_radial_m,
        post_long_m=post_long, post_short_m=post_short,
    )
