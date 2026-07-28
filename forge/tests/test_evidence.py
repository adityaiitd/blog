"""Tests for the evidence register's enforcement rules."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from forge.evidence import (  # noqa: E402
    EvidenceError,
    EvidenceRegister,
    ExtractionMethod,
    Fact,
    Locator,
    RedistributionError,
    Source,
    Uncertainty,
    ValueClass,
)
from forge.evidence import licenses  # noqa: E402
from forge.evidence.extract import DigitizedCurve  # noqa: E402
from forge.evidence.register import DomainError  # noqa: E402


class RegisterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.reg = EvidenceRegister(Path(self.tmp.name) / "evidence.sqlite")
        self.reg.add_source(
            Source(
                key="tdk_n49",
                url="https://example.invalid/n49.pdf",
                owner="TDK Electronics AG",
                title="Ferrite material N49",
                license_id="tdk-datasheet",
                revision="2023-05",
            )
        )

    def tearDown(self) -> None:
        self.reg.close()
        self.tmp.cleanup()

    def test_sourced_fact_requires_existing_source(self):
        with self.assertRaises(EvidenceError):
            self.reg.add_fact(
                Fact(key="x", value=1.0, value_class=ValueClass.SOURCED.value,
                     source_key="does_not_exist")
            )

    def test_sourced_fact_requires_a_source_at_all(self):
        with self.assertRaises(EvidenceError):
            self.reg.add_fact(
                Fact(key="x", value=1.0, value_class=ValueClass.SOURCED.value)
            )

    def test_assumed_fact_may_stand_alone(self):
        self.reg.add_fact(
            Fact(key="assumed.airflow", value=2.0, unit="m/s",
                 value_class=ValueClass.ASSUMED.value,
                 notes="project assumption pending thermal boundary")
        )
        self.assertEqual(self.reg.value("assumed.airflow"), 2.0)

    def test_missing_fact_is_an_error_not_a_default(self):
        with self.assertRaises(EvidenceError):
            self.reg.require("never.recorded")

    def test_domain_rejects_extrapolation(self):
        self.reg.add_fact(
            Fact(
                key="n49.loss", value=100.0, unit="kW/m3",
                value_class=ValueClass.SOURCED.value, source_key="tdk_n49",
                extraction_method=ExtractionMethod.CURVE_DIGITIZED.value,
                domain={"f_hz": (100e3, 1e6), "b_t": (0.01, 0.2)},
            )
        )
        self.reg.require("n49.loss", f_hz=500e3, b_t=0.05)
        with self.assertRaises(DomainError):
            self.reg.require("n49.loss", f_hz=3e6)
        with self.assertRaises(DomainError):
            self.reg.require("n49.loss", b_t=0.5)

    def test_publication_blocked_for_licensed_standard(self):
        self.reg.add_source(
            Source(key="iec62368", url="https://example.invalid/iec",
                   owner="IEC", title="IEC 62368-1",
                   license_id="iec-standard")
        )
        self.reg.add_fact(
            Fact(key="iec.creepage", value=2.5, unit="mm",
                 value_class=ValueClass.SOURCED.value, source_key="iec62368")
        )
        with self.assertRaises(RedistributionError):
            self.reg.assert_publishable("iec.creepage")
        audit = self.reg.publication_audit()
        self.assertIn("iec-standard", audit)

    def test_derived_values_from_datasheet_are_publishable(self):
        self.reg.add_fact(
            Fact(key="n49.ae", value=97.1, unit="mm2",
                 value_class=ValueClass.SOURCED.value, source_key="tdk_n49")
        )
        self.reg.assert_publishable("n49.ae")

    def test_unknown_licence_is_rejected_at_source_creation(self):
        with self.assertRaises(EvidenceError):
            self.reg.add_source(
                Source(key="mystery", url="u", owner="o", title="t",
                       license_id="not-registered")
            )

    def test_unknown_policy_is_maximally_restrictive(self):
        policy = licenses.get("no-such-licence")
        self.assertFalse(policy.redistribute_source)
        self.assertFalse(policy.redistribute_excerpt)
        self.assertFalse(policy.publish_derived_values)

    def test_provenance_table_reports_class_and_locator(self):
        self.reg.add_fact(
            Fact(key="n49.bsat", value=0.49, unit="T",
                 value_class=ValueClass.SOURCED.value, source_key="tdk_n49",
                 locator=Locator(page=2, table="1"))
        )
        rows = {r["fact"]: r for r in self.reg.provenance_table()}
        self.assertEqual(rows["n49.bsat"]["class"], "sourced")
        self.assertIn("p.2", rows["n49.bsat"]["locator"])


class UncertaintyTest(unittest.TestCase):
    def test_relative_bounds(self):
        unc = Uncertainty(kind="relative", value=0.1)
        lo, hi = unc.bounds(100.0)
        self.assertAlmostEqual(lo, 90.0)
        self.assertAlmostEqual(hi, 110.0)
        self.assertAlmostEqual(unc.relative_to(100.0), 0.1)

    def test_absolute_bounds(self):
        unc = Uncertainty(kind="absolute", value=5.0)
        self.assertEqual(unc.bounds(20.0), (15.0, 25.0))

    def test_interval_requires_endpoints(self):
        with self.assertRaises(EvidenceError):
            Uncertainty(kind="interval").bounds(1.0)


class DigitizedCurveTest(unittest.TestCase):
    def make(self) -> DigitizedCurve:
        return DigitizedCurve(
            name="N49 loss at 100 C",
            x=[100e3, 300e3, 1e6],
            y=[50.0, 300.0, 1500.0],
            x_unit="Hz", y_unit="kW/m3",
        )

    def test_log_log_interpolation_is_monotone(self):
        curve = self.make()
        mid = curve.interpolate(500e3)
        self.assertGreater(mid, 300.0)
        self.assertLess(mid, 1500.0)

    def test_extrapolation_rejected_by_default(self):
        curve = self.make()
        with self.assertRaises(EvidenceError):
            curve.interpolate(2e6)
        self.assertGreater(curve.interpolate(2e6, allow_extrapolation=True), 0)

    def test_uncertainty_travels_with_the_curve(self):
        curve = self.make()
        self.assertGreater(curve.uncertainty().value, 0.0)
        self.assertIn("digitization", curve.uncertainty().basis)

    def test_round_trip_json(self):
        curve = self.make()
        again = DigitizedCurve.from_json(curve.to_json())
        self.assertEqual(again.x, curve.x)
        self.assertEqual(again.name, curve.name)

    def test_non_monotone_x_rejected(self):
        with self.assertRaises(EvidenceError):
            DigitizedCurve(name="bad", x=[2.0, 1.0], y=[1.0, 2.0],
                           x_unit="Hz", y_unit="W")


if __name__ == "__main__":
    unittest.main()
