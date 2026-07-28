"""Tests for the LLC tank, winding loss, capacitance and thermal models."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from forge.physics import capacitance as cap  # noqa: E402
from forge.physics import llc, thermal  # noqa: E402
from forge.physics import windings as wind  # noqa: E402


def make_tank(l_r=1.2e-6, l_m=7.2e-6, f_r=1e6, n=4.0) -> llc.TankParameters:
    c_r = llc.resonant_capacitor_for(l_r, f_r)
    return llc.TankParameters(l_r_h=l_r, l_m_h=l_m, c_r_f=c_r, n=n)


class TankTest(unittest.TestCase):
    def test_resonant_frequency_round_trips(self):
        tank = make_tank(f_r=1e6)
        self.assertAlmostEqual(tank.f_r_hz / 1e6, 1.0, places=6)

    def test_unity_gain_at_resonance(self):
        """The defining property of a DCX: M = 1 at f_r, at any load."""
        tank = make_tank()
        for r_load in (0.05, 0.2, 1.0, 5.0):
            self.assertAlmostEqual(
                llc.fha_gain(tank, tank.f_r_hz, r_load), 1.0, places=9
            )

    def test_output_voltage_matches_the_epc_operating_point(self):
        """100 V in, 4:1:1, half bridge at resonance gives 12.5 V."""
        tank = make_tank(n=4.0)
        r_load = 12.5 / 60.0
        self.assertAlmostEqual(
            llc.output_voltage(tank, 100.0, tank.f_r_hz, r_load), 12.5, places=6
        )

    def test_gain_falls_above_resonance(self):
        tank = make_tank()
        r_load = 12.5 / 60.0
        above = llc.fha_gain(tank, tank.f_r_hz * 1.2, r_load)
        self.assertLess(above, 1.0)

    def test_lm_must_exceed_lr(self):
        with self.assertRaises(llc.LLCError):
            llc.TankParameters(l_r_h=5e-6, l_m_h=1e-6, c_r_f=1e-9, n=4.0)

    def test_second_resonance_is_below_the_first(self):
        tank = make_tank()
        self.assertLess(tank.f_r2_hz, tank.f_r_hz)


class OperatingPointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tank = make_tank()
        self.op = llc.operating_point(self.tank, 100.0, 12.5, 60.0)

    def test_secondary_peak_from_rectified_average(self):
        """A rectified sinusoid averaging 60 A has a peak of pi*60/2."""
        self.assertAlmostEqual(
            self.op.i_resonant_peak_a * self.tank.n, math.pi * 60.0 / 2.0
        )

    def test_primary_rms_combines_in_quadrature(self):
        res = self.op.i_resonant_peak_a / math.sqrt(2)
        mag = self.op.i_magnetizing_peak_a / math.sqrt(3)
        self.assertAlmostEqual(self.op.i_primary_rms_a, math.hypot(res, mag))
        # Quadrature addition must be below a naive sum.
        self.assertLess(self.op.i_primary_rms_a, res + mag)

    def test_only_magnetizing_current_is_available_at_switching(self):
        """At resonance the resonant component is zero when the switch turns off."""
        self.assertAlmostEqual(
            self.op.i_tank_at_switching_a, self.op.i_magnetizing_peak_a
        )

    def test_magnetizing_current_scales_inversely_with_lm(self):
        small_lm = llc.operating_point(
            make_tank(l_m=3.6e-6), 100.0, 12.5, 60.0
        )
        self.assertGreater(
            small_lm.i_magnetizing_peak_a, self.op.i_magnetizing_peak_a
        )


class ZvsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tank = make_tank()
        self.op = llc.operating_point(self.tank, 100.0, 12.5, 60.0)

    def test_ideal_tank_alone_does_not_prove_zvs(self):
        """With realistic device charge the same tank can fail."""
        generous = llc.zvs_charge(
            self.tank, self.op, q_oss_total_c=1e-12, c_stray_f=0.0,
            deadtime_s=20e-9, v_cell_v=100.0,
        )
        realistic = llc.zvs_charge(
            self.tank, self.op, q_oss_total_c=244e-9, c_stray_f=30e-12,
            deadtime_s=20e-9, v_cell_v=100.0,
        )
        self.assertTrue(generous.achieved)
        self.assertFalse(realistic.achieved)

    def test_limiting_lm_is_self_consistent(self):
        """A tank built at exactly the limiting Lm should sit on the boundary."""
        result = llc.zvs_charge(
            self.tank, self.op, q_oss_total_c=20e-9, c_stray_f=30e-12,
            deadtime_s=20e-9, v_cell_v=100.0,
        )
        boundary_tank = make_tank(l_m=result.limiting_lm_h)
        boundary_op = llc.operating_point(boundary_tank, 100.0, 12.5, 60.0)
        boundary = llc.zvs_charge(
            boundary_tank, boundary_op, q_oss_total_c=20e-9, c_stray_f=30e-12,
            deadtime_s=20e-9, v_cell_v=100.0,
        )
        self.assertAlmostEqual(boundary.margin, 0.0, places=6)

    def test_longer_deadtime_helps(self):
        short = llc.zvs_charge(self.tank, self.op, 20e-9, 30e-12, 10e-9, 100.0)
        long = llc.zvs_charge(self.tank, self.op, 20e-9, 30e-12, 40e-9, 100.0)
        self.assertGreater(long.margin, short.margin)

    def test_language_is_predictive_not_confirmatory(self):
        result = llc.zvs_charge(self.tank, self.op, 20e-9, 30e-12, 40e-9, 100.0)
        self.assertIn("predicted", result.describe())
        self.assertIn("not a confirmation", result.notes)


class FluxTest(unittest.TestCase):
    def test_peak_flux_formula(self):
        b = llc.flux_density_peak(12.5, 4.0, 1e6, 39.5e-6, 4)
        self.assertAlmostEqual(b, 4 * 12.5 / (4 * 1e6 * 4 * 39.5e-6))

    def test_more_turns_lowers_flux(self):
        few = llc.flux_density_peak(12.5, 4.0, 1e6, 39.5e-6, 4)
        many = llc.flux_density_peak(12.5, 4.0, 1e6, 39.5e-6, 8)
        self.assertAlmostEqual(few / many, 2.0)

    def test_waveform_is_triangular_and_matches_the_peak(self):
        t, b = llc.flux_waveform(12.5, 4.0, 1e6, 39.5e-6, 4)
        expected = llc.flux_density_peak(12.5, 4.0, 1e6, 39.5e-6, 4)
        self.assertAlmostEqual(float(np.max(b)), expected, places=9)
        self.assertAlmostEqual(float(np.min(b)), -expected, places=9)
        # The sample grid repeats the period endpoint, so the naive mean is
        # offset by one sample's worth. Judge it against the peak instead.
        self.assertLess(abs(float(np.mean(b))), expected * 1e-2)
        # Integrating properly over the period gives a true zero mean.
        self.assertAlmostEqual(
            float(np.trapezoid(b, t)) / (t[-1] - t[0]) / expected, 0.0, places=6
        )


class SkinDepthTest(unittest.TestCase):
    def test_known_values(self):
        """Copper skin depth: about 93 um at 500 kHz and 66 um at 1 MHz."""
        self.assertAlmostEqual(wind.skin_depth(500e3) * 1e6, 93.3, delta=0.5)
        self.assertAlmostEqual(wind.skin_depth(1e6) * 1e6, 66.0, delta=0.5)

    def test_scales_as_inverse_square_root(self):
        self.assertAlmostEqual(
            wind.skin_depth(250e3) / wind.skin_depth(1e6), 2.0, places=6
        )

    def test_hot_copper_has_deeper_skin(self):
        self.assertGreater(wind.skin_depth(1e6, 125.0), wind.skin_depth(1e6, 20.0))

    def test_resistivity_rises_about_40_percent_to_125c(self):
        ratio = wind.copper_resistivity(125.0) / wind.copper_resistivity(20.0)
        self.assertAlmostEqual(ratio, 1.41, delta=0.02)


class DowellTest(unittest.TestCase):
    def test_thin_conductor_approaches_dc(self):
        factor = wind.dowell_factor(1e-6, 1e6, 1)
        self.assertAlmostEqual(factor, 1.0, delta=0.02)

    def test_proximity_penalty_grows_with_layer_count(self):
        """The reason interleaving matters.

        The proximity term carries a (2m^2 - 1)/3 factor, but the skin term
        dilutes it, so the fourth layer costs about 2.8 times the first rather
        than a full quadratic 16 times. The growth is still steep enough that
        splitting a stack into shorter portions is the dominant lever.
        """
        thickness = 70e-6
        first = wind.dowell_factor(thickness, 1e6, 1)
        second = wind.dowell_factor(thickness, 1e6, 2)
        fourth = wind.dowell_factor(thickness, 1e6, 4)
        self.assertGreater(second, first)
        self.assertGreater(fourth, second)
        self.assertGreater(fourth, first * 2.5)

    def test_two_ounce_copper_at_1mhz_costs_real_money(self):
        """70 um copper is about one skin depth at 1 MHz, so Rac/Rdc > 1."""
        self.assertGreater(wind.dowell_factor(69.6e-6, 1e6, 1), 1.05)

    def test_porosity_below_one_increases_loss(self):
        full = wind.dowell_factor(69.6e-6, 1e6, 2, porosity=1.0)
        sparse = wind.dowell_factor(69.6e-6, 1e6, 2, porosity=0.5)
        self.assertNotAlmostEqual(full, sparse)


class ViaTest(unittest.TestCase):
    def test_parallel_vias_divide_resistance(self):
        one = wind.ViaField(1, 0.2e-3, 25e-6, 1.6e-3).resistance()
        ten = wind.ViaField(10, 0.2e-3, 25e-6, 1.6e-3).resistance()
        self.assertAlmostEqual(one / ten, 10.0, places=6)

    def test_via_loss_is_not_negligible_at_60a(self):
        """A one-turn 60 A secondary moves everything through the barrels."""
        field = wind.ViaField(20, 0.2e-3, 25e-6, 1.6e-3)
        loss = 47.1 ** 2 * field.resistance(125.0)
        self.assertGreater(loss, 0.05)


class HarmonicTest(unittest.TestCase):
    def test_sine_has_a_single_harmonic(self):
        f = 1e6
        t = np.linspace(0.0, 1.0 / f, 2001)
        i = 10.0 * np.sin(2 * math.pi * f * t)
        spectrum = wind.HarmonicSpectrum.from_waveform(t, i)
        self.assertAlmostEqual(spectrum.amplitudes[1], 10.0 / math.sqrt(2),
                               delta=0.1)
        self.assertEqual(list(spectrum.significant().keys()), [1])

    def test_square_wave_carries_odd_harmonics(self):
        f = 1e6
        t = np.linspace(0.0, 1.0 / f, 4001)
        i = 10.0 * np.sign(np.sin(2 * math.pi * f * t))
        significant = wind.HarmonicSpectrum.from_waveform(t, i).significant()
        self.assertIn(3, significant)
        self.assertNotIn(2, significant)

    def test_harmonic_loss_exceeds_fundamental_only_evaluation(self):
        f = 1e6
        t = np.linspace(0.0, 1.0 / f, 4001)
        i = 10.0 * np.sign(np.sin(2 * math.pi * f * t))
        spectrum = wind.HarmonicSpectrum.from_waveform(t, i)
        layers = [
            wind.Layer(f"l{k}", "primary", 1, 69.6e-6, 3e-3, 30e-3)
            for k in range(4)
        ]
        portion = wind.WindingPortion(layers)
        total, per = wind.harmonic_copper_loss(portion, spectrum)
        self.assertGreater(total, per[1])


class CapacitanceTest(unittest.TestCase):
    def test_parallel_plate(self):
        gap = cap.DielectricGap("g", 1e-4, 0.2e-3, 4.4)
        expected = cap.EPS_0 * 4.4 * 1e-4 / 0.2e-3
        self.assertAlmostEqual(gap.capacitance_f(), expected)

    def test_thinner_dielectric_raises_capacitance(self):
        thick = cap.DielectricGap("t", 1e-4, 0.4e-3, 4.4).capacitance_f()
        thin = cap.DielectricGap("n", 1e-4, 0.2e-3, 4.4).capacitance_f()
        self.assertAlmostEqual(thin / thick, 2.0, places=6)

    def test_leakage_and_capacitance_move_oppositely(self):
        """The trade that makes interleaving a compromise rather than a win."""
        close = cap.leakage_capacitance_tradeoff(0.1e-3, 1e-4, 4.4, 4, 2e-3, 30e-3)
        far = cap.leakage_capacitance_tradeoff(0.4e-3, 1e-4, 4.4, 4, 2e-3, 30e-3)
        self.assertLess(close[0], far[0])      # leakage rises with separation
        self.assertGreater(close[1], far[1])   # capacitance falls with it

    def test_peak_rms_and_average_currents_differ_greatly(self):
        """Comparing an edge peak against an rms budget is a category error."""
        assessment = cap.assess_common_mode(
            c_ps_f=50e-12, dvdt_v_per_s=50e9, cell_count=8, budget_a=0.05,
            voltage_swing_v=100.0, frequency_hz=1e6,
        )
        self.assertAlmostEqual(assessment.i_peak_a, 2.5, places=6)
        self.assertLess(assessment.i_rms_a, assessment.i_peak_a / 10)
        self.assertLess(assessment.i_avg_a, assessment.i_rms_a)

    def test_shield_leaves_a_residual(self):
        self.assertAlmostEqual(cap.shield_effect(100e-12, 0.9), 10e-12)

    def test_coherent_stack_is_worse_than_interleaved(self):
        args = dict(c_ps_f=10e-12, dvdt_v_per_s=50e9, cell_count=8,
                    budget_a=1.0, voltage_swing_v=100.0, frequency_hz=1e6)
        coherent = cap.assess_common_mode(coherent=True, **args)
        spread = cap.assess_common_mode(coherent=False, **args)
        self.assertGreater(coherent.i_rms_stack_a, spread.i_rms_stack_a)


class ThermalTest(unittest.TestCase):
    def boundary(self, velocity=3.0, ambient=45.0, conduction=None):
        return thermal.CoolingBoundary(
            ambient_c=ambient, air_velocity_m_s=velocity,
            characteristic_length_m=0.02, surface_area_m2=3.6e-4,
            conduction_resistance_k_w=conduction,
        )

    def test_still_air_uses_a_natural_convection_floor(self):
        self.assertGreater(
            thermal.convection_coefficient(self.boundary(velocity=0.0)), 0.0
        )

    def test_more_airflow_cools_better(self):
        low = thermal.convection_coefficient(self.boundary(velocity=1.0))
        high = thermal.convection_coefficient(self.boundary(velocity=6.0))
        self.assertGreater(high, low)

    def test_fixed_point_converges_and_heats_the_copper(self):
        result = thermal.solve_fixed_point(
            copper_loss_at_20c_w=5.0, core_loss_fn=lambda t: 2.0,
            boundary=self.boundary(conduction=3.0),
        )
        self.assertTrue(result.converged)
        self.assertGreater(result.winding_c, result.boundary.ambient_c)
        # Copper loss must exceed its 20 C value once hot.
        self.assertGreater(result.copper_loss_w, 5.0)

    def test_conduction_path_dominates_a_small_footprint(self):
        """A few square centimetres cannot shed the loss by convection alone."""
        air_only = thermal.solve_fixed_point(
            5.0, lambda t: 2.0, self.boundary()
        )
        with_sink = thermal.solve_fixed_point(
            5.0, lambda t: 2.0, self.boundary(conduction=3.0)
        )
        self.assertLess(with_sink.winding_c, air_only.winding_c)

    def test_sweep_reports_a_range_not_a_point(self):
        surface = thermal.sweep_boundary(
            copper_loss_at_20c_w=5.0, core_loss_fn=lambda t: 2.0,
            ambient_range_c=[25.0, 45.0, 55.0],
            velocity_range_m_s=[1.0, 3.0, 6.0],
            characteristic_length_m=0.02, surface_area_m2=3.6e-4,
            conduction_resistance_k_w=3.0,
        )
        worst_w, _ = surface.worst_case()
        best_w, _ = surface.best_case()
        self.assertGreater(worst_w, best_w)
        self.assertIn("across the swept boundary", surface.describe(125.0, 100.0))

    def test_within_limits_requires_every_corner(self):
        surface = thermal.sweep_boundary(
            copper_loss_at_20c_w=5.0, core_loss_fn=lambda t: 2.0,
            ambient_range_c=[25.0, 55.0], velocity_range_m_s=[1.0, 6.0],
            characteristic_length_m=0.02, surface_area_m2=3.6e-4,
            conduction_resistance_k_w=3.0,
        )
        worst_w, worst_c = surface.worst_case()
        self.assertTrue(surface.within_limits(worst_w + 1, worst_c + 1))
        self.assertFalse(surface.within_limits(worst_w - 1, worst_c + 1))


if __name__ == "__main__":
    unittest.main()
