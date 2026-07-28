"""Export the 3D conductor geometry for targeted volumetric studies.

The 2D axisymmetric FEMM section cannot see vias, corners, terminations or the
open sides of an ELP core. Rather than pretend otherwise, this module writes
the full 3D conductor description so a volumetric solver can be pointed at the
specific features 2D drops, on the few finalists where that is worth the cost.

No solver is invoked here. The output is a neutral description plus an explicit
statement of which 2D omissions each study would close, so the report can say
what remains unbounded.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .kicad_writer import _racetrack_points
from .model import PlanarTransformer


@dataclass
class ConductorPath:
    """One winding turn as a 3D polyline with a rectangular cross-section."""

    winding: str
    layer_index: int
    turn_index: int
    width_m: float
    thickness_m: float
    points_m: List[Tuple[float, float, float]]

    @property
    def length_m(self) -> float:
        total = 0.0
        for a, b in zip(self.points_m, self.points_m[1:]):
            total += math.dist(a, b)
        return total


@dataclass
class ViaBarrel:
    winding: str
    centre_m: Tuple[float, float]
    z_from_m: float
    z_to_m: float
    drill_m: float
    plating_m: float


@dataclass
class Geometry3D:
    name: str
    conductors: List[ConductorPath] = field(default_factory=list)
    vias: List[ViaBarrel] = field(default_factory=list)
    closes_2d_gaps: List[str] = field(default_factory=list)
    still_unbounded: List[str] = field(default_factory=list)

    def total_conductor_length(self, winding: str) -> float:
        return sum(c.length_m for c in self.conductors if c.winding == winding)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "conductors": [asdict(c) for c in self.conductors],
            "vias": [asdict(v) for v in self.vias],
            "closes_2d_gaps": self.closes_2d_gaps,
            "still_unbounded": self.still_unbounded,
        }

    def save(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=1))
        return path


def export_geometry(
    transformer: PlanarTransformer, segments: int = 64
) -> Geometry3D:
    """Build the 3D description from the canonical model."""
    geometry = Geometry3D(name=transformer.name)

    for copper in sorted(transformer.stackup.copper, key=lambda c: c.index):
        if not copper.is_copper_winding:
            continue
        z = copper.z_m + copper.thickness_m / 2.0
        for turn in transformer.turns_on(copper.index):
            points = [
                (x, y, z) for x, y in _racetrack_points(turn, segments)
            ]
            geometry.conductors.append(ConductorPath(
                winding=copper.winding, layer_index=copper.index,
                turn_index=turn.turn_index, width_m=turn.width_m,
                thickness_m=copper.thickness_m, points_m=points,
            ))

    for group in transformer.vias:
        top = transformer.layer(group.from_layer)
        bottom = transformer.layer(group.to_layer)
        half_long = transformer.core.post_long_m / 2.0
        x = transformer.core.post_short_m / 2.0 + group.radius_m
        per_side = max(1, group.count // 2)
        for side in (1.0, -1.0):
            for i in range(per_side):
                y = -half_long + (2 * half_long) * (i + 0.5) / per_side
                geometry.vias.append(ViaBarrel(
                    winding=group.winding, centre_m=(side * x, y),
                    z_from_m=top.z_m, z_to_m=bottom.z_m,
                    drill_m=group.drill_m, plating_m=group.plating_m,
                ))

    geometry.closes_2d_gaps = [
        "current crowding at via barrels and their entry pads",
        "corner effects where the racetrack turns",
        "conductor edge effects across the trace width",
        "3D flux fringing at the open sides of the ELP core",
    ]
    geometry.still_unbounded = [
        "interwinding capacitance, which needs an electrostatic solve",
        "temperature-dependent material properties during the field solve",
        "manufacturing registration error between layers",
    ]
    return geometry


def write_fasthenry(
    geometry: Geometry3D, path: Path | str, frequency_hz: float
) -> Path:
    """Emit a FastHenry input deck for inductance and resistance extraction.

    FastHenry solves the magnetoquasistatic conductor problem in 3D, which is
    what is needed for leakage inductance including the via and corner paths
    that the axisymmetric section cannot represent.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"* FORGE 3D conductor export: {geometry.name}",
        "* Units are metres; sigma is copper at 20 C.",
        ".units m",
        ".default sigma=5.8e7",
        "",
    ]
    node = 0
    for conductor in geometry.conductors:
        lines.append(
            f"* {conductor.winding} layer {conductor.layer_index} "
            f"turn {conductor.turn_index}"
        )
        first = node
        for point in conductor.points_m:
            lines.append(
                f"N{node} x={point[0]:.6g} y={point[1]:.6g} z={point[2]:.6g}"
            )
            node += 1
        for i in range(first, node - 1):
            lines.append(
                f"E{i} N{i} N{i + 1} w={conductor.width_m:.6g} "
                f"h={conductor.thickness_m:.6g}"
            )
        lines.append("")

    lines += [
        f".freq fmin={frequency_hz:g} fmax={frequency_hz:g} ndec=1",
        ".end",
    ]
    path.write_text("\n".join(lines) + "\n")
    return path
