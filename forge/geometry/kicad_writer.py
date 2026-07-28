"""Emit a KiCad board file from the canonical geometry.

The board file is written directly as S-expressions against a pinned format
version rather than through KiCad's Python API, because the IPC API in KiCad 9
and 10 requires a running GUI and the older SWIG bindings are deprecated.
Writing the format directly keeps the generator headless and reproducible; the
tradeoff is that the output has to be validated by KiCad itself, which
``verify.geometry`` does with ``kicad-cli``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from .model import PlanarTransformer, Turn

#: KiCad board format written by KiCad 9 and read by KiCad 10.
BOARD_FORMAT_VERSION = 20241229
GENERATOR = "forge"
GENERATOR_VERSION = "9.0"

#: Segments used to approximate one circular turn. Enough that the chord error
#: stays well under the trace width at these radii.
ARC_SEGMENTS = 64

NET_FOR_WINDING = {
    "primary": ("PRI", 1),
    "secondary_a": ("SEC_A", 2),
    "secondary_b": ("SEC_B", 3),
}


def _mm(metres: float) -> float:
    return round(metres * 1000.0, 6)


def _layer_names(transformer: PlanarTransformer) -> List[str]:
    return [c.name for c in sorted(transformer.stackup.copper, key=lambda c: c.index)]


def _layer_block(names: Sequence[str]) -> str:
    rows = []
    for ordinal, name in enumerate(names):
        number = 0 if name == "F.Cu" else (31 if name == "B.Cu" else ordinal)
        rows.append(f'\t\t({number} "{name}" signal)')
    extra = [
        (32, "B.Adhes", "user", "B.Adhesive"),
        (33, "F.Adhes", "user", "F.Adhesive"),
        (34, "B.Paste", "user", None),
        (35, "F.Paste", "user", None),
        (36, "B.SilkS", "user", "B.Silkscreen"),
        (37, "F.SilkS", "user", "F.Silkscreen"),
        (38, "B.Mask", "user", None),
        (39, "F.Mask", "user", None),
        (40, "Dwgs.User", "user", "User.Drawings"),
        (41, "Cmts.User", "user", "User.Comments"),
        (44, "Edge.Cuts", "user", None),
        (45, "Margin", "user", None),
    ]
    for number, name, kind, alias in extra:
        alias_part = f' "{alias}"' if alias else ""
        rows.append(f'\t\t({number} "{name}" {kind}{alias_part})')
    return "\n".join(rows)


def _racetrack_points(
    turn: Turn, arc_segments: int, closed: bool = True
) -> List[Tuple[float, float]]:
    """Centreline of a racetrack turn: four straights joined by four arcs.

    The long axis runs in Y, matching an ELP centre post that spans the core
    width. Corner radius is the turn's offset from the post face.

    Straights are subdivided rather than emitted as single chords. That matters
    because the turn is left open by one chord to make it a spiral instead of a
    shorted ring: with a single chord per side, that break would swallow an
    entire straight run and shorten the turn by roughly a third.
    """
    half_long = turn.straight_long_m / 2.0
    half_short = turn.straight_short_m / 2.0
    radius = turn.corner_radius_m
    per_corner = max(3, arc_segments // 4)
    per_straight = max(3, arc_segments // 8)

    points: List[Tuple[float, float]] = []

    def arc(cx: float, cy: float, start: float) -> None:
        for i in range(per_corner + 1):
            angle = start + (math.pi / 2) * i / per_corner
            point = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
            if not points or point != points[-1]:
                points.append(point)

    def straight(to_x: float, to_y: float) -> None:
        x0, y0 = points[-1]
        for i in range(1, per_straight + 1):
            t = i / per_straight
            points.append((x0 + (to_x - x0) * t, y0 + (to_y - y0) * t))

    # Right side, then anticlockwise round the post.
    arc(half_short, half_long, 0.0)                 # top right corner
    straight(-half_short, half_long + radius)       # top run
    arc(-half_short, half_long, math.pi / 2)        # top left corner
    straight(-half_short - radius, -half_long)      # left run
    arc(-half_short, -half_long, math.pi)           # bottom left corner
    straight(half_short, -half_long - radius)       # bottom run
    arc(half_short, -half_long, 3 * math.pi / 2)    # bottom right corner
    if closed:
        straight(half_short + radius, half_long)    # right run, closing
    return points


def _turn_segments(turn: Turn, layer: str, net: int) -> List[str]:
    """Emit one racetrack turn as track segments."""
    # Emit the closed path minus its final short chord, so the turn is a
    # spiral rather than a shorted ring while losing only one chord of length.
    points = _racetrack_points(turn, ARC_SEGMENTS)[:-1]
    out: List[str] = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        out.append(
            f"\t(segment\n"
            f"\t\t(start {_mm(x0)} {_mm(y0)})\n"
            f"\t\t(end {_mm(x1)} {_mm(y1)})\n"
            f"\t\t(width {_mm(turn.width_m)})\n"
            f'\t\t(layer "{layer}")\n'
            f"\t\t(net {net})\n"
            f"\t)"
        )
    return out


def _via(x_m: float, y_m: float, drill_m: float, top: str, bottom: str,
         net: int) -> str:
    diameter = drill_m + 0.2e-3
    return (
        f"\t(via\n"
        f"\t\t(at {_mm(x_m)} {_mm(y_m)})\n"
        f"\t\t(size {_mm(diameter)})\n"
        f"\t\t(drill {_mm(drill_m)})\n"
        f'\t\t(layers "{top}" "{bottom}")\n'
        f"\t\t(net {net})\n"
        f"\t)"
    )


def _edge_cuts(width_m: float, height_m: float) -> List[str]:
    half_w, half_h = width_m / 2.0, height_m / 2.0
    corners = [
        (-half_w, -half_h), (half_w, -half_h),
        (half_w, half_h), (-half_w, half_h),
    ]
    out = []
    for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1]):
        out.append(
            f"\t(gr_line\n"
            f"\t\t(start {_mm(x0)} {_mm(y0)})\n"
            f"\t\t(end {_mm(x1)} {_mm(y1)})\n"
            f"\t\t(stroke (width 0.1) (type solid))\n"
            f'\t\t(layer "Edge.Cuts")\n'
            f"\t)"
        )
    return out


@dataclass
class BoardWriteResult:
    path: Path
    segments: int
    vias: int
    layers: int
    nets: int


def write_board(
    transformer: PlanarTransformer,
    path: Path | str,
    clearance_m: float = 0.15e-3,
) -> BoardWriteResult:
    """Write the transformer geometry as a KiCad board file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    layer_names = _layer_names(transformer)
    board_w, board_h = transformer.board_size_m

    body: List[str] = []
    segment_count = 0
    for copper in sorted(transformer.stackup.copper, key=lambda c: c.index):
        if not copper.is_copper_winding:
            continue
        net_name, net_id = NET_FOR_WINDING.get(copper.winding, ("N/C", 0))
        for turn in transformer.turns_on(copper.index):
            segments = _turn_segments(turn, copper.name, net_id)
            body.extend(segments)
            segment_count += len(segments)

    via_count = 0

    # Series vias joining consecutive primary layers at the spiral ends. The
    # electrical model treats the primary as N turns in series, so the board
    # has to actually connect them that way.
    primary_layers = sorted(
        transformer.stackup.by_winding("primary"), key=lambda c: c.index
    )
    _, primary_net = NET_FOR_WINDING["primary"]
    for upper, lower in zip(primary_layers, primary_layers[1:]):
        turns = transformer.turns_on(upper.index)
        if not turns:
            continue
        end = _racetrack_points(turns[-1], ARC_SEGMENTS)[-1]
        body.append(_via(
            end[0], end[1], transformer.vias[0].drill_m if transformer.vias
            else 0.2e-3, upper.name, lower.name, primary_net,
        ))
        via_count += 1

    for group in transformer.vias:
        _, net_id = NET_FOR_WINDING.get(group.winding, ("N/C", 0))
        top = transformer.layer(group.from_layer).name
        bottom = transformer.layer(group.to_layer).name
        # Stitch along the two long straight runs, where there is room, rather
        # than on a circle that would not follow the racetrack.
        half_long = transformer.core.post_long_m / 2.0
        x = transformer.core.post_short_m / 2.0 + group.radius_m
        per_side = max(1, group.count // 2)
        for side in (1.0, -1.0):
            for i in range(per_side):
                y = -half_long + (2 * half_long) * (i + 0.5) / per_side
                body.append(_via(
                    side * x, y, group.drill_m, top, bottom, net_id
                ))
                via_count += 1

    # Terminal pads. The secondary carries 60 A, so its terminations are a
    # real conductor with real resistance, not a schematic detail.
    pads: List[str] = []

    def add_pad(name: str, net_id: int, layer_name: str,
                x_m: float, y_m: float) -> None:
        pads.append(
            f'\t(footprint "forge:terminal"\n'
            f'\t\t(layer "{layer_name}")\n'
            f"\t\t(at {_mm(x_m)} {_mm(y_m)})\n"
            f'\t\t(property "Reference" "{name}"\n'
            f"\t\t\t(at 0 -1.5 0)\n"
            f'\t\t\t(layer "F.SilkS")\n'
            f"\t\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))\n"
            f"\t\t)\n"
            f'\t\t(pad "1" smd rect\n'
            f"\t\t\t(at 0 0)\n"
            f"\t\t\t(size 1.2 1.0)\n"
            f'\t\t\t(layers "{layer_name}")\n'
            f'\t\t\t(net {net_id} "{name}")\n'
            f"\t\t)\n"
            f"\t)"
        )

    # Terminals are deliberately not placed on this coupon.
    #
    # The winding ends are inside the core window, where a pad large enough to
    # carry 60 A cannot meet the clearance rule against the neighbouring turn.
    # On a real assembly these ends land on the converter motherboard, which is
    # outside the scope of this geometry. Placing pads here anyway would trade
    # a genuine DRC pass for a cosmetic connectivity number.
    #
    # The consequence is recorded rather than hidden: the board reports open
    # winding endpoints, and termination resistance is accounted for in the
    # loss model through windings.termination_resistance rather than by
    # geometry. ``add_pad`` is kept for the assembled-module variant.
    _ = add_pad

    nets = "\n".join(
        [f'\t(net 0 "")']
        + [
            f'\t(net {net_id} "{name}")'
            for name, net_id in sorted(
                NET_FOR_WINDING.values(), key=lambda kv: kv[1]
            )
        ]
    )

    content = f"""(kicad_pcb
\t(version {BOARD_FORMAT_VERSION})
\t(generator "{GENERATOR}")
\t(generator_version "{GENERATOR_VERSION}")
\t(general
\t\t(thickness {_mm(transformer.stackup.total_thickness_m)})
\t\t(legacy_teardrops no)
\t)
\t(paper "A4")
\t(layers
{_layer_block(layer_names)}
\t)
\t(setup
\t\t(pad_to_mask_clearance 0)
\t\t(allow_soldermask_bridges_in_footprints no)
\t)
{nets}
{chr(10).join(pads)}
{chr(10).join(_edge_cuts(board_w, board_h))}
{chr(10).join(body)}
)
"""
    path.write_text(content)
    return BoardWriteResult(
        path=path, segments=segment_count, vias=via_count,
        layers=len(layer_names), nets=len(NET_FOR_WINDING) + 1,
    )


def write_project(
    path: Path | str,
    clearance_m: float,
    track_width_m: float,
    via_drill_m: float,
    via_diameter_m: float,
) -> Path:
    """Write the .kicad_pro carrying this design's manufacturing constraints.

    Without it, ``kicad-cli pcb drc`` checks KiCad's stock minimums rather than
    the limits the converter brief actually specifies, and reports violations
    against rules nobody chose.
    """
    import json

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rules = {
        "min_clearance": _mm(clearance_m),
        "min_track_width": _mm(track_width_m),
        "min_through_hole_diameter": _mm(via_drill_m),
        "min_via_diameter": _mm(via_diameter_m),
        "min_via_annular_ring": _mm((via_diameter_m - via_drill_m) / 2.0),
        "min_hole_to_hole": _mm(via_drill_m),
        "min_hole_clearance": _mm(via_drill_m),
        "solder_mask_to_copper_clearance": 0.0,
    }
    project = {
        "board": {
            "design_settings": {
                "rules": rules,
                "defaults": {
                    "via_diameter": _mm(via_diameter_m),
                    "via_drill": _mm(via_drill_m),
                    "track_width": _mm(track_width_m),
                },
            }
        },
        "meta": {"filename": path.name, "version": 3},
    }
    path.write_text(json.dumps(project, indent=2))
    return path


def write_design_rules(
    path: Path | str,
    clearance_m: float,
    track_width_m: float,
    via_drill_m: float,
    via_diameter_m: float,
) -> Path:
    """Write a .kicad_dru file so DRC checks the rules this design assumes.

    Without this, DRC would silently check KiCad's defaults instead of the
    clearances the insulation basis actually calls for.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "(version 1)\n\n"
        '(rule "minimum clearance"\n'
        "\t(constraint clearance (min " + f"{_mm(clearance_m)}mm" + "))\n"
        ")\n\n"
        '(rule "minimum track width"\n'
        "\t(constraint track_width (min " + f"{_mm(track_width_m)}mm" + "))\n"
        ")\n\n"
        '(rule "via geometry"\n'
        "\t(constraint hole_size (min " + f"{_mm(via_drill_m)}mm" + "))\n"
        "\t(constraint via_diameter (min " + f"{_mm(via_diameter_m)}mm" + "))\n"
        ")\n"
    )
    return path
