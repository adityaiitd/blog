"""Interwinding capacitance and the common-mode current it drives.

Interleaving is the main lever on leakage inductance and proximity loss, and
it works by putting primary and secondary copper closer together and more
often. That is also precisely how interwinding capacitance is built. The two
cannot be optimised separately, so both live here and are reported together.

In this converter the consequence is sharper than usual. Eight cells sit at
different potentials along an 800 V stack, and every one of their secondaries
is tied to the same output. Each cell therefore injects displacement current
into a shared node.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

EPS_0 = 8.8541878128e-12


class CapacitanceError(RuntimeError):
    pass


@dataclass(frozen=True)
class DielectricGap:
    """One primary-to-secondary interface in the stackup."""

    name: str
    overlap_area_m2: float
    separation_m: float
    relative_permittivity: float
    #: Fraction of the applied primary-secondary voltage across this interface.
    #: Adjacent layers in an interleaved stack do not all see the full swing.
    voltage_fraction: float = 1.0

    def capacitance_f(self) -> float:
        if self.separation_m <= 0:
            raise CapacitanceError(f"gap '{self.name}' has zero separation")
        return (
            EPS_0
            * self.relative_permittivity
            * self.overlap_area_m2
            / self.separation_m
        )

    def effective_capacitance_f(self) -> float:
        """Capacitance weighted by how much voltage actually appears across it.

        Static capacitance overstates the common-mode path when a layer pair
        moves together. Energy scales with the square of the voltage fraction,
        so that is the correct weighting for an equivalent lumped element.
        """
        return self.capacitance_f() * self.voltage_fraction ** 2


@dataclass
class StackupCapacitance:
    """Primary-to-secondary capacitance of a complete planar stackup."""

    gaps: List[DielectricGap] = field(default_factory=list)

    def add(self, gap: DielectricGap) -> DielectricGap:
        self.gaps.append(gap)
        return gap

    def static_c_ps_f(self) -> float:
        return sum(g.capacitance_f() for g in self.gaps)

    def effective_c_ps_f(self) -> float:
        return sum(g.effective_capacitance_f() for g in self.gaps)

    def per_gap(self) -> Dict[str, float]:
        return {g.name: g.capacitance_f() for g in self.gaps}

    def dominant_gap(self) -> Optional[str]:
        if not self.gaps:
            return None
        return max(self.gaps, key=lambda g: g.effective_capacitance_f()).name


def common_mode_current_a(c_ps_f: float, dvdt_v_per_s: float) -> float:
    """i_cm = C_ps * dv/dt for one switching edge."""
    return c_ps_f * dvdt_v_per_s


@dataclass(frozen=True)
class CommonModeAssessment:
    """Three different currents, because they answer different questions.

    ``i_peak`` is the displacement current during a switching edge. It is large
    and very brief, and it is what stresses a shield or a Y-capacitor.
    ``i_avg`` is the charge moved per cycle times the switching frequency, the
    right figure for a leakage-current limit. ``i_rms`` is what heats things
    and what an EMI budget is normally written against. Comparing a peak edge
    current against an RMS budget confuses two quantities that differ by more
    than an order of magnitude here.
    """

    c_ps_f: float
    dvdt_v_per_s: float
    voltage_swing_v: float
    frequency_hz: float
    i_peak_a: float
    i_avg_a: float
    i_rms_a: float
    i_rms_stack_a: float
    cell_count: int
    within_budget: bool
    budget_a: float
    edge_duration_s: float

    def describe(self) -> str:
        verdict = "within" if self.within_budget else "OVER"
        return (
            f"C_ps {self.c_ps_f*1e12:.1f} pF at {self.dvdt_v_per_s/1e9:.0f} V/ns: "
            f"peak {self.i_peak_a:.2f} A over a {self.edge_duration_s*1e9:.1f} ns "
            f"edge, {self.i_rms_a*1e3:.0f} mA rms, {self.i_avg_a*1e3:.1f} mA "
            f"average, {verdict} the {self.budget_a*1e3:.0f} mA rms budget"
        )


def assess_common_mode(
    c_ps_f: float,
    dvdt_v_per_s: float,
    cell_count: int,
    budget_a: float,
    voltage_swing_v: float,
    frequency_hz: float,
    coherent: bool = False,
) -> CommonModeAssessment:
    """Common-mode current for one cell and for the stack.

    ``coherent`` selects how cells combine. Synchronously switched cells add
    linearly, which is the worst case; interleaved cells at different phases
    partially cancel, and root-sum-square is the optimistic bound.
    """
    if min(voltage_swing_v, frequency_hz, dvdt_v_per_s) <= 0:
        raise CapacitanceError("swing, frequency and dv/dt must be positive")

    i_peak = common_mode_current_a(c_ps_f, dvdt_v_per_s)
    edge = voltage_swing_v / dvdt_v_per_s
    charge = c_ps_f * voltage_swing_v

    # Two edges per switching period, each moving the same charge.
    i_avg = 2.0 * charge * frequency_hz
    # Treating each edge as a rectangular pulse of height i_peak and width
    # ``edge`` gives the mean square directly.
    i_rms = math.sqrt(2.0 * i_peak ** 2 * edge * frequency_hz)

    stack = (
        i_rms * cell_count if coherent else i_rms * math.sqrt(cell_count)
    )
    return CommonModeAssessment(
        c_ps_f=c_ps_f, dvdt_v_per_s=dvdt_v_per_s,
        voltage_swing_v=voltage_swing_v, frequency_hz=frequency_hz,
        i_peak_a=i_peak, i_avg_a=i_avg, i_rms_a=i_rms, i_rms_stack_a=stack,
        cell_count=cell_count, within_budget=i_rms <= budget_a,
        budget_a=budget_a, edge_duration_s=edge,
    )


def shield_effect(c_ps_f: float, shield_coverage: float = 0.9) -> float:
    """Residual primary-secondary capacitance behind a Faraday shield.

    A shield does not remove the capacitance; it terminates most of the
    displacement current locally instead of letting it reach the secondary.
    Coverage is never complete, and the residual is what still couples.
    """
    if not 0.0 <= shield_coverage <= 1.0:
        raise CapacitanceError("coverage must be a fraction between 0 and 1")
    return c_ps_f * (1.0 - shield_coverage)


def leakage_capacitance_tradeoff(
    separation_m: float,
    overlap_area_m2: float,
    relative_permittivity: float,
    turns_primary: int,
    window_height_m: float,
    mean_turn_length_m: float,
) -> Tuple[float, float]:
    """The competing pair, evaluated from one geometry.

    Returns (leakage inductance, interwinding capacitance). Moving the
    windings apart raises leakage and lowers capacitance; interleaving does
    the opposite. Reporting them from a single geometry is what keeps the
    trade honest.

    The leakage estimate is the standard energy-in-the-gap expression for
    concentric planar windings and is a screening figure only; the field
    solver supersedes it.
    """
    if min(separation_m, window_height_m) <= 0:
        raise CapacitanceError("separation and window height must be positive")

    mu_0 = 4.0e-7 * math.pi
    l_leak = (
        mu_0
        * turns_primary ** 2
        * mean_turn_length_m
        * separation_m
        / window_height_m
    )
    c_ps = EPS_0 * relative_permittivity * overlap_area_m2 / separation_m
    return l_leak, c_ps
