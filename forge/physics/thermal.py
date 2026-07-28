"""Thermal model with an explicit cooling boundary.

A single predicted temperature implies a cooling boundary that this project
does not have: EPC publishes a converter height but no airflow, no heatsink
and no interface data. So the model takes airflow and ambient as inputs and
returns a surface over them. Where the boundary is unknown, the output is a
sensitivity map, not a number.

The copper resistance and temperature are solved as a fixed point, because
they depend on each other: hotter copper dissipates more, which makes it
hotter. Evaluating losses once at 20 C understates the answer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .windings import ALPHA_CU


class ThermalError(RuntimeError):
    pass


@dataclass(frozen=True)
class CoolingBoundary:
    """Everything the thermal answer is conditional on."""

    ambient_c: float
    air_velocity_m_s: float
    characteristic_length_m: float
    surface_area_m2: float
    #: Conduction path into the board and any cold plate, kelvin per watt.
    conduction_resistance_k_w: Optional[float] = None
    emissivity: float = 0.9

    def describe(self) -> str:
        path = (
            f", conduction {self.conduction_resistance_k_w:.2f} K/W"
            if self.conduction_resistance_k_w
            else ""
        )
        return (
            f"{self.ambient_c:.0f} C inlet, {self.air_velocity_m_s:.1f} m/s over "
            f"{self.surface_area_m2*1e4:.1f} cm2{path}"
        )


# Dry air at roughly 60 C, adequate over the range of interest.
_AIR_K = 0.028          # W/(m K)
_AIR_NU = 1.9e-5        # m^2/s
_AIR_PR = 0.70
_SIGMA_SB = 5.670374419e-8


def convection_coefficient(boundary: CoolingBoundary) -> float:
    """Forced-convection coefficient over a flat plate.

    Laminar and turbulent correlations are blended at the transition Reynolds
    number. Natural convection is used as a floor so that zero airflow does
    not predict infinite temperature.
    """
    velocity = max(boundary.air_velocity_m_s, 0.0)
    length = boundary.characteristic_length_m
    if length <= 0:
        raise ThermalError("characteristic length must be positive")

    natural_h = 5.0  # W/(m^2 K), still air over a small horizontal surface
    if velocity < 1e-6:
        return natural_h

    reynolds = velocity * length / _AIR_NU
    if reynolds < 5e5:
        nusselt = 0.664 * math.sqrt(reynolds) * _AIR_PR ** (1.0 / 3.0)
    else:
        nusselt = 0.037 * reynolds ** 0.8 * _AIR_PR ** (1.0 / 3.0)
    return max(natural_h, nusselt * _AIR_K / length)


def radiation_coefficient(
    surface_c: float, ambient_c: float, emissivity: float
) -> float:
    """Linearised radiative coefficient, small but not always negligible."""
    t_s = surface_c + 273.15
    t_a = ambient_c + 273.15
    return emissivity * _SIGMA_SB * (t_s + t_a) * (t_s ** 2 + t_a ** 2)


@dataclass
class ThermalResult:
    winding_c: float
    core_c: float
    surface_c: float
    boundary: CoolingBoundary
    copper_loss_w: float
    core_loss_w: float
    iterations: int
    converged: bool

    @property
    def total_loss_w(self) -> float:
        return self.copper_loss_w + self.core_loss_w

    @property
    def rise_k(self) -> float:
        return self.winding_c - self.boundary.ambient_c


def solve_fixed_point(
    copper_loss_at_20c_w: float,
    core_loss_fn: Callable[[float], float],
    boundary: CoolingBoundary,
    winding_to_surface_k_w: float = 2.0,
    core_to_surface_k_w: float = 3.0,
    max_iterations: int = 100,
    tolerance_k: float = 0.01,
) -> ThermalResult:
    """Solve the coupled copper-resistance and temperature problem.

    ``core_loss_fn`` takes a core temperature and returns core loss, because
    ferrite loss is not monotonic in temperature and cannot be scaled the way
    copper can.
    """
    if copper_loss_at_20c_w < 0:
        raise ThermalError("copper loss cannot be negative")

    ambient = boundary.ambient_c
    h_conv = convection_coefficient(boundary)
    winding_c = core_c = surface_c = ambient
    converged = False
    iteration = 0

    for iteration in range(1, max_iterations + 1):
        copper_loss = copper_loss_at_20c_w * (
            1.0 + ALPHA_CU * (winding_c - 20.0)
        )
        core_loss = max(core_loss_fn(core_c), 0.0)
        total = copper_loss + core_loss

        h_rad = radiation_coefficient(surface_c, ambient, boundary.emissivity)
        h_total = h_conv + h_rad
        conv_resistance = 1.0 / (h_total * boundary.surface_area_m2)
        if boundary.conduction_resistance_k_w:
            conv_resistance = 1.0 / (
                1.0 / conv_resistance + 1.0 / boundary.conduction_resistance_k_w
            )

        new_surface = ambient + total * conv_resistance
        new_winding = new_surface + copper_loss * winding_to_surface_k_w
        new_core = new_surface + core_loss * core_to_surface_k_w

        delta = max(
            abs(new_winding - winding_c),
            abs(new_core - core_c),
            abs(new_surface - surface_c),
        )
        # Under-relax; the copper feedback can oscillate when the rise is large.
        winding_c += 0.6 * (new_winding - winding_c)
        core_c += 0.6 * (new_core - core_c)
        surface_c += 0.6 * (new_surface - surface_c)

        if delta < tolerance_k:
            converged = True
            break

    copper_loss = copper_loss_at_20c_w * (1.0 + ALPHA_CU * (winding_c - 20.0))
    return ThermalResult(
        winding_c=winding_c, core_c=core_c, surface_c=surface_c,
        boundary=boundary, copper_loss_w=copper_loss,
        core_loss_w=max(core_loss_fn(core_c), 0.0),
        iterations=iteration, converged=converged,
    )


@dataclass
class SensitivitySurface:
    """Temperature over the range of cooling conditions we cannot pin down."""

    ambient_c: List[float]
    velocity_m_s: List[float]
    winding_c: np.ndarray
    core_c: np.ndarray

    def worst_case(self) -> Tuple[float, float]:
        return float(np.max(self.winding_c)), float(np.max(self.core_c))

    def best_case(self) -> Tuple[float, float]:
        return float(np.min(self.winding_c)), float(np.min(self.core_c))

    def within_limits(self, winding_limit_c: float, core_limit_c: float) -> bool:
        """True only if every corner of the swept boundary passes."""
        return bool(
            np.all(self.winding_c <= winding_limit_c)
            and np.all(self.core_c <= core_limit_c)
        )

    def failing_fraction(
        self, winding_limit_c: float, core_limit_c: float
    ) -> float:
        failures = (self.winding_c > winding_limit_c) | (
            self.core_c > core_limit_c
        )
        return float(np.mean(failures))

    def describe(self, winding_limit_c: float, core_limit_c: float) -> str:
        w_hi, c_hi = self.worst_case()
        w_lo, c_lo = self.best_case()
        fraction = self.failing_fraction(winding_limit_c, core_limit_c)
        return (
            f"winding {w_lo:.0f}-{w_hi:.0f} C, core {c_lo:.0f}-{c_hi:.0f} C "
            f"across the swept boundary; {fraction:.0%} of the range exceeds a "
            f"limit"
        )


def sweep_boundary(
    copper_loss_at_20c_w: float,
    core_loss_fn: Callable[[float], float],
    ambient_range_c: Sequence[float],
    velocity_range_m_s: Sequence[float],
    characteristic_length_m: float,
    surface_area_m2: float,
    conduction_resistance_k_w: Optional[float] = None,
    winding_to_surface_k_w: float = 2.0,
    core_to_surface_k_w: float = 3.0,
) -> SensitivitySurface:
    """Solve across the boundary conditions instead of asserting one."""
    ambients = list(ambient_range_c)
    velocities = list(velocity_range_m_s)
    winding = np.zeros((len(ambients), len(velocities)))
    core = np.zeros_like(winding)

    for i, ambient in enumerate(ambients):
        for j, velocity in enumerate(velocities):
            result = solve_fixed_point(
                copper_loss_at_20c_w,
                core_loss_fn,
                CoolingBoundary(
                    ambient_c=ambient, air_velocity_m_s=velocity,
                    characteristic_length_m=characteristic_length_m,
                    surface_area_m2=surface_area_m2,
                    conduction_resistance_k_w=conduction_resistance_k_w,
                ),
                winding_to_surface_k_w, core_to_surface_k_w,
            )
            winding[i, j] = result.winding_c
            core[i, j] = result.core_c

    return SensitivitySurface(ambients, velocities, winding, core)
