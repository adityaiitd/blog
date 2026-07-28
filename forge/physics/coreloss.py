"""Ferrite core loss: Steinmetz fitting and the improved generalized model.

Datasheets publish a handful of loss points at round conditions. Those points
are the only defensible anchor, so this module fits Steinmetz coefficients to
them, records the residual, and refuses to evaluate outside the frequency,
flux and temperature range the points came from.

The improved generalized Steinmetz equation (iGSE) extends the sinusoidal fit
to an arbitrary flux waveform:

    P_v = (1/T) * integral( k_i * |dB/dt|^alpha * (dB)^(beta-alpha) ) dt

with

    k_i = k / ( (2*pi)^(alpha-1) * integral_0^{2pi} |cos t|^alpha 2^(beta-alpha) dt )

This matters because an LLC's flux waveform is not sinusoidal, and applying a
sinusoidal figure directly understates loss. What iGSE does not do is account
for DC bias, relaxation, minor-loop history, gap fringing or the difference
between a toroid test core and a shaped one. Those live in the uncertainty
budget, not in the equation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


class CoreLossError(RuntimeError):
    pass


class DomainError(CoreLossError):
    """Raised when a loss model is asked about conditions it never saw."""


@dataclass(frozen=True)
class LossPoint:
    """One published specific-loss measurement."""

    frequency_hz: float
    b_peak_t: float
    temperature_c: float
    pv_w_m3: float
    note: str = ""


@dataclass
class SteinmetzFit:
    """P_v = k * f^alpha * B^beta, valid only over the fitted domain."""

    k: float
    alpha: float
    beta: float
    f_domain: Tuple[float, float]
    b_domain: Tuple[float, float]
    temperature_c: float
    n_points: int
    max_residual: float
    alpha_assumed: bool = False
    notes: str = ""

    def pv(
        self,
        frequency_hz: float,
        b_peak_t: float,
        allow_extrapolation: bool = False,
    ) -> float:
        if not allow_extrapolation:
            self.check_domain(frequency_hz, b_peak_t)
        return self.k * frequency_hz ** self.alpha * b_peak_t ** self.beta

    def check_domain(self, frequency_hz: float, b_peak_t: float) -> None:
        lo, hi = self.f_domain
        if not lo * 0.999 <= frequency_hz <= hi * 1.001:
            raise DomainError(
                f"loss fit covers {lo/1e3:g}-{hi/1e3:g} kHz; asked for "
                f"{frequency_hz/1e3:g} kHz"
            )
        lo, hi = self.b_domain
        if not lo * 0.999 <= b_peak_t <= hi * 1.001:
            raise DomainError(
                f"loss fit covers {lo*1e3:g}-{hi*1e3:g} mT; asked for "
                f"{b_peak_t*1e3:g} mT"
            )

    def k_i(self) -> float:
        """Waveform coefficient used by iGSE."""
        theta = np.linspace(0.0, 2.0 * math.pi, 2001)
        integrand = np.abs(np.cos(theta)) ** self.alpha * (
            2.0 ** (self.beta - self.alpha)
        )
        integral = float(np.trapezoid(integrand, theta))
        return self.k / ((2.0 * math.pi) ** (self.alpha - 1.0) * integral)


def fit_steinmetz(
    points: Sequence[LossPoint],
    assumed_alpha: Optional[float] = None,
) -> SteinmetzFit:
    """Least-squares fit of log Pv = log k + alpha log f + beta log B.

    With points at only one frequency, alpha is unidentifiable. Rather than
    invent one, the caller must supply it explicitly and the fit records that
    it was assumed.
    """
    if len(points) < 2:
        raise CoreLossError("need at least two loss points")
    temps = {p.temperature_c for p in points}
    if len(temps) != 1:
        raise CoreLossError(
            "fit one temperature at a time; ferrite loss is not monotonic in "
            f"temperature and these points span {sorted(temps)}"
        )

    log_f = np.log(np.array([p.frequency_hz for p in points]))
    log_b = np.log(np.array([p.b_peak_t for p in points]))
    log_p = np.log(np.array([p.pv_w_m3 for p in points]))
    single_frequency = float(np.ptp(log_f)) < 1e-9

    if single_frequency:
        if assumed_alpha is None:
            raise CoreLossError(
                "all points share one frequency, so alpha cannot be fitted. "
                "Supply assumed_alpha explicitly so the assumption is recorded."
            )
        design = np.column_stack([np.ones_like(log_b), log_b])
        target = log_p - assumed_alpha * log_f
        coeffs, *_ = np.linalg.lstsq(design, target, rcond=None)
        log_k, beta = float(coeffs[0]), float(coeffs[1])
        alpha = float(assumed_alpha)
    else:
        design = np.column_stack([np.ones_like(log_f), log_f, log_b])
        coeffs, *_ = np.linalg.lstsq(design, log_p, rcond=None)
        log_k, alpha, beta = (float(c) for c in coeffs)

    k = math.exp(log_k)
    predicted = k * np.exp(alpha * log_f + beta * log_b)
    actual = np.array([p.pv_w_m3 for p in points])
    residual = float(np.max(np.abs(predicted - actual) / actual))

    return SteinmetzFit(
        k=k, alpha=alpha, beta=beta,
        f_domain=(
            float(min(p.frequency_hz for p in points)),
            float(max(p.frequency_hz for p in points)),
        ),
        b_domain=(
            float(min(p.b_peak_t for p in points)),
            float(max(p.b_peak_t for p in points)),
        ),
        temperature_c=float(next(iter(temps))),
        n_points=len(points),
        max_residual=residual,
        alpha_assumed=single_frequency,
    )


def igse_pv(
    fit: SteinmetzFit,
    time_s: np.ndarray,
    b_t: np.ndarray,
    allow_extrapolation: bool = False,
) -> float:
    """Specific loss for an arbitrary periodic flux waveform, in W/m^3.

    ``time_s`` and ``b_t`` describe exactly one period.
    """
    if time_s.shape != b_t.shape:
        raise CoreLossError("time and flux arrays must have the same shape")
    if time_s.size < 8:
        raise CoreLossError("need a reasonably sampled waveform")

    period = float(time_s[-1] - time_s[0])
    if period <= 0:
        raise CoreLossError("waveform must span a positive period")

    delta_b = float(np.max(b_t) - np.min(b_t))
    if delta_b <= 0:
        return 0.0

    b_peak = delta_b / 2.0
    frequency = 1.0 / period
    if not allow_extrapolation:
        fit.check_domain(frequency, b_peak)

    dbdt = np.gradient(b_t, time_s)
    integrand = np.abs(dbdt) ** fit.alpha * delta_b ** (fit.beta - fit.alpha)
    return float(fit.k_i() * np.trapezoid(integrand, time_s) / period)


@dataclass
class MaterialLossModel:
    """A named material with its fits and the uncertainty that travels along."""

    material: str
    manufacturer: str
    density_kg_m3: float
    b_sat_25c_t: float
    b_sat_100c_t: float
    curie_c: float
    resistivity_ohm_m: float
    mu_i: float
    fits: Dict[float, SteinmetzFit] = field(default_factory=dict)
    #: Relative uncertainty on any loss prediction from this model.
    relative_uncertainty: float = 0.25
    intended_band_hz: Tuple[float, float] = (0.0, math.inf)
    source_key: str = ""
    notes: str = ""

    def fit_at(self, temperature_c: float) -> SteinmetzFit:
        if not self.fits:
            raise CoreLossError(f"{self.material} has no loss fit")
        nearest = min(self.fits, key=lambda t: abs(t - temperature_c))
        if abs(nearest - temperature_c) > 25.0:
            raise DomainError(
                f"{self.material} loss is characterised at "
                f"{sorted(self.fits)} C; asked for {temperature_c} C. Ferrite "
                "loss varies non-monotonically with temperature, so this is "
                "not safe to interpolate."
            )
        return self.fits[nearest]

    def pv(
        self,
        frequency_hz: float,
        b_peak_t: float,
        temperature_c: float = 100.0,
        allow_extrapolation: bool = False,
    ) -> float:
        return self.fit_at(temperature_c).pv(
            frequency_hz, b_peak_t, allow_extrapolation
        )

    def pv_with_bounds(
        self,
        frequency_hz: float,
        b_peak_t: float,
        temperature_c: float = 100.0,
        allow_extrapolation: bool = False,
    ) -> Tuple[float, float, float]:
        nominal = self.pv(
            frequency_hz, b_peak_t, temperature_c, allow_extrapolation
        )
        spread = nominal * self.relative_uncertainty
        return nominal - spread, nominal, nominal + spread

    def b_sat_at(self, temperature_c: float) -> float:
        """Linear interpolation between the two published saturation points."""
        t0, t1 = 25.0, 100.0
        b0, b1 = self.b_sat_25c_t, self.b_sat_100c_t
        if temperature_c <= t0:
            return b0
        if temperature_c >= t1:
            # Beyond 100 C saturation keeps falling toward the Curie point;
            # extrapolating linearly is conservative but not physical, so cap.
            return b1
        return b0 + (b1 - b0) * (temperature_c - t0) / (t1 - t0)

    def suits_frequency(self, frequency_hz: float) -> bool:
        lo, hi = self.intended_band_hz
        return lo <= frequency_hz <= hi
