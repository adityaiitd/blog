"""Circuit verification in ngspice, in the order that keeps claims honest.

Four rungs, each answering something the one below it cannot:

1. Analytic first-harmonic gain. Cheap, and it is the model the tank was
   designed against, so disagreement here means a coding error rather than a
   physical discovery.
2. Switched transient of one cell with real device capacitance. This is the
   first rung that can say anything about zero-voltage switching, because an
   ideal switch has no output charge to drain.
3. Eight-cell sharing with deliberate component mismatch. Simulating eight
   identical cells proves nothing: they share by symmetry. The question is what
   happens when they differ.
4. Fault cases, of which the open cell matters most: the survivors absorb the
   departed cell's share of the bus.

Nothing here confirms ZVS in hardware. The wording throughout is "predicted",
and the acceptance criteria for the real thing live in the hardware gate.
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


class SpiceError(RuntimeError):
    pass


def ngspice_available() -> bool:
    return shutil.which("ngspice") is not None


def run_netlist(netlist: str, workdir: Optional[Path] = None,
                timeout: float = 300.0) -> Tuple[str, Dict[str, List[float]]]:
    """Run a netlist in batch mode and parse whatever it printed."""
    if not ngspice_available():
        raise SpiceError("ngspice is not installed")
    owns = workdir is None
    work = Path(workdir or tempfile.mkdtemp(prefix="forge-spice-"))
    work.mkdir(parents=True, exist_ok=True)
    path = work / "deck.cir"
    path.write_text(netlist)
    try:
        proc = subprocess.run(
            ["ngspice", "-b", str(path)],
            capture_output=True, text=True, timeout=timeout, cwd=work,
        )
        return proc.stdout + proc.stderr, _parse_print(proc.stdout)
    finally:
        if owns:
            shutil.rmtree(work, ignore_errors=True)


def _interpolate(xs: List[float], ys: List[float], x: float) -> float:
    """Linear interpolation, clamped to the sampled range."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            span = xs[i + 1] - xs[i]
            if span <= 0:
                return ys[i]
            t = (x - xs[i]) / span
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


