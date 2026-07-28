"""Evaluate one design point completely, in a form both the UI and report use.

Screening is throwaway: it rejects on the first violation and moves on. This
module is the opposite. It evaluates everything about a single design, keeps
the intermediate quantities, and explains each gate in words, so a person can
see not just whether a design passes but which constraint is actually binding
and what would move it.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..data.catalog import Catalog
from ..geometry.model import PlanarTransformer, build_planar_transformer, core_from_catalog
from ..physics import capacitance as cap
from ..physics import llc, thermal
from ..physics import windings as wind
from ..physics.coreloss import DomainError, igse_pv


@dataclass
class DesignInputs:
    """Everything a person can turn a knob on."""

    core_part: str = "ELP18/4/10withI18/2/10"
    material: str = "3F46"
    frequency_hz: float = 2.0e6
    primary_turns: int = 4
    turns_per_primary_layer: int = 1
    secondary_parallel: int = 4
    copper_oz: float = 3.0
    interleave: bool = True
    dielectric_um: float = 100.0
    barrier_um: float = 400.0
    deadtime_ns: float = 20.0
    ambient_c: float = 45.0
    airflow_m_s: float = 3.0
    heatsink_k_w: float = 3.0
    lm_fraction_of_limit: float = 0.8
    ln_ratio: float = 6.0

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "DesignInputs":
        base = DesignInputs()
        for key, value in payload.items():
            if not hasattr(base, key):
                continue
            current = getattr(base, key)
            if isinstance(current, bool):
                setattr(base, key, bool(value))
            elif isinstance(current, int) and not isinstance(current, bool):
                setattr(base, key, int(value))
            elif isinstance(current, float):
                setattr(base, key, float(value))
            else:
                setattr(base, key, value)
        return base


@dataclass
class Gate:
    """One pass/fail check, with the reason a newcomer needs."""

    name: str
    passed: bool
    value: str
    limit: str
    why: str
    lever: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DesignResult:
    inputs: DesignInputs
    ok: bool
    error: str = ""
    gates: List[Gate] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    geometry: Dict[str, Any] = field(default_factory=dict)
    waveforms: Dict[str, Any] = field(default_factory=dict)
    curves: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inputs": asdict(self.inputs),
            "ok": self.ok,
            "error": self.error,
            "gates": [g.to_dict() for g in self.gates],
            "metrics": self.metrics,
            "geometry": self.geometry,
            "waveforms": self.waveforms,
            "curves": self.curves,
            "notes": self.notes,
        }


#: Operating conditions that are not knobs: they come from the frozen brief.
V_CELL = 100.0
V_OUT = 12.5
I_OUT = 60.0
P_OUT = 750.0
TURNS_RATIO = 4.0
CELL_COUNT = 8
MAX_LAYERS = 14
MAX_HEIGHT_MM = 8.0
T_MAX_CORE = 100.0
T_MAX_WINDING = 125.0
C_PS_BUDGET_F = 50e-12
CM_BUDGET_A = 0.05
DVDT_V_PER_S = 50e9
FLUX_DERATING = 0.70


def build_geometry(inputs: DesignInputs, catalog: Catalog) -> PlanarTransformer:
    core = core_from_catalog(catalog.core(inputs.core_part), inputs.material)
    thickness = catalog.copper_thickness_um(inputs.copper_oz) * 1e-6
    secondary_turns = max(1, int(round(inputs.primary_turns / TURNS_RATIO)))
    return build_planar_transformer(
        name="cell", core=core,
        primary_turns=inputs.primary_turns,
        secondary_turns=secondary_turns,
        turns_per_primary_layer=inputs.turns_per_primary_layer,
        secondary_parallel=inputs.secondary_parallel,
        copper_thickness_m=thickness,
        dielectric_thickness_m=inputs.dielectric_um * 1e-6,
        barrier_thickness_m=inputs.barrier_um * 1e-6,
        interleave=inputs.interleave,
    )


def evaluate(inputs: DesignInputs, catalog: Optional[Catalog] = None) -> DesignResult:
    """Evaluate a design point and explain every gate."""
    catalog = catalog or Catalog()
    result = DesignResult(inputs=inputs, ok=True)

    try:
        material = catalog.material(inputs.material)
    except KeyError as exc:
        return DesignResult(inputs=inputs, ok=False, error=str(exc))

    try:
        transformer = build_geometry(inputs, catalog)
    except Exception as exc:  # geometry is user-driven, so this is reachable
        return DesignResult(inputs=inputs, ok=False, error=str(exc))

    core = transformer.core
    secondary_turns = max(1, int(round(inputs.primary_turns / TURNS_RATIO)))
    f_s = inputs.frequency_hz

    # ---------------------------------------------------------- geometry
    problems = transformer.validate()
    layers = transformer.stackup.layer_count
    result.gates.append(Gate(
        "Turns fit the core window", not problems,
        f"{len(problems)} clash(es)" if problems else "no clashes", "0",
        "Copper has to sit between the centre post and the outer leg without "
        "touching either, and turns must keep their spacing from each other.",
        "Fewer turns per layer, a bigger core, or thinner traces.",
    ))
    result.gates.append(Gate(
        "Layer count", layers <= MAX_LAYERS, f"{layers} layers",
        f"<= {MAX_LAYERS}",
        "The transformer board in the reference converter is 14 layers. Every "
        "primary turn and every parallel secondary copy costs a layer.",
        "Put more turns on each primary layer, or use fewer parallel "
        "secondary layers (which raises secondary loss).",
    ))
    result.gates.append(Gate(
        "Core height", core.height_m * 1e3 <= MAX_HEIGHT_MM,
        f"{core.height_m*1e3:.1f} mm", f"<= {MAX_HEIGHT_MM:.0f} mm",
        "The whole converter is 8 mm tall, so the core set has to fit inside "
        "that. This is the constraint that eliminates most catalogue cores.",
        "A lower-profile core, at the cost of less core area.",
    ))

    # ------------------------------------------------------------- flux
    b_peak = llc.flux_density_peak(
        V_OUT, TURNS_RATIO, f_s, core.ae_m2, inputs.primary_turns
    )
    b_limit = material.b_sat_at(T_MAX_CORE) * FLUX_DERATING
    result.gates.append(Gate(
        "Peak flux density", b_peak <= b_limit,
        f"{b_peak*1e3:.1f} mT", f"<= {b_limit*1e3:.0f} mT",
        "Push the core too hard and it saturates: permeability collapses and "
        "the magnetising current runs away. The limit is derated because "
        "saturation falls as the core heats.",
        "More turns or a bigger core lowers flux; so does a higher frequency.",
    ))

    # -------------------------------------------------------- core loss
    core_loss = 0.0
    domain_ok = True
    domain_msg = ""
    try:
        fit = material.fit_at(T_MAX_CORE)
        t_wave, b_wave = llc.flux_waveform(
            V_OUT, TURNS_RATIO, f_s, core.ae_m2, inputs.primary_turns
        )
        core_loss = igse_pv(fit, t_wave, b_wave) * core.ve_m3
    except DomainError as exc:
        domain_ok = False
        domain_msg = str(exc)
        fit = None
        t_wave = np.linspace(0.0, 1.0 / f_s, 201)
        b_wave = np.zeros_like(t_wave)

    result.gates.append(Gate(
        "Material data covers this operating point", domain_ok,
        f"{f_s/1e6:.2f} MHz at {b_peak*1e3:.0f} mT",
        "inside the datasheet's measured range",
        "The loss model is fitted to the handful of points the datasheet "
        "publishes. Outside that range the fit is a guess, so FORGE refuses "
        "to use it rather than quietly extrapolating.",
        "Move the frequency or flux back into range, or pick a material "
        "characterised where you want to operate.",
    ))
    if not domain_ok:
        result.notes.append(domain_msg)

    # ---------------------------------------------------------- the tank
    primary_device = catalog.device("EPC2305")
    deadtime = inputs.deadtime_ns * 1e-9
    q_oss = 2.0 * primary_device.q_oss_scaled(V_CELL) * 1e-9
    c_stray = 30e-12
    charge_required = q_oss + c_stray * V_CELL
    l_m_limit = TURNS_RATIO * V_OUT * deadtime / (4.0 * f_s * charge_required)
    l_m = l_m_limit * inputs.lm_fraction_of_limit
    l_r = l_m / max(inputs.ln_ratio, 1.5)
    c_r = llc.resonant_capacitor_for(l_r, f_s)
    tank = llc.TankParameters(l_r_h=l_r, l_m_h=l_m, c_r_f=c_r, n=TURNS_RATIO)
    op = llc.operating_point(tank, V_CELL, V_OUT, I_OUT, f_s)
    zvs = llc.zvs_charge(tank, op, q_oss, c_stray, deadtime, V_CELL)

    result.gates.append(Gate(
        "Zero-voltage switching", zvs.achieved,
        f"{zvs.charge_available_c*1e9:.0f} nC available",
        f">= {zvs.charge_required_c*1e9:.0f} nC required",
        "Before a transistor turns on, the tank current must drain the charge "
        "sitting on the switch node. If it cannot, the transistor turns on "
        "into a charged node and burns that energy every cycle.",
        "A smaller magnetising inductance gives more current to do the job, "
        "but costs circulating loss at every load. Longer deadtime also helps.",
    ))

    # -------------------------------------------------------- windings
    thickness = catalog.copper_thickness_um(inputs.copper_oz) * 1e-6
    delta = wind.skin_depth(f_s, T_MAX_WINDING)
    per_portion = 2 if inputs.interleave else 4

    primary_layers_model = [
        wind.Layer(
            f"p{c.index}", "primary", c.turns, thickness,
            _representative_width(transformer, c.index),
            transformer.mean_turn_length(c.index),
        )
        for c in transformer.stackup.by_winding("primary")
    ]
    primary_portions = [
        wind.WindingPortion(primary_layers_model[i:i + per_portion])
        for i in range(0, len(primary_layers_model), per_portion)
    ]
    primary_loss = sum(
        op.i_primary_rms_a ** 2 * p.ac_resistance(f_s, T_MAX_WINDING)
        for p in primary_portions
    )
    r_primary = sum(p.ac_resistance(f_s, T_MAX_WINDING) for p in primary_portions)

    sec_layers = transformer.stackup.by_winding("secondary_a")
    sec_index = sec_layers[0].index if sec_layers else 0
    secondary_model = wind.Layer(
        "s", "secondary_a", secondary_turns, thickness,
        _representative_width(transformer, sec_index),
        transformer.mean_turn_length(sec_index),
    )
    r_sec_layer = wind.WindingPortion([secondary_model]).ac_resistance(
        f_s, T_MAX_WINDING
    )
    secondary_loss = (
        op.i_secondary_rms_a ** 2 * r_sec_layer / inputs.secondary_parallel
    ) * 2.0

    vias = wind.ViaField(
        count=max(8, int(I_OUT / 3.0)), drill_diameter_m=0.2e-3,
        plating_thickness_m=25e-6,
        length_m=transformer.stackup.total_thickness_m,
    )
    via_loss = op.i_secondary_rms_a ** 2 * vias.resistance(T_MAX_WINDING)
    copper_loss = primary_loss + secondary_loss
    total_loss = core_loss + copper_loss + via_loss
    efficiency = P_OUT / (P_OUT + total_loss) if total_loss >= 0 else 0.0

    # ----------------------------------------------------- capacitance
    stack = cap.StackupCapacitance()
    interfaces = transformer.stackup.primary_secondary_interfaces()
    for i, (upper, lower, separation) in enumerate(interfaces):
        stack.add(cap.DielectricGap(
            name=f"L{upper}-L{lower}",
            overlap_area_m2=transformer.overlap_area(upper, lower),
            separation_m=separation, relative_permittivity=4.4,
            voltage_fraction=1.0 / max(1, len(interfaces)),
        ))
    # Two capacitances, because they answer different questions and disagree.
    #
    # The static value is the plain facing-area capacitance and rises with
    # interleaving, since interleaving is precisely the act of putting primary
    # and secondary copper adjacent more often. The effective value additionally
    # weights each interface by the fraction of the full primary-secondary
    # voltage that actually appears across it, which falls as interfaces
    # multiply.
    #
    # The gate uses the static value. The voltage-fraction weighting is a
    # simplification, and letting the optimistic number drive a safety-adjacent
    # limit would reward interleaving for something it does not really buy.
    c_ps_static = stack.static_c_ps_f()
    c_ps_effective = stack.effective_c_ps_f()
    c_ps = c_ps_static
    cm = cap.assess_common_mode(
        c_ps, DVDT_V_PER_S, CELL_COUNT, CM_BUDGET_A, V_CELL, f_s
    )

    result.gates.append(Gate(
        "Common-mode current", cm.within_budget,
        f"{cm.i_rms_a*1e3:.0f} mA rms", f"<= {CM_BUDGET_A*1e3:.0f} mA",
        "Primary and secondary copper form a capacitor. Every switching edge "
        "pushes current through it into the shared output. Eight cells sit at "
        "different points along an 800 V stack and all inject into one node. "
        "This uses the static capacitance, which is the conservative reading.",
        "Move the windings apart or interleave less, which raises leakage "
        "inductance in exchange. A shield helps but never fully.",
    ))
    if c_ps_effective < c_ps_static * 0.9:
        result.notes.append(
            f"Interwinding capacitance is {c_ps_static*1e12:.1f} pF static but "
            f"{c_ps_effective*1e12:.1f} pF once each interface is weighted by "
            "the voltage actually across it. The gate uses the larger, "
            "conservative figure; an electrostatic field solve would settle "
            "which is right."
        )

    # ---------------------------------------------------------- thermal
    surface_area = 2.0 * core.outline_x_m * core.outline_y_m
    ambients = [inputs.ambient_c - 20.0, inputs.ambient_c, inputs.ambient_c + 10.0]
    velocities = [max(0.5, inputs.airflow_m_s - 2.0), inputs.airflow_m_s,
                  inputs.airflow_m_s + 3.0]
    surface = thermal.sweep_boundary(
        copper_loss_at_20c_w=copper_loss + via_loss,
        core_loss_fn=lambda t_c: core_loss,
        ambient_range_c=ambients, velocity_range_m_s=velocities,
        characteristic_length_m=core.outline_x_m,
        surface_area_m2=surface_area,
        conduction_resistance_k_w=inputs.heatsink_k_w,
    )
    winding_hi, core_hi = surface.worst_case()
    thermal_ok = surface.within_limits(T_MAX_WINDING, T_MAX_CORE)
    result.gates.append(Gate(
        "Temperature across the cooling sweep", thermal_ok,
        f"winding {winding_hi:.0f} C, core {core_hi:.0f} C",
        f"<= {T_MAX_WINDING:.0f} / {T_MAX_CORE:.0f} C",
        "Airflow and inlet temperature are not known for this converter, so "
        "the design has to hold at every corner of a swept range, not just at "
        "one comfortable assumption.",
        "A better heatsink path, more copper, or lower loss.",
    ))

    # ------------------------------------------------------------ output
    result.ok = all(g.passed for g in result.gates)

    result.metrics = {
        "b_peak_mT": b_peak * 1e3,
        "b_limit_mT": b_limit * 1e3,
        "core_loss_W": core_loss,
        "primary_loss_W": primary_loss,
        "secondary_loss_W": secondary_loss,
        "via_loss_W": via_loss,
        "total_loss_W": total_loss,
        "efficiency": efficiency,
        "l_m_uH": l_m * 1e6,
        "l_r_uH": l_r * 1e6,
        "c_r_nF": c_r * 1e9,
        "l_m_limit_uH": l_m_limit * 1e6,
        "f_resonant_MHz": tank.f_r_hz / 1e6,
        "i_primary_rms_A": op.i_primary_rms_a,
        "i_secondary_rms_A": op.i_secondary_rms_a,
        "i_magnetizing_peak_A": op.i_magnetizing_peak_a,
        "zvs_margin": zvs.margin,
        "zvs_required_nC": zvs.charge_required_c * 1e9,
        "zvs_available_nC": zvs.charge_available_c * 1e9,
        "c_ps_static_pF": c_ps_static * 1e12,
        "c_ps_effective_pF": c_ps_effective * 1e12,
        "c_ps_pF": c_ps * 1e12,
        "cm_peak_A": cm.i_peak_a,
        "cm_rms_mA": cm.i_rms_a * 1e3,
        "cm_avg_mA": cm.i_avg_a * 1e3,
        "winding_c": winding_hi,
        "core_c": core_hi,
        "skin_depth_um": delta * 1e6,
        "copper_thickness_um": thickness * 1e6,
        "layers": layers,
        "board_thickness_mm": transformer.stackup.total_thickness_m * 1e3,
        "secondary_turns": secondary_turns,
        "r_primary_mohm": r_primary * 1e3,
        "r_secondary_layer_mohm": r_sec_layer * 1e3,
        "capacitor_peak_V": llc.capacitor_voltage_peak(op, c_r),
    }

    result.geometry = _geometry_payload(transformer)
    result.waveforms = _waveform_payload(tank, op, t_wave, b_wave, f_s)
    result.curves = _curve_payload(tank, surface, ambients, velocities)
    return result


def _representative_width(transformer: PlanarTransformer, layer_index: int) -> float:
    turns = transformer.turns_on(layer_index)
    if not turns:
        return 0.5e-3
    return sum(t.width_m for t in turns) / len(turns)


def _geometry_payload(transformer: PlanarTransformer) -> Dict[str, Any]:
    """Everything the browser needs to draw the design, in millimetres."""
    core = transformer.core
    barriers = {
        (a, b): t for a, b, t in transformer.stackup.primary_secondary_interfaces()
    }
    layers = []
    for copper in sorted(transformer.stackup.copper, key=lambda c: c.index):
        layers.append({
            "index": copper.index,
            "name": copper.name,
            "winding": copper.winding,
            "turns": copper.turns,
            "thickness_mm": copper.thickness_m * 1e3,
            "z_mm": copper.z_m * 1e3,
            "mlt_mm": transformer.mean_turn_length(copper.index) * 1e3,
            "tracks": [
                {
                    "offset_mm": t.offset_m * 1e3,
                    "width_mm": t.width_m * 1e3,
                    "length_mm": t.length_m * 1e3,
                }
                for t in transformer.turns_on(copper.index)
            ],
        })
    dielectrics = [
        {
            "below": d.below_index,
            "thickness_mm": d.thickness_m * 1e3,
            "is_barrier": (d.below_index, d.below_index + 1) in barriers
            or d.name.startswith("barrier"),
            "name": d.name,
        }
        for d in transformer.stackup.dielectrics
    ]
    board_x, board_y = transformer.board_size_m
    return {
        "core": {
            "part": core.part,
            "post_long_mm": core.post_long_m * 1e3,
            "post_short_mm": core.post_short_m * 1e3,
            "window_radial_mm": core.window_radial_m * 1e3,
            "outline_x_mm": core.outline_x_m * 1e3,
            "outline_y_mm": core.outline_y_m * 1e3,
            "height_mm": core.height_m * 1e3,
            "ae_mm2": core.ae_m2 * 1e6,
        },
        "layers": layers,
        "dielectrics": dielectrics,
        "board_x_mm": board_x * 1e3,
        "board_y_mm": board_y * 1e3,
        "vias": [
            {
                "winding": v.winding, "count": v.count,
                "drill_mm": v.drill_m * 1e3,
                "radius_mm": v.radius_m * 1e3,
            }
            for v in transformer.vias
        ],
    }


def _waveform_payload(
    tank: llc.TankParameters, op: llc.OperatingPoint,
    t_wave: np.ndarray, b_wave: np.ndarray, f_s: float
) -> Dict[str, Any]:
    period = 1.0 / f_s
    t = np.linspace(0.0, period, 241)
    phase = 2.0 * math.pi * f_s * t
    resonant = op.i_resonant_peak_a * np.sin(phase)
    magnetizing = op.i_magnetizing_peak_a * (
        2.0 / math.pi
    ) * np.arcsin(np.sin(phase - math.pi / 2))
    primary = resonant + magnetizing
    secondary = np.abs(resonant - magnetizing) * tank.n

    step = max(1, len(t_wave) // 241)
    return {
        "t_ns": (t * 1e9).tolist(),
        "i_resonant_A": resonant.tolist(),
        "i_magnetizing_A": magnetizing.tolist(),
        "i_primary_A": primary.tolist(),
        "i_secondary_A": secondary.tolist(),
        "flux_t_ns": (t_wave[::step] * 1e9).tolist(),
        "flux_mT": (b_wave[::step] * 1e3).tolist(),
    }


def _curve_payload(
    tank: llc.TankParameters, surface: thermal.SensitivitySurface,
    ambients: Sequence[float], velocities: Sequence[float]
) -> Dict[str, Any]:
    r_load = V_OUT / I_OUT
    ratios = np.linspace(0.5, 1.6, 120)
    gains_full = [llc.fha_gain(tank, r * tank.f_r_hz, r_load) for r in ratios]
    gains_light = [
        llc.fha_gain(tank, r * tank.f_r_hz, r_load * 10.0) for r in ratios
    ]
    return {
        "gain_fn": ratios.tolist(),
        "gain_full_load": gains_full,
        "gain_light_load": gains_light,
        "thermal": {
            "ambients": list(ambients),
            "velocities": list(velocities),
            "winding_c": surface.winding_c.tolist(),
            "core_c": surface.core_c.tolist(),
        },
    }
