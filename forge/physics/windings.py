"""Planar winding loss: skin, proximity, vias and terminations.

At the frequencies this design uses, copper thickness and skin depth are
comparable, which is the regime where proximity effect between layers
dominates and where the interleaving pattern decides the answer.

Dowell's one-dimensional model is used for screening. It assumes wide, flat,
straight conductors filling the window, with field parallel to the layers.
Planar PCB windings violate that at trace edges, corners, terminations and
around vias, so every result here is explicitly a screening estimate and the
2D field solver is expected to correct it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

MU_0 = 4.0e-7 * math.pi
RHO_CU_20C = 1.724e-8      # ohm-metre
ALPHA_CU = 3.93e-3         # per kelvin


def copper_resistivity(temperature_c: float) -> float:
    """Copper resistivity at temperature.

    Ignoring this is worth roughly 40 percent on winding loss between room
    temperature and a 125 C hotspot.
    """
    return RHO_CU_20C * (1.0 + ALPHA_CU * (temperature_c - 20.0))


def skin_depth(frequency_hz: float, temperature_c: float = 20.0) -> float:
    """delta = sqrt(rho / (pi f mu0))."""
    if frequency_hz <= 0:
        raise ValueError("frequency must be positive")
    return math.sqrt(
        copper_resistivity(temperature_c) / (math.pi * frequency_hz * MU_0)
    )


@dataclass(frozen=True)
class Layer:
    """One copper layer of a planar winding."""

    name: str
    winding: str            # 'primary', 'secondary_a', 'secondary_b'
    turns: int
    thickness_m: float
    trace_width_m: float
    mean_turn_length_m: float
    #: Layers carrying the same winding wired in parallel share this tag.
    parallel_group: Optional[str] = None

    @property
    def conductor_area_m2(self) -> float:
        return self.thickness_m * self.trace_width_m

    def dc_resistance(self, temperature_c: float = 20.0) -> float:
        return (
            copper_resistivity(temperature_c)
            * self.turns
            * self.mean_turn_length_m
            / self.conductor_area_m2
        )


def dowell_factor(
    thickness_m: float,
    frequency_hz: float,
    layer_index: int,
    porosity: float = 1.0,
    temperature_c: float = 20.0,
) -> float:
    """Dowell AC-to-DC resistance ratio for one layer.

    ``layer_index`` is the position within a portion of winding between two
    zero-MMF planes, counting from one. The (2m^2 - 1)/3 term is the proximity
    contribution and grows quadratically, which is exactly why interleaving,
    by resetting the MMF and lowering m, is the dominant design lever.
    """
    if not 0 < porosity <= 1.0:
        raise ValueError("porosity must be in (0, 1]")
    if layer_index < 1:
        raise ValueError("layer index counts from one")

    delta = skin_depth(frequency_hz, temperature_c) / math.sqrt(porosity)
    xi = thickness_m / delta
    if xi < 1e-6:
        return 1.0

    sinh2, sin2 = math.sinh(2 * xi), math.sin(2 * xi)
    cosh2, cos2 = math.cosh(2 * xi), math.cos(2 * xi)
    sinh1, sin1 = math.sinh(xi), math.sin(xi)
    cosh1, cos1 = math.cosh(xi), math.cos(xi)

    denom_a = cosh2 - cos2
    denom_b = cosh1 + cos1
    if abs(denom_a) < 1e-15 or abs(denom_b) < 1e-15:
        return 1.0

    m = float(layer_index)
    skin_term = (sinh2 + sin2) / denom_a
    prox_term = (2.0 * (m ** 2 - 1.0) / 3.0) * (sinh1 - sin1) / denom_b
    return xi * (skin_term + prox_term)


@dataclass
class WindingPortion:
    """A run of layers between two zero-MMF planes.

    Interleaving splits the winding into more portions with fewer layers each.
    Since the proximity term scales with the square of the layer count, this
    is where the loss is won or lost.
    """

    layers: List[Layer]
    porosity: float = 0.8

    def ac_resistance(
        self, frequency_hz: float, temperature_c: float = 20.0
    ) -> float:
        total = 0.0
        for index, layer in enumerate(self.layers, start=1):
            factor = dowell_factor(
                layer.thickness_m, frequency_hz, index, self.porosity,
                temperature_c,
            )
            total += layer.dc_resistance(temperature_c) * factor
        return total

    def dc_resistance(self, temperature_c: float = 20.0) -> float:
        return sum(layer.dc_resistance(temperature_c) for layer in self.layers)


@dataclass(frozen=True)
class ViaField:
    """A group of plated through-holes carrying winding current."""

    count: int
    drill_diameter_m: float
    plating_thickness_m: float
    length_m: float

    def resistance(self, temperature_c: float = 20.0) -> float:
        """Parallel resistance of the plated barrels.

        Routinely omitted from planar loss estimates, and not negligible: a
        one-turn 60 A secondary moves its entire current through these barrels.
        """
        if self.count <= 0:
            raise ValueError("via count must be positive")
        barrel_area = math.pi * self.drill_diameter_m * self.plating_thickness_m
        one = copper_resistivity(temperature_c) * self.length_m / barrel_area
        return one / self.count

    def current_density(self, current_a: float) -> float:
        barrel_area = math.pi * self.drill_diameter_m * self.plating_thickness_m
        return current_a / (self.count * barrel_area)


@dataclass
class HarmonicSpectrum:
    """Winding current decomposed into harmonics of the switching frequency."""

    fundamental_hz: float
    #: harmonic order -> RMS amplitude in amperes
    amplitudes: Dict[int, float] = field(default_factory=dict)

    @staticmethod
    def from_waveform(
        time_s: np.ndarray, current_a: np.ndarray, max_harmonic: int = 15
    ) -> "HarmonicSpectrum":
        if time_s.shape != current_a.shape:
            raise ValueError("time and current must have the same shape")
        period = float(time_s[-1] - time_s[0])
        if period <= 0:
            raise ValueError("waveform must span a positive period")
        samples = current_a[:-1]
        spectrum = np.fft.rfft(samples) / samples.size
        amplitudes: Dict[int, float] = {}
        for order in range(1, min(max_harmonic, spectrum.size - 1) + 1):
            amplitudes[order] = float(abs(spectrum[order]) * 2.0 / math.sqrt(2.0))
        return HarmonicSpectrum(1.0 / period, amplitudes)

    def rms(self) -> float:
        return math.sqrt(sum(a ** 2 for a in self.amplitudes.values()))

    def significant(self, threshold: float = 0.02) -> Dict[int, float]:
        """Harmonics worth solving for, relative to the fundamental."""
        if not self.amplitudes:
            return {}
        reference = max(self.amplitudes.values())
        return {
            order: amp
            for order, amp in self.amplitudes.items()
            if amp >= threshold * reference
        }


def harmonic_copper_loss(
    portion: WindingPortion,
    spectrum: HarmonicSpectrum,
    temperature_c: float = 20.0,
) -> Tuple[float, Dict[int, float]]:
    """Sum I_h^2 * R_ac(h * f_s) over the significant harmonics.

    Evaluating AC resistance only at the fundamental understates loss, because
    R_ac rises with frequency while the harmonic amplitudes fall more slowly
    than that rise for the sharp-edged components.
    """
    per_harmonic: Dict[int, float] = {}
    total = 0.0
    for order, amplitude in spectrum.significant().items():
        r_ac = portion.ac_resistance(
            spectrum.fundamental_hz * order, temperature_c
        )
        loss = amplitude ** 2 * r_ac
        per_harmonic[order] = loss
        total += loss
    return total, per_harmonic


def termination_resistance(
    length_m: float,
    width_m: float,
    thickness_m: float,
    temperature_c: float = 20.0,
) -> float:
    """Spreading resistance of a copper termination pad."""
    if min(length_m, width_m, thickness_m) <= 0:
        raise ValueError("termination dimensions must be positive")
    return copper_resistivity(temperature_c) * length_m / (width_m * thickness_m)


@dataclass
class WindingLossBreakdown:
    """Where the copper loss actually goes, kept separable on purpose."""

    primary_w: float
    secondary_w: float
    via_w: float
    termination_w: float

    @property
    def total_w(self) -> float:
        return self.primary_w + self.secondary_w + self.via_w + self.termination_w

    def shares(self) -> Dict[str, float]:
        total = self.total_w
        if total <= 0:
            return {}
        return {
            "primary": self.primary_w / total,
            "secondary": self.secondary_w / total,
            "vias": self.via_w / total,
            "terminations": self.termination_w / total,
        }
