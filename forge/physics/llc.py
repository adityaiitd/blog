"""LLC resonant tank: gain, waveforms, RMS currents and the ZVS condition.

Conventions used throughout, stated once because half-bridge LLC notation is
inconsistent in the literature:

* ``n`` is the primary-to-half-secondary turns ratio, N_p / N_s,half. For the
  4:1:1 centre-tapped transformer in this design, n = 4.
* A half bridge applies +/- V_cell/2 to the primary, so the output at unity
  tank gain is V_o = M * V_cell / (2n). At V_cell = 100 V and n = 4 this gives
  12.5 V, which is the EPC operating point.
* ``L_r`` is the *total* series resonant inductance seen by the tank:
  transformer leakage plus any discrete inductor plus interconnect. It is not
  synonymous with transformer leakage, though leakage may supply all of it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

MU_0 = 4.0e-7 * math.pi


class LLCError(RuntimeError):
    pass


@dataclass(frozen=True)
class TankParameters:
    """A resonant tank plus the transformer ratio it drives."""

    l_r_h: float          # total series resonant inductance
    l_m_h: float          # magnetizing inductance, primary referred
    c_r_f: float          # resonant capacitance
    n: float              # primary to half-secondary turns ratio

    def __post_init__(self) -> None:
        for name, value in (
            ("l_r_h", self.l_r_h), ("l_m_h", self.l_m_h),
            ("c_r_f", self.c_r_f), ("n", self.n),
        ):
            if value <= 0:
                raise LLCError(f"{name} must be positive, got {value}")
        if self.l_m_h <= self.l_r_h:
            raise LLCError(
                "magnetizing inductance must exceed the resonant inductance; "
                f"got Lm={self.l_m_h:.3e} H and Lr={self.l_r_h:.3e} H"
            )

    @property
    def f_r_hz(self) -> float:
        """Series resonant frequency."""
        return 1.0 / (2.0 * math.pi * math.sqrt(self.l_r_h * self.c_r_f))

    @property
    def f_r2_hz(self) -> float:
        """Lower resonance with the magnetizing inductance in circuit."""
        return 1.0 / (
            2.0 * math.pi * math.sqrt((self.l_r_h + self.l_m_h) * self.c_r_f)
        )

    @property
    def l_n(self) -> float:
        """Inductance ratio Lm/Lr, the classic LLC shape parameter."""
        return self.l_m_h / self.l_r_h

    @property
    def z_r_ohm(self) -> float:
        """Characteristic impedance sqrt(Lr/Cr)."""
        return math.sqrt(self.l_r_h / self.c_r_f)

    def r_ac_ohm(self, r_load_ohm: float) -> float:
        """Load resistance reflected to the primary under FHA.

        The 8/pi^2 factor converts the square-wave-driven rectifier into its
        fundamental-equivalent resistance. The n^2 refers it to the primary,
        doubled for a centre tap because each half conducts alternately.
        """
        if r_load_ohm <= 0:
            raise LLCError("load resistance must be positive")
        return (8.0 / math.pi ** 2) * (self.n ** 2) * r_load_ohm

    def q(self, r_load_ohm: float) -> float:
        return self.z_r_ohm / self.r_ac_ohm(r_load_ohm)


def fha_gain(tank: TankParameters, f_s_hz: float, r_load_ohm: float) -> float:
    """Tank voltage gain M by first-harmonic approximation.

    FHA is accurate near resonance and degrades away from it, which is
    acceptable here because the converter is a DCX operating at resonance.
    """
    f_n = f_s_hz / tank.f_r_hz
    l_n = tank.l_n
    q = tank.q(r_load_ohm)
    real = (l_n + 1.0) * f_n ** 2 - 1.0
    imag = (f_n ** 2 - 1.0) * f_n * l_n * q
    denominator = math.hypot(real, imag)
    if denominator == 0:
        raise LLCError("degenerate tank: gain is unbounded")
    return (l_n * f_n ** 2) / denominator


def output_voltage(
    tank: TankParameters, v_cell_v: float, f_s_hz: float, r_load_ohm: float
) -> float:
    """V_o = M * V_cell / (2n) for a half bridge with a centre-tapped secondary."""
    return fha_gain(tank, f_s_hz, r_load_ohm) * v_cell_v / (2.0 * tank.n)


@dataclass(frozen=True)
class OperatingPoint:
    """Currents and flux at one load, evaluated at the resonant frequency."""

    f_s_hz: float
    v_cell_v: float
    v_out_v: float
    i_out_a: float
    i_magnetizing_peak_a: float
    i_resonant_peak_a: float
    i_primary_rms_a: float
    i_secondary_rms_a: float
    i_tank_at_switching_a: float

    @property
    def p_out_w(self) -> float:
        return self.v_out_v * self.i_out_a


def operating_point(
    tank: TankParameters,
    v_cell_v: float,
    v_out_v: float,
    i_out_a: float,
    f_s_hz: Optional[float] = None,
) -> OperatingPoint:
    """Currents at resonance for a centre-tapped half-bridge LLC.

    At resonance the resonant current is very nearly sinusoidal and the
    magnetizing current is triangular and in quadrature with it. The two add
    in quadrature, which is why the primary RMS is not simply their sum.
    """
    f_s = f_s_hz or tank.f_r_hz
    if i_out_a < 0:
        raise LLCError("output current cannot be negative")

    # Each secondary half conducts for one half cycle. A rectified sinusoid of
    # peak Is averages 2*Is/pi over a full period when both halves conduct.
    i_sec_peak = math.pi * i_out_a / 2.0
    i_res_peak = i_sec_peak / tank.n

    # Magnetizing current ramps under the reflected output voltage n*Vo for
    # half a period, so its peak is n*Vo/(4*Lm*fs).
    i_mag_peak = tank.n * v_out_v / (4.0 * tank.l_m_h * f_s)

    i_res_rms = i_res_peak / math.sqrt(2.0)
    i_mag_rms = i_mag_peak / math.sqrt(3.0)
    i_pri_rms = math.hypot(i_res_rms, i_mag_rms)

    # Each secondary half carries a half-wave rectified sinusoid.
    i_sec_rms = i_sec_peak / 2.0

    return OperatingPoint(
        f_s_hz=f_s, v_cell_v=v_cell_v, v_out_v=v_out_v, i_out_a=i_out_a,
        i_magnetizing_peak_a=i_mag_peak, i_resonant_peak_a=i_res_peak,
        i_primary_rms_a=i_pri_rms, i_secondary_rms_a=i_sec_rms,
        # At resonance the resonant component crosses zero exactly at the
        # switching instant, so only the magnetizing current is available to
        # commutate the switch node.
        i_tank_at_switching_a=i_mag_peak,
    )


def flux_density_peak(
    v_out_v: float, n: float, f_s_hz: float, ae_m2: float, n_primary_turns: float
) -> float:
    """Peak flux density from the volt-seconds applied to the primary.

    B_pk = n * V_o / (4 * f_s * N_p * A_e), the half-cycle volt-second integral
    divided by turns and core area.
    """
    if min(f_s_hz, ae_m2, n_primary_turns) <= 0:
        raise LLCError("frequency, area and turns must be positive")
    return (n * v_out_v) / (4.0 * f_s_hz * n_primary_turns * ae_m2)


def flux_waveform(
    v_out_v: float,
    n: float,
    f_s_hz: float,
    ae_m2: float,
    n_primary_turns: float,
    samples: int = 2001,
) -> Tuple[np.ndarray, np.ndarray]:
    """One period of core flux for iGSE.

    A square voltage across the magnetizing inductance integrates to a
    triangular flux, which is the waveform the core actually sees. Feeding a
    sinusoid to iGSE instead would overstate the loss.
    """
    period = 1.0 / f_s_hz
    b_peak = flux_density_peak(v_out_v, n, f_s_hz, ae_m2, n_primary_turns)
    t = np.linspace(0.0, period, samples)
    phase = (t / period) % 1.0
    b = np.where(
        phase < 0.5,
        -b_peak + 4.0 * b_peak * phase,
        b_peak - 4.0 * b_peak * (phase - 0.5),
    )
    return t, b


@dataclass(frozen=True)
class ZvsResult:
    """Charge-based ZVS assessment for one half-bridge transition."""

    charge_required_c: float
    charge_available_c: float
    deadtime_s: float
    margin: float
    achieved: bool
    limiting_lm_h: float
    notes: str = ""

    def describe(self) -> str:
        verdict = "predicted" if self.achieved else "NOT predicted"
        return (
            f"ZVS {verdict}: {self.charge_available_c*1e9:.1f} nC available "
            f"against {self.charge_required_c*1e9:.1f} nC required "
            f"(margin {self.margin:+.0%})"
        )


def zvs_charge(
    tank: TankParameters,
    op: OperatingPoint,
    q_oss_total_c: float,
    c_stray_f: float,
    deadtime_s: float,
    v_cell_v: float,
) -> ZvsResult:
    """Charge-based ZVS check.

    The switch node must be swung across the full cell voltage during the
    deadtime by the tank current. Both devices' non-linear output charge plus
    the stray node capacitance have to be moved:

        integral over deadtime of |i_tank| dt  >=  Q_oss_total + C_stray * V

    Passing an ideal-tank simulation is not the same as meeting this: an ideal
    switch has no Qoss. Reporting is deliberately phrased as *predicted* ZVS,
    because confirmation needs a switched simulation with device models and
    ultimately a double-pulse measurement.
    """
    if deadtime_s <= 0:
        raise LLCError("deadtime must be positive")

    charge_required = q_oss_total_c + c_stray_f * v_cell_v
    # The magnetizing current is flat to within a few percent over a short
    # deadtime, so the integral is close to i * t_dead.
    charge_available = op.i_tank_at_switching_a * deadtime_s
    margin = (charge_available - charge_required) / charge_required

    # Rearranging i_mag_peak * t_dead >= Q gives the largest Lm that still
    # commutates the node. This is the design-facing form of the constraint.
    limiting_lm = (
        tank.n * op.v_out_v * deadtime_s / (4.0 * op.f_s_hz * charge_required)
    )

    return ZvsResult(
        charge_required_c=charge_required,
        charge_available_c=charge_available,
        deadtime_s=deadtime_s,
        margin=margin,
        achieved=charge_available >= charge_required,
        limiting_lm_h=limiting_lm,
        notes=(
            "predicted under the modelled conditions; not a confirmation of "
            "ZVS in hardware"
        ),
    )


def magnetizing_loss_penalty(
    tank: TankParameters, op: OperatingPoint, r_primary_ohm: float
) -> float:
    """Conduction loss caused purely by circulating magnetizing current.

    This is the other half of the Lm trade. Lowering Lm buys commutation
    charge for ZVS and immediately costs conduction loss, all of it present
    even at no load.
    """
    i_mag_rms = op.i_magnetizing_peak_a / math.sqrt(3.0)
    return i_mag_rms ** 2 * r_primary_ohm


def resonant_capacitor_for(l_r_h: float, f_r_hz: float) -> float:
    """Cr that places the series resonance at the requested frequency."""
    if min(l_r_h, f_r_hz) <= 0:
        raise LLCError("inductance and frequency must be positive")
    return 1.0 / (l_r_h * (2.0 * math.pi * f_r_hz) ** 2)


def capacitor_voltage_peak(op: OperatingPoint, c_r_f: float) -> float:
    """Peak voltage across the resonant capacitor.

    Sizing this wrong is a common way to destroy a resonant capacitor: the
    tank current integrates onto it every half cycle regardless of the DC bus.
    """
    return op.i_resonant_peak_a / (2.0 * math.pi * op.f_s_hz * c_r_f)
