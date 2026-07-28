"""Tests for benchmark pre-registration, release gates and hardware scoring."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from forge.verify.benchmarks import (  # noqa: E402
    BENCHMARKS,
    Role,
    build_protocol,
    compare,
)
from forge.verify.gates import (  # noqa: E402
    ClaimError,
    GateRecord,
    GateReport,
    GateState,
    ReleaseLevel,
    assert_claim_allowed,
)
from forge.verify.hardware import (  # noqa: E402
    HardwareError,
    Measurement,
    load_criteria,
    score,
)


class BenchmarkProtocolTest(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = build_protocol()

    def test_hash_changes_if_a_tolerance_is_edited(self):
        """Pre-registration only means something if edits are detectable."""
        before = self.protocol.content_hash()
        self.protocol.benchmarks[0].observables[0].__dict__  # frozen dataclass
        widened = build_protocol()
        widened.rules.append("tolerances widened after the fact")
        self.assertNotEqual(before, widened.content_hash())

    def test_calibration_and_holdout_are_disjoint(self):
        overlap = set(self.protocol.calibration_allowed_against) & set(
            self.protocol.holdout)
        self.assertEqual(overlap, set())

    def test_no_benchmark_claims_to_validate(self):
        for bench in self.protocol.benchmarks:
            self.assertTrue(bench.why_it_cannot_validate)
            self.assertNotEqual(bench.role, "validation")

    def test_unregistered_observable_is_refused(self):
        """Adding an observable after seeing results would defeat the protocol."""
        bench = BENCHMARKS[0]
        with self.assertRaises(KeyError):
            compare(bench, "some_observable_invented_later", 1.0, 1.0)

    def test_absolute_and_relative_bands_both_work(self):
        bench = next(b for b in BENCHMARKS if b.key == "epc_isop")
        near = compare(bench, "converter_efficiency_full_load", 0.972, 0.970)
        self.assertTrue(near.within_band)
        far = compare(bench, "converter_efficiency_full_load", 0.930, 0.970)
        self.assertFalse(far.within_band)

    def test_unpublished_quantity_is_unscored_not_passed(self):
        bench = BENCHMARKS[0]
        result = compare(bench, "converter_efficiency", 0.98, None)
        self.assertFalse(result.scored)
        self.assertIsNone(result.within_band)

    def test_protocol_saves_with_a_hash(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            path = self.protocol.save(Path(tmp) / "p.json")
            self.assertIn("content_hash", json.loads(path.read_text()))


class GateTest(unittest.TestCase):
    def full_report(self, state=GateState.PASS.value) -> GateReport:
        from forge.verify.gates import MANDATORY_GATES
        report = GateReport()
        for key, title, safety in MANDATORY_GATES:
            report.add(GateRecord(key, title, state, "checked",
                                  safety_critical=safety))
        return report

    def test_unevaluated_gate_blocks_exactly_like_a_failure(self):
        """'We did not check' is not the same claim as 'we checked'."""
        report = GateReport()
        report.add(GateRecord("requirements", "Requirements",
                              GateState.PASS.value, "ok"))
        self.assertEqual(report.level(), ReleaseLevel.RESEARCH_REPORT)
        self.assertIn("never evaluated", report.refusal_reason())
        self.assertFalse(report.may_release_manufacturing_files())

    def test_all_passing_reaches_candidate_but_no_further(self):
        report = self.full_report()
        self.assertEqual(report.level(), ReleaseLevel.CANDIDATE_PACKAGE)
        self.assertTrue(report.may_release_manufacturing_files())
        self.assertNotEqual(report.level(), ReleaseLevel.VALIDATED)

    def test_unverified_state_blocks_release(self):
        report = self.full_report()
        report.get("thermal").state = GateState.UNVERIFIED.value
        self.assertFalse(report.may_release_manufacturing_files())
        self.assertIn("thermal", report.refusal_reason())

    def test_safety_gate_is_called_out_separately(self):
        report = self.full_report()
        report.get("insulation").state = GateState.FAIL.value
        self.assertTrue(report.safety_open)
        self.assertIn("safety-critical", report.refusal_reason())

    def test_non_applicable_does_not_block(self):
        report = self.full_report()
        report.get("field_2d").state = GateState.NOT_APPLICABLE.value
        self.assertTrue(report.may_release_manufacturing_files())


class ClaimTest(unittest.TestCase):
    def report(self) -> GateReport:
        return GateReport()

    def test_validated_is_refused_without_hardware(self):
        with self.assertRaises(ClaimError):
            assert_claim_allowed("a validated design", self.report())

    def test_production_ready_is_refused(self):
        with self.assertRaises(ClaimError):
            assert_claim_allowed("this is production-ready", self.report())

    def test_honest_language_is_allowed(self):
        assert_claim_allowed(
            "Simulation-backed preliminary design, not production-qualified.",
            self.report(), hardware_passed=False)

    def test_the_required_disclaimer_is_not_self_rejecting(self):
        """A naive substring check rejected this project's own disclaimer."""
        for phrase in (
            "not production-qualified",
            "This design is not validated.",
            "no part of this is proven in hardware",
            "never certified",
            "hazardous high voltage; not production qualified",
        ):
            assert_claim_allowed(phrase, self.report())

    def test_negation_does_not_hide_a_real_claim(self):
        with self.assertRaises(ClaimError):
            assert_claim_allowed(
                "Not a prototype. This is a validated production design.",
                self.report())

    def test_validated_allowed_once_hardware_passes(self):
        assert_claim_allowed("model-validated prototype", self.report(),
                             hardware_passed=True)

    def test_production_qualified_never_allowed(self):
        with self.assertRaises(ClaimError):
            assert_claim_allowed("production qualified", self.report(),
                                 hardware_passed=True)


