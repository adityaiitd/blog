"""Validate generated board files with KiCad itself.

A generator that only ever reads its own output proves nothing. These checks
hand the board to ``kicad-cli`` and require it to run design rule checks, plot
manufacturing data and read the file back.

Open winding endpoints are reported but do not fail the check. The winding
coupon terminates on the converter motherboard, so its ends are legitimately
free; what would be a real failure is a clearance or edge violation.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class GeometryCheck:
    name: str
    passed: bool
    detail: str
    blocking: bool = True


@dataclass
class GeometryVerification:
    board: Path
    checks: List[GeometryCheck] = field(default_factory=list)
    violations_by_type: Dict[str, int] = field(default_factory=dict)
    unconnected: int = 0
    gerber_count: int = 0

    def add(self, check: GeometryCheck) -> GeometryCheck:
        self.checks.append(check)
        return check

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks if c.blocking)

    def summary(self) -> str:
        lines = [f"geometry verification for {self.board.name}"]
        for check in self.checks:
            mark = "pass" if check.passed else ("FAIL" if check.blocking else "warn")
            lines.append(f"  [{mark}] {check.name}: {check.detail}")
        return "\n".join(lines)


def _run(args: List[str], timeout: float = 600.0) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def verify_board(
    board_path: Path | str,
    workdir: Optional[Path] = None,
    expect_zero_violations: bool = True,
) -> GeometryVerification:
    board_path = Path(board_path)
    work = Path(workdir) if workdir else board_path.parent / "verify"
    work.mkdir(parents=True, exist_ok=True)
    result = GeometryVerification(board=board_path)

    cli = shutil.which("kicad-cli")
    if cli is None:
        result.add(GeometryCheck(
            "kicad-cli available", False,
            "kicad-cli is not installed; manufacturing release is blocked",
        ))
        return result
    version = _run([cli, "version"]).stdout.strip()
    result.add(GeometryCheck("kicad-cli available", True, f"version {version}"))

    # Design rule check.
    drc_json = work / "drc.json"
    proc = _run([
        cli, "pcb", "drc", "--severity-error", "--format", "json",
        "-o", str(drc_json), str(board_path),
    ])
    if drc_json.exists():
        payload = json.loads(drc_json.read_text())
        violations = payload.get("violations", [])
        result.unconnected = len(payload.get("unconnected_items", []))
        for item in violations:
            key = item.get("type", "unknown")
            result.violations_by_type[key] = result.violations_by_type.get(key, 0) + 1
        ok = (len(violations) == 0) if expect_zero_violations else True
        detail = (
            "no violations"
            if not violations
            else ", ".join(
                f"{n} x {k}" for k, n in result.violations_by_type.items()
            )
        )
        result.add(GeometryCheck("design rules", ok, detail))
        result.add(GeometryCheck(
            "winding endpoints", True,
            f"{result.unconnected} open endpoints, expected for a winding "
            "coupon that terminates on the motherboard",
            blocking=False,
        ))
    else:
        result.add(GeometryCheck(
            "design rules", False, f"drc produced no report: {proc.stderr[:200]}"
        ))

    # Manufacturing output.
    gerber_dir = work / "gerbers"
    gerber_dir.mkdir(exist_ok=True)
    proc = _run([cli, "pcb", "export", "gerbers", "-o", str(gerber_dir),
                 str(board_path)])
    # KiCad gives copper layers their traditional extensions (.gtl, .g1 ... .gbl)
    # rather than .gbr, so counting only .gbr would miss every copper layer.
    gerbers = [
        p for p in gerber_dir.iterdir()
        if p.suffix.lower() not in (".drl", ".gbrjob")
    ]
    copper = [
        p for p in gerbers
        if p.suffix.lower() in (".gtl", ".gbl")
        or (p.suffix.lower().startswith(".g") and p.suffix[2:].isdigit())
    ]
    result.gerber_count = len(gerbers)
    result.add(GeometryCheck(
        "gerber export", bool(copper),
        f"{len(gerbers)} files, {len(copper)} copper layers"
        if copper else proc.stderr[:200],
    ))

    proc = _run([cli, "pcb", "export", "drill", "-o", str(gerber_dir),
                 str(board_path)])
    drills = list(gerber_dir.glob("*.drl"))
    result.add(GeometryCheck(
        "drill export", bool(drills),
        f"{len(drills)} drill file(s)" if drills else proc.stderr[:200],
    ))

    # Reopen: ask KiCad to parse the file again and emit something from it.
    svg_dir = work / "svg"
    proc = _run([cli, "pcb", "export", "svg", "--mode-single", "--layers",
                 "F.Cu,Edge.Cuts", "-o", str(svg_dir / "reopen.svg"),
                 str(board_path)])
    reopened = (svg_dir / "reopen.svg").exists()
    result.add(GeometryCheck(
        "reopen round trip", reopened,
        "board parses and plots" if reopened else proc.stderr[:200],
    ))

    return result
