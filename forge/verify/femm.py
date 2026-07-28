"""Run FEMM studies and turn them into inductance and resistance figures.

What this can deliver: frequency-dependent AC resistance of the layered copper,
open- and short-circuit inductances, and a mesh-convergence check on both.

What it cannot: anything three-dimensional. The section is axisymmetric, so
vias, racetrack corners, terminations and the open sides of an ELP core are
absent. Results are therefore labelled as 2D-sectional estimates, and the
inductance figures in particular should be treated as bounded rather than
final. Every result carries that label so a downstream report cannot quietly
promote it.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from ..geometry.femm_writer import unsupported_features, write_winding_study
from ..geometry.model import PlanarTransformer


class FemmError(RuntimeError):
    pass


DEFAULT_FEMM = Path.home() / ".wine/drive_c/femm42/bin/femm.exe"


@dataclass
class FemmSolution:
    """Parsed circuit properties from one solve."""

    frequency_hz: float
    windings: Dict[str, Dict[str, float]] = field(default_factory=dict)
    energy_j: float = 0.0
    mesh_size_mm: float = 0.0

    def impedance(self, winding: str) -> complex:
        data = self.windings[winding]
        current = complex(
            data.get("current_re", 0.0), data.get("current_im", 0.0)
        )
        volts = complex(data.get("volts_re", 0.0), data.get("volts_im", 0.0))
        if current == 0:
            raise FemmError(f"winding '{winding}' carried no current")
        return volts / current

    def resistance(self, winding: str) -> float:
        return self.impedance(winding).real

    def inductance(self, winding: str) -> float:
        if self.frequency_hz > 0:
            omega = 2.0 * math.pi * self.frequency_hz
            return self.impedance(winding).imag / omega
        data = self.windings[winding]
        current = data.get("current_re", 0.0)
        if current == 0:
            raise FemmError(f"winding '{winding}' carried no current")
        return data.get("flux_re", 0.0) / current


@dataclass
class FieldResult:
    """A complete field characterisation, with its limitations attached."""

    l_open_h: float
    l_short_h: float
    r_ac_ohm: Dict[int, float]
    frequency_hz: float
    mesh_converged: bool
    mesh_detail: str
    unsupported: List[str] = field(default_factory=list)
    verified: bool = True

    @property
    def l_magnetizing_h(self) -> float:
        """Open-circuit inductance, less the leakage that is also present."""
        return max(self.l_open_h - self.l_short_h, 0.0)

    @property
    def l_leakage_h(self) -> float:
        return self.l_short_h

    @property
    def coupling(self) -> float:
        if self.l_open_h <= 0:
            return 0.0
        return math.sqrt(max(1.0 - self.l_short_h / self.l_open_h, 0.0))

    def describe(self) -> str:
        status = "2D sectional estimate" if self.verified else "UNVERIFIED"
        return (
            f"Lm {self.l_magnetizing_h*1e6:.2f} uH, Lleak "
            f"{self.l_leakage_h*1e9:.1f} nH, k {self.coupling:.4f} "
            f"({status}; {self.mesh_detail})"
        )


def femm_available(femm_path: Optional[Path] = None) -> bool:
    path = Path(femm_path) if femm_path else DEFAULT_FEMM
    return path.exists() and bool(shutil.which("wine") or shutil.which("wine64"))


def run_lua(
    lua_path: Path,
    result_path: Path,
    femm_path: Optional[Path] = None,
    timeout: float = 900.0,
) -> Dict[str, float]:
    """Execute a FEMM Lua script headlessly under Wine and parse its output."""
    femm = Path(femm_path) if femm_path else DEFAULT_FEMM
    if not femm.exists():
        raise FemmError(f"FEMM not found at {femm}")
    wine = shutil.which("wine64") or shutil.which("wine")
    if wine is None:
        raise FemmError("wine is not installed")

    if result_path.exists():
        result_path.unlink()

    env = dict(os.environ)
    env.setdefault("WINEDEBUG", "-all")
    env.setdefault("DISPLAY", ":1")
    proc = subprocess.run(
        [wine, str(femm), f"-lua-script=Z:{lua_path.as_posix()}", "-windowhide"],
        capture_output=True, text=True, timeout=timeout, env=env,
    )
    if not result_path.exists():
        raise FemmError(
            f"FEMM produced no result file (rc={proc.returncode}): "
            f"{proc.stderr[-300:]}"
        )

    values: Dict[str, float] = {}
    for line in result_path.read_text().splitlines():
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        try:
            values[key.strip()] = float(raw.strip())
        except ValueError:
            continue
    return values


def _solution_from(values: Dict[str, float], frequency_hz: float,
                   mesh_size_mm: float) -> FemmSolution:
    solution = FemmSolution(frequency_hz=frequency_hz, mesh_size_mm=mesh_size_mm)
    for key, value in values.items():
        if key == "energy":
            solution.energy_j = value
            continue
        if "." not in key:
            continue
        winding, _, field_name = key.partition(".")
        solution.windings.setdefault(winding, {})[field_name] = value
    return solution


def solve(
    transformer: PlanarTransformer,
    frequency_hz: float,
    excitation: Dict[str, float],
    workdir: Path,
    mesh_size_mm: float = 0.12,
    femm_path: Optional[Path] = None,
) -> FemmSolution:
    workdir.mkdir(parents=True, exist_ok=True)
    tag = f"{int(frequency_hz)}_{mesh_size_mm:g}_{'_'.join(excitation)}"
    study = write_winding_study(
        transformer, workdir / f"study_{tag}.lua", frequency_hz, excitation,
        mesh_size_mm=mesh_size_mm,
    )
    values = run_lua(study.lua_path, study.result_path, femm_path)
    return _solution_from(values, frequency_hz, mesh_size_mm)


def extract_inductances(
    transformer: PlanarTransformer,
    frequency_hz: float,
    workdir: Path,
    mesh_size_mm: float = 0.12,
    femm_path: Optional[Path] = None,
) -> Tuple[float, float, Dict[str, FemmSolution]]:
    """Open- and short-circuit inductance from two solves of one geometry.

    The short-circuit case drives the primary and balances its amp-turns with a
    single secondary half, because in a centre-tapped rectifier only one half
    conducts at any instant. Balancing both halves at once would model a
    condition the converter never sees.
    """
    primary_turns = sum(
        c.turns for c in transformer.stackup.by_winding("primary")
    )
    secondary_layers = transformer.stackup.by_winding("secondary_a")
    secondary_turns = secondary_layers[0].turns if secondary_layers else 1

    open_solution = solve(
        transformer, frequency_hz, {"primary": 1.0}, workdir, mesh_size_mm,
        femm_path,
    )
    balance = -primary_turns / max(secondary_turns, 1)
    short_solution = solve(
        transformer, frequency_hz,
        {"primary": 1.0, "secondary_a": balance}, workdir, mesh_size_mm,
        femm_path,
    )
    return (
        open_solution.inductance("primary"),
        short_solution.inductance("primary"),
        {"open": open_solution, "short": short_solution},
    )


def mesh_convergence(
    transformer: PlanarTransformer,
    frequency_hz: float,
    workdir: Path,
    mesh_sizes_mm: Sequence[float] = (0.25, 0.15, 0.10),
    tolerance: float = 0.02,
    femm_path: Optional[Path] = None,
) -> Tuple[bool, str, Dict[float, float]]:
    """Refine the mesh until the answer stops moving.

    A field result quoted without this is a number from an arbitrary mesh.
    """
    inductances: Dict[float, float] = {}
    for size in mesh_sizes_mm:
        solution = solve(
            transformer, frequency_hz, {"primary": 1.0}, workdir, size,
            femm_path,
        )
        inductances[size] = solution.inductance("primary")

    values = [inductances[s] for s in mesh_sizes_mm]
    if len(values) < 2 or values[-1] == 0:
        return False, "insufficient mesh points", inductances
    drift = abs(values[-1] - values[-2]) / abs(values[-1])
    converged = drift <= tolerance
    detail = (
        f"mesh {mesh_sizes_mm[-2]:g} to {mesh_sizes_mm[-1]:g} mm moved "
        f"{drift:.2%}, tolerance {tolerance:.0%}"
    )
    return converged, detail, inductances


def rac_by_harmonic(
    transformer: PlanarTransformer,
    fundamental_hz: float,
    harmonics: Sequence[int],
    workdir: Path,
    mesh_size_mm: float = 0.12,
    femm_path: Optional[Path] = None,
) -> Dict[int, float]:
    """AC resistance at each harmonic of the switching frequency.

    Evaluating only at the fundamental understates loss, because R_ac keeps
    rising with frequency while the harmonic amplitudes fall.
    """
    out: Dict[int, float] = {}
    for order in harmonics:
        solution = solve(
            transformer, fundamental_hz * order, {"primary": 1.0}, workdir,
            mesh_size_mm, femm_path,
        )
        out[order] = solution.resistance("primary")
    return out


def characterise(
    transformer: PlanarTransformer,
    frequency_hz: float,
    workdir: Optional[Path] = None,
    harmonics: Sequence[int] = (1, 3, 5),
    femm_path: Optional[Path] = None,
) -> FieldResult:
    """Full 2D characterisation, or an explicit UNVERIFIED result if FEMM is absent."""
    if not femm_available(femm_path):
        return FieldResult(
            l_open_h=0.0, l_short_h=0.0, r_ac_ohm={}, frequency_hz=frequency_hz,
            mesh_converged=False,
            mesh_detail="FEMM unavailable; no field solution was run",
            unsupported=unsupported_features() + ["the entire field solution"],
            verified=False,
        )

    owns_dir = workdir is None
    work = Path(workdir or tempfile.mkdtemp(prefix="forge-femm-"))
    try:
        converged, detail, _ = mesh_convergence(
            transformer, frequency_hz, work, femm_path=femm_path
        )
        l_open, l_short, _ = extract_inductances(
            transformer, frequency_hz, work, femm_path=femm_path
        )
        resistances = rac_by_harmonic(
            transformer, frequency_hz, harmonics, work, femm_path=femm_path
        )
        return FieldResult(
            l_open_h=l_open, l_short_h=l_short, r_ac_ohm=resistances,
            frequency_hz=frequency_hz, mesh_converged=converged,
            mesh_detail=detail, unsupported=unsupported_features(),
            verified=True,
        )
    finally:
        if owns_dir:
            shutil.rmtree(work, ignore_errors=True)
