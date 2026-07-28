"""Tests for requirement scoping, coverage and the insulation basis."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from forge.requirements import (  # noqa: E402
    Category,
    Provenance,
    Requirement,
    RequirementError,
    RequirementSet,
    Scope,
    build,
    load_set,
    stack_working_voltage,
    validate,
    worst_case_working_voltage,
)
from forge.requirements.insulation import ReviewStatus, build_basis  # noqa: E402
from forge.requirements.lock import RequirementLock  # noqa: E402

REQ_DIR = Path(__file__).resolve().parents[1] / "requirements"


def _req(**kwargs) -> Requirement:
    base = dict(
        key="x.y", value=1.0, unit="V",
        scope=Scope.CONVERTER_BRIEF.value,
        category=Category.INPUT_ARCHITECTURE.value,
        provenance=Provenance.ASSUMED.value,
        rationale="a sufficiently long rationale for the test",
        sensitivity=[0.5, 1.5],
    )
    base.update(kwargs)
    return Requirement(**base)


class ScopeTest(unittest.TestCase):
    def test_cannot_add_converter_requirement_to_interface_set(self):
        rset = RequirementSet(Scope.DIABLO_INTERFACE, "iface")
        with self.assertRaises(ValueError) as ctx:
            rset.add(_req())
        self.assertIn("kept apart", str(ctx.exception))

    def test_duplicate_key_rejected(self):
        rset = RequirementSet(Scope.CONVERTER_BRIEF, "brief")
        rset.add(_req(key="a"))
        with self.assertRaises(ValueError):
            rset.add(_req(key="a"))

    def test_sourced_requirement_must_cite(self):
        with self.assertRaises(ValueError):
            _req(provenance=Provenance.SOURCED.value, source_key=None)

    def test_assumed_requirement_must_explain(self):
        with self.assertRaises(ValueError):
            _req(rationale="")


class SweepPolicyTest(unittest.TestCase):
    def test_assumed_number_without_range_is_flagged(self):
        req = _req(sensitivity=None)
        self.assertTrue(req.needs_sensitivity_sweep)

    def test_boolean_is_exempt(self):
        req = _req(value=True, sensitivity=None)
        self.assertFalse(req.needs_sensitivity_sweep)

    def test_declared_classification_is_exempt(self):
        req = _req(value=2, sensitivity=None, discrete=True)
        self.assertFalse(req.needs_sensitivity_sweep)

    def test_sourced_number_needs_no_sweep(self):
        req = _req(provenance=Provenance.SOURCED.value, source_key="s",
                   sensitivity=None)
        self.assertFalse(req.needs_sensitivity_sweep)


class ValidationTest(unittest.TestCase):
    def test_missing_mandatory_category_is_an_error(self):
        diablo = RequirementSet(Scope.DIABLO_INTERFACE, "iface")
        converter = RequirementSet(Scope.CONVERTER_BRIEF, "brief")
        converter.add(_req(key="conv.a"))
        report = validate(diablo, converter)
        self.assertFalse(report.ok)
        self.assertTrue(
            any("mandatory category" in e for e in report.errors)
        )

    def test_converter_requirement_sourced_from_diablo_is_rejected(self):
        diablo = RequirementSet(Scope.DIABLO_INTERFACE, "iface")
        converter = RequirementSet(Scope.CONVERTER_BRIEF, "brief")
        converter.add(_req(
            key="conv.stolen", provenance=Provenance.SOURCED.value,
            source_key="ocp_diablo_400_v070",
        ))
        report = validate(diablo, converter)
        self.assertTrue(
            any("specifies the rack interface, not this" in e
                for e in report.errors)
        )

    def test_lock_refuses_to_save_when_invalid(self):
        diablo = RequirementSet(Scope.DIABLO_INTERFACE, "iface")
        converter = RequirementSet(Scope.CONVERTER_BRIEF, "brief")
        report = validate(diablo, converter)
        lock = RequirementLock(diablo, converter, report)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RequirementError):
                lock.save(Path(tmp) / "lock.yaml")


class RealFilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.lock = build()

    def test_shipped_requirements_validate(self):
        errors = [
            e for e in self.lock.report.errors
            if "evidence register" not in e
        ]
        self.assertEqual(errors, [], f"unexpected errors: {errors}")

    def test_all_mandatory_categories_covered(self):
        self.assertEqual(self.lock.converter.missing_categories(), [])

    def test_interface_and_brief_are_separate_objects(self):
        self.assertNotIn("conv.v_cell_nominal", self.lock.diablo)
        self.assertNotIn("diablo.rail_voltage_full_load", self.lock.converter)

    def test_bus_envelope_arithmetic(self):
        d = self.lock.diablo
        self.assertAlmostEqual(d.value("diablo.bus_800v_full_load"), 800.0)
        self.assertAlmostEqual(d.value("diablo.bus_800v_no_load"), 820.0)
        self.assertAlmostEqual(
            d.value("diablo.bus_800v_max_steady"), 820.0 * 1.005, places=2
        )
        self.assertAlmostEqual(
            d.value("diablo.bus_800v_max_transient"), 820.0 * 1.03, places=2
        )

    def test_cell_arithmetic_is_consistent(self):
        c = self.lock.converter
        cells = c.value("conv.cell_count")
        self.assertAlmostEqual(
            c.value("conv.v_in_system_nominal") / cells,
            c.value("conv.v_cell_nominal"),
        )
        self.assertAlmostEqual(
            c.value("conv.p_out_cell") / c.value("conv.v_out_nominal"),
            c.value("conv.i_out_cell"),
        )
        self.assertAlmostEqual(
            c.value("conv.p_out_cell") * cells, c.value("conv.p_out_total")
        )

    def test_hash_changes_with_content(self):
        first = self.lock.compute_hash()
        self.lock.converter.add(_req(key="conv.extra"))
        self.assertNotEqual(first, self.lock.compute_hash())


class InsulationTest(unittest.TestCase):
    def test_top_cell_sees_the_whole_bus(self):
        self.assertAlmostEqual(stack_working_voltage(800.0, 8, 7), 800.0)
        self.assertAlmostEqual(stack_working_voltage(800.0, 8, 0), 100.0)
        self.assertAlmostEqual(worst_case_working_voltage(800.0, 8), 800.0)

    def test_cell_index_bounds_checked(self):
        with self.assertRaises(ValueError):
            stack_working_voltage(800.0, 8, 8)

    def test_basis_uses_stack_voltage_not_cell_voltage(self):
        lock = build()
        basis = build_basis(lock.converter, lock.diablo)
        # The whole point: the barrier is designed for ~845 V, not ~106 V.
        self.assertGreater(basis.working_voltage_v, 800.0)
        self.assertAlmostEqual(
            basis.working_voltage_v,
            lock.diablo.value("diablo.bus_800v_max_transient"),
            places=1,
        )
        local = basis.items["local_cell_voltage"].value
        self.assertAlmostEqual(basis.working_voltage_v / local, 8.0, places=3)

    def test_licensed_items_block_review_completion(self):
        lock = build()
        basis = build_basis(lock.converter, lock.diablo)
        self.assertFalse(basis.review_complete)
        blocking = {i.key for i in basis.blocking_items()}
        self.assertIn("creepage", blocking)
        self.assertIn("clearance", blocking)

    def test_altitude_correction_applies_only_above_2000m(self):
        lock = build()
        basis = build_basis(lock.converter, lock.diablo)
        self.assertAlmostEqual(basis.altitude_correction(1500.0), 1.0)
        self.assertGreater(basis.altitude_correction(3000.0), 1.0)


if __name__ == "__main__":
    unittest.main()
