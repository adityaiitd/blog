"""Tests for the circuit verification hierarchy."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from forge.verify.spice import (  # noqa: E402
    SpiceError,
    _parse_print,
    analyse_faults,
    check_gain,
    ngspice_available,
    simulate_sharing,
    simulate_zvs,
)

TANK = dict(l_r_h=0.0668e-6, l_m_h=0.401e-6, c_r_f=93.85e-9, n=4.0)
needs_spice = unittest.skipUnless(ngspice_available(), "ngspice not installed")


class ParseTest(unittest.TestCase):
    def test_parses_an_ngspice_table(self):
        text = """
Index   frequency       vm(tank)
--------------------------------------------------------------------------------
0\t5.000000e+05\t6.477736e-01
1\t8.944272e+05\t2.905787e+00
"""
        columns = _parse_print(text)
        self.assertEqual(len(columns["frequency"]), 2)
        self.assertAlmostEqual(columns["vm(tank)"][1], 2.905787)

    def test_ignores_noise(self):
        self.assertEqual(_parse_print("no table here at all"), {})


@needs_spice
class GainTest(unittest.TestCase):
    def test_spice_agrees_with_the_analytic_model(self):
        """Both describe the same linear network, so they must match."""
        result = check_gain(r_load_ohm=12.5 / 60, **TANK)
        self.assertTrue(result.agrees, result.describe())
        self.assertLess(result.max_relative_error, 0.01)

    def test_sweep_actually_returned_points(self):
        # ngspice "dec" counts points per decade, and this span is about half
        # a decade wide.
        result = check_gain(r_load_ohm=12.5 / 60, points=20, **TANK)
        self.assertGreater(len(result.frequencies_hz), 5)


@needs_spice
class ZvsTest(unittest.TestCase):
    def sim(self, deadtime_s=20e-9, c_oss_f=1.2e-9):
        return simulate_zvs(
            v_cell_v=100.0, v_out_v=12.5, i_out_a=60.0,
            deadtime_s=deadtime_s, c_oss_f=c_oss_f, frequency_hz=2e6, **TANK
        )

    def test_node_is_clamped_not_ringing_to_absurdity(self):
        """Without reverse-conduction clamps the node swung to -97 V."""
        result = self.sim()
        self.assertGreater(result.switch_node_at_turn_on_v, -5.0)

    def test_measured_at_turn_on_not_at_the_window_minimum(self):
        """The low side grounds this node every cycle.

        Taking the minimum over the window would report ~0 V for any design,
        making the check meaningless. A deliberately hopeless case must fail.
        """
        hopeless = self.sim(deadtime_s=1e-9, c_oss_f=500e-9)
        self.assertGreater(hopeless.switch_node_at_turn_on_v, 10.0)

    def test_zvs_predicted_at_the_design_point(self):
        result = self.sim()
        self.assertTrue(result.achieved, result.describe())

    def test_surplus_charge_is_reported_as_an_opportunity(self):
        result = self.sim()
        self.assertIn("optimistic", result.note)

    def test_huge_node_capacitance_defeats_zvs(self):
        """A node too heavy to swing in the dead time must fail."""
        result = self.sim(deadtime_s=2e-9, c_oss_f=100e-9)
        self.assertFalse(result.achieved)
        self.assertGreater(result.residual_volts, 0.0)


@needs_spice
class SharingTest(unittest.TestCase):
    def test_matched_cells_divide_evenly(self):
        result = simulate_sharing(800.0, 8, [10e-6] * 8, [1 / 50.0] * 8, 120.0)
        for voltage in result.cell_voltages:
            self.assertAlmostEqual(voltage, 100.0, places=3)
        self.assertLess(result.spread, 1e-6)

    def test_load_mismatch_makes_the_division_uneven(self):
        """The claim that an ISOP stack balances itself needs this test."""
        conductances = [1 / 50.0 * (1 + 0.10 * ((i % 3) - 1)) for i in range(8)]
        result = simulate_sharing(800.0, 8, [10e-6] * 8, conductances, 120.0)
        self.assertGreater(result.spread, 0.10)
        self.assertAlmostEqual(sum(result.cell_voltages), 800.0, places=2)

    def test_voltages_always_sum_to_the_bus(self):
        conductances = [1 / 50.0 * (1 + 0.2 * i / 8) for i in range(8)]
        result = simulate_sharing(800.0, 8, [10e-6] * 8, conductances, 120.0)
        self.assertAlmostEqual(sum(result.cell_voltages), 800.0, places=2)

    def test_wrong_argument_lengths_rejected(self):
        with self.assertRaises(SpiceError):
            simulate_sharing(800.0, 8, [10e-6] * 3, [1 / 50.0] * 8, 120.0)


class FaultTest(unittest.TestCase):
    def test_healthy_stack_is_within_rating(self):
        healthy = analyse_faults(800.0, 8, 150.0)[0]
        self.assertAlmostEqual(healthy.voltage_per_survivor, 100.0)
        self.assertTrue(healthy.within_rating)

    def test_losing_two_cells_exceeds_the_derated_rating(self):
        """The finding that matters: 133 V per survivor against a 120 V limit."""
        faults = {f.scenario: f for f in analyse_faults(800.0, 8, 150.0)}
        two = faults["two cells stop drawing power"]
        self.assertAlmostEqual(two.voltage_per_survivor, 800.0 / 6)
        self.assertFalse(two.within_rating)
        self.assertLess(two.margin, 0.0)

    def test_shorted_cell_is_as_bad_as_a_lost_one(self):
        faults = {f.scenario: f for f in analyse_faults(800.0, 8, 150.0)}
        self.assertAlmostEqual(
            faults["one cell input shorted"].voltage_per_survivor,
            faults["one cell stops drawing power"].voltage_per_survivor,
        )

    def test_derating_changes_the_verdict(self):
        strict = analyse_faults(800.0, 8, 150.0, derating=0.6)
        self.assertFalse(strict[1].within_rating)
        loose = analyse_faults(800.0, 8, 150.0, derating=1.0)
        self.assertTrue(loose[1].within_rating)


if __name__ == "__main__":
    unittest.main()
