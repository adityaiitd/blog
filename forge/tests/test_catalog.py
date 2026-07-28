"""Tests for core-loss fitting and the component catalog."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from forge.data.catalog import Catalog  # noqa: E402
from forge.physics.coreloss import (  # noqa: E402
    CoreLossError,
    DomainError,
    LossPoint,
    MaterialLossModel,
    fit_steinmetz,
    igse_pv,
)


class SteinmetzFitTest(unittest.TestCase):
    def test_recovers_known_coefficients(self):
        k, alpha, beta = 1e-5, 1.9, 2.4
        points = [
            LossPoint(f, b, 100.0, k * f ** alpha * b ** beta)
            for f in (300e3, 1e6)
            for b in (0.02, 0.05, 0.1)
        ]
        fit = fit_steinmetz(points)
        self.assertAlmostEqual(fit.alpha, alpha, places=6)
        self.assertAlmostEqual(fit.beta, beta, places=6)
        self.assertAlmostEqual(fit.k, k, delta=k * 1e-6)
        self.assertLess(fit.max_residual, 1e-9)

    def test_single_frequency_requires_explicit_alpha(self):
        points = [
            LossPoint(500e3, 0.05, 100.0, 90e3),
            LossPoint(500e3, 0.10, 100.0, 700e3),
        ]
        with self.assertRaises(CoreLossError):
            fit_steinmetz(points)
        fit = fit_steinmetz(points, assumed_alpha=1.85)
        self.assertTrue(fit.alpha_assumed)
        # beta from two points at one frequency is exact.
        self.assertAlmostEqual(fit.beta, math.log(700 / 90) / math.log(2), places=6)

    def test_mixed_temperatures_rejected(self):
        with self.assertRaises(CoreLossError):
            fit_steinmetz([
                LossPoint(500e3, 0.05, 25.0, 100e3),
                LossPoint(500e3, 0.10, 100.0, 700e3),
            ])

    def test_domain_is_enforced(self):
        fit = fit_steinmetz([
            LossPoint(1e6, 0.05, 100.0, 150e3),
            LossPoint(3e6, 0.01, 100.0, 50e3),
            LossPoint(3e6, 0.03, 100.0, 500e3),
        ])
        fit.pv(2e6, 0.02)
        with self.assertRaises(DomainError):
            fit.pv(500e3, 0.02)
        with self.assertRaises(DomainError):
            fit.pv(2e6, 0.2)
        self.assertGreater(fit.pv(500e3, 0.02, allow_extrapolation=True), 0.0)


class IgseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fit = fit_steinmetz([
            LossPoint(1e6, 0.05, 100.0, 150e3),
            LossPoint(3e6, 0.01, 100.0, 50e3),
            LossPoint(3e6, 0.03, 100.0, 500e3),
        ])

    def test_sinusoid_reproduces_the_steinmetz_value(self):
        """iGSE must collapse to the sinusoidal fit for a sine wave."""
        f, b_peak = 1e6, 0.03
        t = np.linspace(0.0, 1.0 / f, 4001)
        b = b_peak * np.sin(2 * math.pi * f * t)
        self.assertAlmostEqual(
            igse_pv(self.fit, t, b) / self.fit.pv(f, b_peak), 1.0, delta=0.02
        )

    def test_triangular_flux_loses_less_than_sinusoidal(self):
        """At equal peak flux a triangle is gentler than a sine.

        A sinusoid slews at 2*pi*f*Bp at the zero crossing; a triangle of the
        same amplitude and period slews at a constant 4*f*Bp, about 36 percent
        lower. Since iGSE weights |dB/dt|^alpha with alpha above one, the
        triangle costs less. This is why applying a sinusoidal datasheet figure
        to a square-driven magnetic overstates its loss.
        """
        f, b_peak = 1e6, 0.03
        t = np.linspace(0.0, 1.0 / f, 4001)
        sine = b_peak * np.sin(2 * math.pi * f * t)
        tri = b_peak * (2.0 / math.pi) * np.arcsin(np.sin(2 * math.pi * f * t))
        self.assertLess(igse_pv(self.fit, t, tri), igse_pv(self.fit, t, sine))

    def test_asymmetric_flux_costs_more_than_symmetric(self):
        """Duty asymmetry is what iGSE exists to capture.

        Same peak flux, same frequency, but one edge is compressed into a
        fifth of the period. A plain Steinmetz evaluation cannot see this.
        """
        f, b_peak, period = 1e6, 0.03, 1e-6
        t = np.linspace(0.0, period, 6001)

        def asymmetric(duty: float) -> np.ndarray:
            phase = (t / period) % 1.0
            rising = phase < duty
            out = np.empty_like(phase)
            out[rising] = -b_peak + 2 * b_peak * phase[rising] / duty
            out[~rising] = b_peak - 2 * b_peak * (phase[~rising] - duty) / (
                1.0 - duty
            )
            return out

        self.assertGreater(
            igse_pv(self.fit, t, asymmetric(0.2)),
            igse_pv(self.fit, t, asymmetric(0.5)),
        )

    def test_flat_flux_is_lossless(self):
        t = np.linspace(0.0, 1e-6, 100)
        self.assertEqual(igse_pv(self.fit, t, np.zeros_like(t)), 0.0)


class MaterialModelTest(unittest.TestCase):
    def model(self) -> MaterialLossModel:
        fit = fit_steinmetz([
            LossPoint(1e6, 0.05, 100.0, 150e3),
            LossPoint(3e6, 0.01, 100.0, 50e3),
            LossPoint(3e6, 0.03, 100.0, 500e3),
        ])
        return MaterialLossModel(
            material="3F46", manufacturer="Ferroxcube", density_kg_m3=4750.0,
            b_sat_25c_t=0.52, b_sat_100c_t=0.43, curie_c=280.0,
            resistivity_ohm_m=5.0, mu_i=750.0, fits={100.0: fit},
            intended_band_hz=(1e6, 3e6),
        )

    def test_far_temperature_refused(self):
        with self.assertRaises(DomainError):
            self.model().pv(1e6, 0.03, temperature_c=25.0)

    def test_saturation_falls_with_temperature(self):
        m = self.model()
        self.assertGreater(m.b_sat_at(25.0), m.b_sat_at(100.0))
        self.assertAlmostEqual(m.b_sat_at(62.5), (0.52 + 0.43) / 2, places=4)

    def test_bounds_bracket_the_nominal(self):
        lo, nom, hi = self.model().pv_with_bounds(1e6, 0.03)
        self.assertLess(lo, nom)
        self.assertLess(nom, hi)

    def test_band_check(self):
        m = self.model()
        self.assertTrue(m.suits_frequency(1.5e6))
        self.assertFalse(m.suits_frequency(300e3))


class CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = Catalog()

    def test_catalog_is_populated(self):
        summary = self.catalog.summary()
        self.assertGreaterEqual(summary["cores"], 6)
        self.assertGreaterEqual(summary["devices"], 2)

    def test_height_filter_is_restrictive(self):
        """Only very low cores survive the 8 mm converter height."""
        tall = self.catalog.cores()
        short = self.catalog.cores(max_height_mm=8.0)
        self.assertLess(len(short), len(tall))
        self.assertTrue(all(c.height_mm <= 8.0 for c in short))

    def test_3f46_fit_reproduces_its_datasheet_point(self):
        material = self.catalog.material("3F46")
        self.assertAlmostEqual(
            material.pv(1e6, 0.05, 100.0) / 150e3, 1.0, delta=0.01
        )

    def test_uncharacterised_material_refuses_to_load(self):
        with self.assertRaises(KeyError) as ctx:
            self.catalog.material("ML95S")
        self.assertIn("no usable loss data", str(ctx.exception))

    def test_dmr51_attributed_to_dmegc(self):
        row = self.catalog.connection.execute(
            "SELECT manufacturer FROM materials WHERE name = 'DMR51'"
        ).fetchone()
        self.assertIn("DMEGC", row["manufacturer"])

    def test_core_unit_conversions(self):
        core = self.catalog.cores()[0]
        self.assertAlmostEqual(core.ae_m2, core.ae_mm2 * 1e-6)
        self.assertAlmostEqual(core.le_m, core.le_mm * 1e-3)

    def test_copper_thickness_matches_ipc_nominal(self):
        self.assertAlmostEqual(self.catalog.copper_thickness_um(2.0), 69.6)

    def test_qoss_scaling_needs_a_reference(self):
        device = self.catalog.device("EPC2366")
        self.assertGreater(device.q_oss_scaled(20.0), device.q_oss_nc)


if __name__ == "__main__":
    unittest.main()