def _parse_print(output: str) -> Dict[str, List[float]]:
    """Pull columns out of ngspice's print tables."""
    columns: Dict[str, List[float]] = {}
    headers: List[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("-"):
            continue
        parts = stripped.split()
        if parts[0].lower() == "index":
            headers = [p.lower() for p in parts[1:]]
            for h in headers:
                columns.setdefault(h, [])
            continue
        if headers and parts[0].isdigit() and len(parts) >= len(headers) + 1:
            for name, raw in zip(headers, parts[1:]):
                try:
                    columns[name].append(float(raw))
                except ValueError:
                    pass
    return columns


# ------------------------------------------------------------ rung 1: gain

@dataclass
class GainCheck:
    frequencies_hz: List[float]
    gain_spice: List[float]
    gain_analytic: List[float]
    max_relative_error: float
    agrees: bool

    def describe(self) -> str:
        verdict = "agrees with" if self.agrees else "DISAGREES with"
        return (
            f"AC sweep {verdict} the analytic model; worst relative error "
            f"{self.max_relative_error:.2%}"
        )


def check_gain(
    l_r_h: float, l_m_h: float, c_r_f: float, n: float, r_load_ohm: float,
    points: int = 25, tolerance: float = 0.05,
) -> GainCheck:
    """Compare an ngspice AC sweep against the first-harmonic model.

    The tank is driven as a linear network with the rectifier replaced by its
    equivalent resistance, which is exactly what the analytic model assumes.
    Agreement therefore checks the implementation, not the physics.
    """
    from ..physics.llc import TankParameters, fha_gain

    tank = TankParameters(l_r_h=l_r_h, l_m_h=l_m_h, c_r_f=c_r_f, n=n)
    r_ac = tank.r_ac_ohm(r_load_ohm)
    f_r = tank.f_r_hz
    f_lo, f_hi = f_r * 0.5, f_r * 1.6

    netlist = f"""FORGE LLC tank, first-harmonic equivalent
Vin in 0 AC 1
Lr in mid {l_r_h:.6e}
Cr mid tank {c_r_f:.6e}
Lm tank 0 {l_m_h:.6e}
Rac tank 0 {r_ac:.6e}
.ac dec {points} {f_lo:.6e} {f_hi:.6e}
.print ac vm(tank)
.end
"""
    _, columns = run_netlist(netlist)
    freqs = columns.get("frequency", [])
    mags = columns.get("v(tank)", []) or columns.get("vm(tank)", [])
    if not freqs or not mags:
        raise SpiceError("AC sweep produced no usable output")

    analytic = [fha_gain(tank, f, r_load_ohm) for f in freqs]
    errors = [
        abs(s - a) / a for s, a in zip(mags, analytic) if a > 1e-9
    ]
    worst = max(errors) if errors else float("inf")
    return GainCheck(freqs, mags, analytic, worst, worst <= tolerance)


# -------------------------------------------------- rung 2: switched cell

@dataclass
class ZvsSimulation:
    achieved: bool
    residual_volts: float
    deadtime_s: float
    switch_node_at_turn_on_v: float
    note: str

    def describe(self) -> str:
        return (
            f"switch node is at {self.switch_node_at_turn_on_v:.1f} V when the "
            f"next device turns on, after a {self.deadtime_s*1e9:.0f} ns dead "
            f"time ({'ZVS predicted' if self.achieved else 'hard switching'})"
        )


def simulate_zvs(
    l_r_h: float, l_m_h: float, c_r_f: float, n: float, v_cell_v: float,
    v_out_v: float, i_out_a: float, deadtime_s: float, c_oss_f: float,
    frequency_hz: float, cycles: int = 6,
) -> ZvsSimulation:
    """Switched half bridge, checking whether the node actually reaches zero.

    Device output capacitance is modelled as a fixed capacitor at the switch
    node, which is a simplification: real GaN output capacitance is strongly
    non-linear with voltage and stores more charge at low voltage than a linear
    model suggests. This therefore reads slightly optimistic, and the residual
    voltage is reported rather than a bare pass or fail.
    """
    period = 1.0 / frequency_hz
    half = period / 2.0
    on_time = half - deadtime_s
    r_load = v_out_v / max(i_out_a, 1e-6)
    r_ac = (8.0 / math.pi ** 2) * n ** 2 * r_load
    stop = cycles * period

    # Switches as voltage-controlled resistors driven by pulse sources.
    netlist = f"""FORGE switched half-bridge LLC cell
.param TD={deadtime_s:.6e} TON={on_time:.6e} PER={period:.6e}
Vbus bus 0 DC {v_cell_v:.6e}
Vgh gh 0 PULSE(0 1 0 1n 1n {{TON}} {{PER}})
Vgl gl 0 PULSE(0 1 {{{half:.6e}}} 1n 1n {{TON}} {{PER}})
Sh bus sw gh 0 SWMOD
Sl sw 0 gl 0 SWMOD
* GaN conducts in reverse without a true body diode, but functionally the
* switch node is clamped once it swings a diode drop past either rail.
* Without these the node rings far below ground and the result is nonsense.
Dh sw bus DCLAMP
Dl 0 sw DCLAMP
Coss sw 0 {c_oss_f:.6e}
Lr sw mid {l_r_h:.6e}
Cr mid tank {c_r_f:.6e}
Lm tank 0 {l_m_h:.6e}
Rac tank 0 {r_ac:.6e}
.model SWMOD SW(Ron=5m Roff=1e9 Vt=0.5 Vh=0.1)
.model DCLAMP D(Is=1e-12 N=1.2 Rs=5m)
.tran {period/2000:.6e} {stop:.6e} {stop - 1.2*period:.6e}
.print tran v(sw)
.options reltol=1e-4 abstol=1e-9 vntol=1e-6
.end
"""
    output, columns = run_netlist(netlist)
    node = columns.get("v(sw)", [])
    times = columns.get("time", [])
    if not node or not times:
        raise SpiceError(f"transient produced no output: {output[-400:]}")

    # Sample at the end of the dead time, not the minimum over the window.
    #
    # The low-side switch grounds this node for half of every cycle, so the
    # window minimum is always about zero and would declare ZVS achieved for
    # any design at all. The question is only ever what the node has reached by
    # the instant the next device turns on.
    last_start = times[-1] - (times[-1] % period)
    sample_at = last_start + half - 0.02 * deadtime_s
    if sample_at > times[-1] or sample_at < times[0]:
        sample_at = last_start - period + half - 0.02 * deadtime_s
    lowest = _interpolate(times, node, sample_at)
    # Clamped below ground means the tank had more than enough charge to swing
    # the node; the diode simply caught the overshoot.
    clamped = lowest < -0.3
    residual = max(lowest, 0.0)
    achieved = residual < 0.1 * v_cell_v
    note = (
        "device capacitance modelled as linear, which understates the charge "
        "stored near zero volts; treat as optimistic"
    )
    if clamped:
        note += (
            ". The node reached the reverse-conduction clamp, so there was "
            "surplus commutation charge: magnetising inductance could be "
            "raised to cut circulating loss"
        )
    return ZvsSimulation(
        achieved=achieved, residual_volts=residual, deadtime_s=deadtime_s,
        switch_node_at_turn_on_v=lowest, note=note,
    )


# ------------------------------------------- rung 3: eight-cell sharing

@dataclass
class SharingResult:
    cell_voltages: List[float]
    mean_v: float
    spread: float
    worst_cell: int
    within_limit: bool
    limit_v: float

    def describe(self) -> str:
        return (
            f"cell voltages {min(self.cell_voltages):.1f} to "
            f"{max(self.cell_voltages):.1f} V, spread {self.spread:.1%} about "
            f"the mean; worst is cell {self.worst_cell + 1}"
        )


def simulate_sharing(
    bus_v: float,
    cells: int,
    capacitance_f: Sequence[float],
    load_conductance: Sequence[float],
    limit_v: float,
) -> SharingResult:
    """Steady-state input voltage division across a mismatched series stack.

    Each cell is represented by its input capacitor and an equivalent load
    conductance standing in for the power it draws. Mismatch in either makes
    the division uneven, which is the thing the natural-balancing claim has to
    survive.
    """
    if len(capacitance_f) != cells or len(load_conductance) != cells:
        raise SpiceError("need one capacitance and conductance per cell")

    lines = ["FORGE ISOP input voltage sharing", f"Vbus n0 0 DC {bus_v:.6e}"]
    for i in range(cells):
        top, bottom = f"n{i}", f"n{i+1}" if i < cells - 1 else "0"
        lines.append(f"C{i} {top} {bottom} {capacitance_f[i]:.6e}")
        lines.append(f"R{i} {top} {bottom} {1.0/load_conductance[i]:.6e}")
    # A single-point .dc sweep prints a parseable table; .op does not.
    probes = " ".join(f"v(n{i})" for i in range(cells))
    lines += [f".dc Vbus {bus_v:.6e} {bus_v:.6e} 1", f".print dc {probes}", ".end"]
    output, columns = run_netlist("\n".join(lines) + "\n")

    nodes: Dict[str, float] = {}
    for i in range(cells):
        series = columns.get(f"v(n{i})", [])
        if series:
            nodes[f"n{i}"] = series[-1]

    if len(nodes) < cells:
        raise SpiceError(
            f"sharing sweep returned {len(nodes)} of {cells} node voltages; "
            f"output was: {output[-300:]}"
        )

    voltages: List[float] = []
    for i in range(cells):
        top = nodes[f"n{i}"]
        bottom = nodes.get(f"n{i+1}", 0.0)
        voltages.append(top - bottom)

    mean = sum(voltages) / len(voltages)
    spread = (max(voltages) - min(voltages)) / mean if mean else 0.0
    worst = max(range(cells), key=lambda i: voltages[i])
    return SharingResult(
        cell_voltages=voltages, mean_v=mean, spread=spread, worst_cell=worst,
        within_limit=max(voltages) <= limit_v, limit_v=limit_v,
    )


# ------------------------------------------------------ rung 4: faults

@dataclass
class FaultResult:
    scenario: str
    surviving_cells: int
    voltage_per_survivor: float
    device_rating_v: float
    within_rating: bool
    margin: float
    consequence: str


def analyse_faults(
    bus_v: float, cells: int, device_rating_v: float,
    derating: float = 0.8,
) -> List[FaultResult]:
    """What the survivors see when a cell stops taking its share.

    This is the dangerous direction for a series stack and needs no simulator:
    if a cell stops conducting, the bus redistributes across the rest.
    """
    limit = device_rating_v * derating
    results: List[FaultResult] = []

    for lost, scenario, consequence in [
        (0, "all cells healthy", "nominal operation"),
        (1, "one cell stops drawing power",
         "the remaining seven divide the whole bus"),
        (2, "two cells stop drawing power",
         "six cells divide the whole bus"),
    ]:
        survivors = cells - lost
        if survivors <= 0:
            continue
        per = bus_v / survivors
        results.append(FaultResult(
            scenario=scenario, surviving_cells=survivors,
            voltage_per_survivor=per, device_rating_v=device_rating_v,
            within_rating=per <= limit,
            margin=(limit - per) / limit,
            consequence=consequence,
        ))

    results.append(FaultResult(
        scenario="one cell input shorted", surviving_cells=cells - 1,
        voltage_per_survivor=bus_v / (cells - 1),
        device_rating_v=device_rating_v,
        within_rating=bus_v / (cells - 1) <= limit,
        margin=(limit - bus_v / (cells - 1)) / limit,
        consequence=(
            "a shorted cell contributes no voltage drop, so the others take "
            "its share immediately and without warning"
        ),
    ))
    return results


@dataclass
class CircuitVerification:
    gain: Optional[GainCheck] = None
    zvs: Optional[ZvsSimulation] = None
    sharing: Optional[SharingResult] = None
    faults: List[FaultResult] = field(default_factory=list)
    available: bool = True
    note: str = ""

    def summary(self) -> List[str]:
        lines: List[str] = []
        if not self.available:
            return [f"ngspice unavailable: {self.note}"]
        if self.gain:
            lines.append(f"gain      {self.gain.describe()}")
        if self.zvs:
            lines.append(f"switching {self.zvs.describe()}")
        if self.sharing:
            lines.append(f"sharing   {self.sharing.describe()}")
        for fault in self.faults:
            mark = "ok " if fault.within_rating else "OVER"
            lines.append(
                f"fault     [{mark}] {fault.scenario}: "
                f"{fault.voltage_per_survivor:.0f} V per surviving cell"
            )
        return lines
