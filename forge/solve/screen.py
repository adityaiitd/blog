"""Analytic screening: enumerate planar transformer candidates and filter them.

Screening is deliberately cheap and deliberately strict. Every candidate is
evaluated with closed-form models and rejected on the first hard constraint it
violates, so that the expensive field solver only ever sees geometries that
already make sense. Rejection reasons are kept, because the pattern of
rejections is usually more informative than the survivors.

A candidate that asks a material about conditions outside its characterised
range is rejected rather than extrapolated. That single rule does most of the
work of keeping the results honest.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from ..data.catalog import Catalog, Core, Device
from ..physics import capacitance as cap
from ..physics import llc
from ..physics import thermal
from ..physics import windings as wind
from ..physics.coreloss import DomainError, MaterialLossModel, igse_pv


@dataclass(frozen=True)
class ScreenInputs:
    """Everything screening needs from the frozen requirements."""

    v_cell_nominal_v: float
    v_cell_max_transient_v: float
    v_out_v: float
    i_out_a: float
    p_out_w: float
    turns_ratio_n: float
    max_height_mm: float
    max_layers: int
    core_flux_derating: float
    t_max_core_c: float
    t_max_winding_c: float
    ambient_sweep_c: Sequence[float]
    velocity_sweep_m_s: Sequence[float]
    cm_capacitance_max_f: float
    dvdt_v_per_s: float
    cm_current_max_a: float
    cell_count: int
    min_trace_width_m: float
    min_via_drill_m: float
    solid_insulation_min_m: float
    heatsink_resistance_k_w: float

    @staticmethod
    def from_lock(lock) -> "ScreenInputs":
        c, d = lock.converter, lock.diablo
        return ScreenInputs(
            v_cell_nominal_v=c.value("conv.v_cell_nominal"),
            v_cell_max_transient_v=c.value("conv.v_cell_max_transient"),
            v_out_v=c.value("conv.v_out_nominal"),
            i_out_a=c.value("conv.i_out_cell"),
            p_out_w=c.value("conv.p_out_cell"),
            turns_ratio_n=4.0,
            max_height_mm=c.value("conv.converter_height"),
            max_layers=int(c.value("conv.transformer_board_layers")),
            core_flux_derating=c.value("conv.core_flux_derating"),
            t_max_core_c=c.value("conv.t_max_core"),
            t_max_winding_c=c.value("conv.t_max_winding"),
            ambient_sweep_c=tuple(
                np.linspace(*c.get("conv.ambient_temperature").sensitivity, 3)
            ),
            velocity_sweep_m_s=tuple(
                np.linspace(*c.get("conv.airflow_velocity").sensitivity, 3)
            ),
            cm_capacitance_max_f=c.value("conv.cm_capacitance_max") * 1e-12,
            dvdt_v_per_s=c.value("conv.dvdt_max") * 1e9,
            cm_current_max_a=c.value("conv.cm_current_max"),
            cell_count=int(c.value("conv.cell_count")),
            min_trace_width_m=c.value("conv.min_trace_width") * 1e-3,
            min_via_drill_m=c.value("conv.min_via_drill") * 1e-3,
            solid_insulation_min_m=c.value("conv.solid_insulation_min") * 1e-3,
            heatsink_resistance_k_w=c.value("conv.heatsink_resistance"),
        )


@dataclass
class Candidate:
    """One screened design point."""

    core: Core
    material: str
    frequency_hz: float
    n_primary_turns: int
    n_secondary_turns: int
    copper_oz: float
    interleaving: str
    turns_per_primary_layer: int
    secondary_parallel: int
    b_peak_t: float
    core_loss_w: float
    copper_loss_w: float
    via_loss_w: float
    total_loss_w: float
    efficiency: float
    l_m_h: float
    l_r_h: float
    c_r_f: float
    c_ps_f: float
    zvs: llc.ZvsResult
    winding_c: float
    core_c: float
    layers_used: int
    notes: List[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return (
            f"{self.core.part}/{self.material}/{self.frequency_hz/1e3:.0f}kHz/"
            f"{self.n_primary_turns}T/{self.copper_oz}oz/{self.interleaving}/"
            f"{self.turns_per_primary_layer}tpl/{self.secondary_parallel}p"
        )


@dataclass
class ScreenReport:
    candidates: List[Candidate] = field(default_factory=list)
    rejections: Dict[str, int] = field(default_factory=dict)
    examined: int = 0

    def reject(self, reason: str) -> None:
        self.rejections[reason] = self.rejections.get(reason, 0) + 1

    def best(self, count: int = 10) -> List[Candidate]:
        return sorted(self.candidates, key=lambda c: c.total_loss_w)[:count]

    def summary(self) -> str:
        lines = [
            f"examined {self.examined} geometries, "
            f"{len(self.candidates)} feasible"
        ]
        for reason, n in sorted(
            self.rejections.items(), key=lambda kv: -kv[1]
        ):
            lines.append(f"  rejected {n:>5}  {reason}")
        return "\n".join(lines)


#: Interleaving patterns, expressed as the number of layers between zero-MMF
#: planes. Fewer layers per portion means a lower proximity penalty and a
#: higher interwinding capacitance.
INTERLEAVING = {
    "none": 1,
    "simple": 2,
    "full": 4,
}


def _mean_turn_length_m(core: Core) -> float:
    """Approximate mean length of turn from the core footprint.

    Screening only. The canonical geometry model computes this per layer from
    the actual copper, which is what the field solver and the board file use.
    """
    if core.window_w_mm and core.window_h_mm:
        return 2.0 * (core.window_w_mm + core.window_h_mm) * 1e-3
    # Fall back to the core outline; ELP windings wrap the centre post.
    return math.pi * math.sqrt(core.ae_mm2) * 1.8e-3


def _trace_width_m(core: Core, min_width_m: float) -> float:
    """Usable trace width for a turn on a planar layer."""
    if core.window_w_mm:
        return max(core.window_w_mm * 1e-3 * 0.8, min_width_m)
    return max(math.sqrt(core.ae_mm2) * 1e-3 * 0.6, min_width_m)


def evaluate(
    core: Core,
    material: MaterialLossModel,
    frequency_hz: float,
    n_primary: int,
    copper_oz: float,
    copper_thickness_m: float,
    interleaving: str,
    turns_per_primary_layer: int,
    secondary_parallel: int,
    inputs: ScreenInputs,
    primary_device: Device,
    secondary_device: Device,
    report: ScreenReport,
) -> Optional[Candidate]:
    """Evaluate one geometry, returning None with a logged reason if infeasible."""
    report.examined += 1
    notes: List[str] = []

    n_secondary = int(round(n_primary / inputs.turns_ratio_n))
    if n_secondary < 1 or n_secondary * inputs.turns_ratio_n != n_primary:
        report.reject("turns ratio not realisable in whole turns")
        return None

    primary_layer_count = math.ceil(n_primary / turns_per_primary_layer)
    # Each centre-tapped half gets its own parallel stack.
    layers_used = primary_layer_count + 2 * secondary_parallel
    if layers_used > inputs.max_layers:
        report.reject(f"needs more than {inputs.max_layers} layers")
        return None

    if not material.suits_frequency(frequency_hz):
        report.reject(f"{material.material} not intended for this frequency")
        return None

    b_peak = llc.flux_density_peak(
        inputs.v_out_v, inputs.turns_ratio_n, frequency_hz,
        core.ae_m2, n_primary,
    )
    b_limit = material.b_sat_at(inputs.t_max_core_c) * inputs.core_flux_derating
    if b_peak > b_limit:
        report.reject("peak flux exceeds the derated saturation limit")
        return None

    # Core loss over the real triangular flux waveform.
    try:
        t, b_wave = llc.flux_waveform(
            inputs.v_out_v, inputs.turns_ratio_n, frequency_hz,
            core.ae_m2, n_primary,
        )
        fit = material.fit_at(inputs.t_max_core_c)
        pv = igse_pv(fit, t, b_wave)
    except DomainError:
        report.reject("flux or frequency outside the material's fitted domain")
        return None
    core_loss = pv * core.ve_m3

    # Tank. Lm is set by the ZVS charge requirement, which is the binding
    # constraint, then Lr follows from a practical ratio and Cr from resonance.
    deadtime = 20e-9
    q_oss_total = 2.0 * primary_device.q_oss_scaled(
        inputs.v_cell_nominal_v
    ) * 1e-9
    c_stray = 30e-12
    charge_required = q_oss_total + c_stray * inputs.v_cell_nominal_v
    l_m_limit = (
        inputs.turns_ratio_n * inputs.v_out_v * deadtime
        / (4.0 * frequency_hz * charge_required)
    )
    l_m = l_m_limit * 0.8
    l_r = l_m / 6.0
    try:
        tank = llc.TankParameters(l_r_h=l_r, l_m_h=l_m, c_r_f=1e-9, n=inputs.turns_ratio_n)
    except llc.LLCError:
        report.reject("degenerate tank")
        return None
    c_r = llc.resonant_capacitor_for(l_r, frequency_hz)
    tank = llc.TankParameters(l_r_h=l_r, l_m_h=l_m, c_r_f=c_r, n=inputs.turns_ratio_n)

    op = llc.operating_point(
        tank, inputs.v_cell_nominal_v, inputs.v_out_v, inputs.i_out_a,
        frequency_hz,
    )
    zvs = llc.zvs_charge(
        tank, op, q_oss_total, c_stray, deadtime, inputs.v_cell_nominal_v
    )
    if not zvs.achieved:
        report.reject("charge-based ZVS not met")
        return None

    # Windings. The primary carries a modest current in series turns; the
    # secondary carries 60 A through one or two turns, so it is replicated
    # across parallel layers, which is what real planar designs do and what
    # sets the layer budget.
    mlt = _mean_turn_length_m(core)
    trace_w = _trace_width_m(core, inputs.min_trace_width_m)
    per_portion = INTERLEAVING[interleaving]

    primary_layers = [
        wind.Layer(
            f"p{i}", "primary", turns_per_primary_layer, copper_thickness_m,
            trace_w, mlt,
        )
        for i in range(primary_layer_count)
    ]
    primary_portions = [
        wind.WindingPortion(primary_layers[i:i + per_portion])
        for i in range(0, len(primary_layers), per_portion)
    ]
    primary_loss = sum(
        op.i_primary_rms_a ** 2
        * portion.ac_resistance(frequency_hz, inputs.t_max_winding_c)
        for portion in primary_portions
    )

    # One representative secondary layer, carrying its share of the current.
    secondary_layer = wind.Layer(
        "s", "secondary_a", n_secondary, copper_thickness_m, trace_w, mlt
    )
    secondary_portion = wind.WindingPortion([secondary_layer])
    r_secondary_layer = secondary_portion.ac_resistance(
        frequency_hz, inputs.t_max_winding_c
    )
    # Ps parallel layers each carry I/Ps, so total loss is I^2 * R / Ps.
    secondary_loss = (
        op.i_secondary_rms_a ** 2 * r_secondary_layer / secondary_parallel
    ) * 2.0  # two centre-tapped halves, each conducting half the time

    vias = wind.ViaField(
        count=max(8, int(inputs.i_out_a / 3.0)),
        drill_diameter_m=inputs.min_via_drill_m,
        plating_thickness_m=25e-6,
        length_m=1.6e-3,
    )
    via_loss = op.i_secondary_rms_a ** 2 * vias.resistance(inputs.t_max_winding_c)

    copper_loss = primary_loss + secondary_loss

    # Interwinding capacitance from the primary-secondary interfaces created
    # by this interleaving pattern.
    overlap = (core.window_w_mm or math.sqrt(core.ae_mm2)) * 1e-3 * mlt
    # Interleaving creates a primary-secondary boundary each time the stack
    # alternates, so more portions means more capacitive interfaces.
    interfaces = max(1, min(2 * secondary_parallel, len(primary_portions) + 1))
    stack = cap.StackupCapacitance()
    for i in range(interfaces):
        stack.add(cap.DielectricGap(
            name=f"ps{i}", overlap_area_m2=overlap,
            separation_m=inputs.solid_insulation_min_m,
            relative_permittivity=4.4,
            voltage_fraction=1.0 / max(1, interfaces),
        ))
    c_ps = stack.effective_c_ps_f()
    if c_ps > inputs.cm_capacitance_max_f:
        report.reject("interwinding capacitance over budget")
        return None

    cm = cap.assess_common_mode(
        c_ps, inputs.dvdt_v_per_s, inputs.cell_count, inputs.cm_current_max_a,
        voltage_swing_v=inputs.v_cell_nominal_v, frequency_hz=frequency_hz,
    )
    if not cm.within_budget:
        report.reject("common-mode rms current over budget")
        return None

    # Thermal, swept over the boundary we cannot pin down.
    surface_area = 2.0 * (core.length_mm or 20.0) * (core.width_mm or 20.0) * 1e-6
    surface = thermal.sweep_boundary(
        copper_loss_at_20c_w=copper_loss + via_loss,
        core_loss_fn=lambda t_c: core_loss,
        ambient_range_c=inputs.ambient_sweep_c,
        velocity_range_m_s=inputs.velocity_sweep_m_s,
        characteristic_length_m=(core.length_mm or 20.0) * 1e-3,
        surface_area_m2=surface_area,
        conduction_resistance_k_w=inputs.heatsink_resistance_k_w,
    )
    if not surface.within_limits(inputs.t_max_winding_c, inputs.t_max_core_c):
        report.reject("exceeds a temperature limit somewhere in the sweep")
        return None
    w_hi, c_hi = surface.worst_case()

    total_loss = core_loss + copper_loss + via_loss
    efficiency = inputs.p_out_w / (inputs.p_out_w + total_loss)

    if fit.alpha_assumed:
        notes.append(
            f"{material.material} alpha is assumed, not fitted; core loss "
            "carries that assumption"
        )
    notes.append(
        "screening estimate from 1D analytics; field solver supersedes the "
        "winding and leakage figures"
    )

    return Candidate(
        core=core, material=material.material, frequency_hz=frequency_hz,
        n_primary_turns=n_primary, n_secondary_turns=n_secondary,
        copper_oz=copper_oz, interleaving=interleaving,
        turns_per_primary_layer=turns_per_primary_layer,
        secondary_parallel=secondary_parallel, b_peak_t=b_peak,
        core_loss_w=core_loss, copper_loss_w=copper_loss, via_loss_w=via_loss,
        total_loss_w=total_loss, efficiency=efficiency, l_m_h=l_m, l_r_h=l_r,
        c_r_f=c_r, c_ps_f=c_ps, zvs=zvs, winding_c=w_hi, core_c=c_hi,
        layers_used=layers_used, notes=notes,
    )


def screen(
    catalog: Catalog,
    inputs: ScreenInputs,
    frequencies_hz: Sequence[float] = (700e3, 1.0e6, 1.5e6, 2.0e6),
    primary_turns: Sequence[int] = (4, 8, 12, 16),
    copper_weights_oz: Sequence[float] = (1.0, 2.0, 3.0),
    interleavings: Sequence[str] = tuple(INTERLEAVING),
    turns_per_primary_layer: Sequence[int] = (1, 2),
    secondary_parallel: Sequence[int] = (2, 3, 4),
) -> ScreenReport:
    """Enumerate and filter the design space."""
    report = ScreenReport()
    cores = catalog.cores(max_height_mm=inputs.max_height_mm)
    if not cores:
        report.reject("no catalogued core fits the height limit")
        return report

    primary_device = catalog.device("EPC2305")
    secondary_device = catalog.device("EPC2366")
    materials = [catalog.material(name) for name in catalog.materials()]

    for core in cores:
        for material in materials:
            for frequency in frequencies_hz:
                for turns in primary_turns:
                    for oz in copper_weights_oz:
                        thickness = catalog.copper_thickness_um(oz) * 1e-6
                        for pattern in interleavings:
                            for tpl in turns_per_primary_layer:
                                for par in secondary_parallel:
                                    candidate = evaluate(
                                        core, material, frequency, turns, oz,
                                        thickness, pattern, tpl, par, inputs,
                                        primary_device, secondary_device,
                                        report,
                                    )
                                    if candidate is not None:
                                        report.candidates.append(candidate)
    return report