class HardwareAcceptanceTest(unittest.TestCase):
    def test_criteria_load_with_a_hash(self):
        criteria, digest = load_criteria()
        self.assertGreaterEqual(len(criteria), 8)
        self.assertEqual(len(digest), 64)

    def test_missing_measurement_blocks_promotion(self):
        result = score({}, {})
        self.assertFalse(result.promoted)
        self.assertTrue(result.unscored)
        self.assertEqual(result.claim(), "simulation-backed preliminary design")

    def test_a_single_pass_does_not_promote(self):
        result = score(
            {"magnetising_inductance": Measurement(
                "magnetising_inductance", 0.42, 0.01, "uH")},
            {"magnetising_inductance": 0.401},
        )
        self.assertFalse(result.promoted)
        self.assertTrue(result.unscored)

    def test_out_of_band_measurement_fails(self):
        result = score(
            {"magnetising_inductance": Measurement(
                "magnetising_inductance", 0.60, 0.01, "uH")},
            {"magnetising_inductance": 0.401},
        )
        self.assertIn("magnetising_inductance", result.failed)

    def test_measurement_uncertainty_widens_the_band(self):
        tight = score(
            {"magnetising_inductance": Measurement(
                "magnetising_inductance", 0.45, 0.001, "uH")},
            {"magnetising_inductance": 0.401})
        loose = score(
            {"magnetising_inductance": Measurement(
                "magnetising_inductance", 0.45, 0.20, "uH")},
            {"magnetising_inductance": 0.401})
        self.assertIn("magnetising_inductance", tight.failed)
        self.assertNotIn("magnetising_inductance", loose.failed)

    def test_unknown_band_text_raises_rather_than_guessing(self):
        from forge.verify.hardware import Criterion, _tolerance_for
        bogus = Criterion("x", "q", "somewhere in the right ballpark", "")
        with self.assertRaises(HardwareError):
            _tolerance_for(bogus, 1.0, Measurement("x", 1.0, 0.0, ""))


if __name__ == "__main__":
    unittest.main()
