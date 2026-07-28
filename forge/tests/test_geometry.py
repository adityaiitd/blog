"""Tests for the canonical geometry and the artifacts generated from it."""

from __future__ import annotations

import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from forge.data.catalog import Catalog  # noqa: E402
from forge.geometry.femm_writer import (  # noqa: E402
    equivalent_radius,
    unsupported_features,
    write_winding_study,
)
from forge.geometry.kicad_writer import (  # noqa: E402
    BOARD_FORMAT_VERSION,
    _racetrack_points,
    write_board,
    write_design_rules,
    write_project,
)
from forge.geometry.model import (  # noqa: E402
    CoreGeometry,
    GeometryError,
    build_planar_transformer,
    core_from_catalog,
)
from forge.geometry.peec_writer import export_geometry, write_fasthenry  # noqa: E402
from forge.verify.geometry import verify_board  # noqa: E402


def sample_core() -> CoreGeometry:
    return core_from_catalog(
        Catalog().core("ELP18/4/10withI18/2/10"), "3F46"
    )


def sample_transformer(**overrides):
    params = dict(
        name="cell", core=sample_core(), primary_turns=4, secondary_turns=1,
        turns_per_primary_layer=1, secondary_parallel=4,
        copper_thickness_m=104.4e-6, dielectric_thickness_m=0.1e-3,
        barrier_thickness_m=0.4e-3,
    )
    params.update(overrides)
    return build_planar_transformer(**params)


class CoreGeometryTest(unittest.TestCase):
    def test_post_dimensions_reproduce_the_effective_area(self):
        core = sample_core()
        self.assertAlmostEqual(
            core.post_long_m * core.post_short_m, core.ae_m2, places=12
        )

    def test_post_is_wide_not_square(self):
        """An ELP centre post spans the core width, so turns are racetracks."""
        core = sample_core()
        self.assertGreater(core.post_long_m / core.post_short_m, 2.0)

    def test_turn_length_grows_with_offset(self):
        core = sample_core()
        near = core.turn_length(0.5e-3)
        far = core.turn_length(2.0e-3)
        self.assertGreater(far, near)
        # The increment is exactly the circumference of the offset difference.
        self.assertAlmostEqual(far - near, 2 * math.pi * 1.5e-3, places=9)

    def test_square_fallback_when_post_unknown(self):
        core = CoreGeometry(
            part="x", material="m", ae_m2=100e-6, le_m=0.03, ve_m3=3e-6,
            height_m=0.006, outline_x_m=0.02, outline_y_m=0.015,
            window_height_m=0.002, window_radial_m=0.003,
        )
        self.assertAlmostEqual(core.post_long_m, core.post_short_m)


class StackupTest(unittest.TestCase):
    def test_barrier_only_where_the_stack_crosses(self):
        """Thick insulation between every layer would make the board unbuildable."""
        tr = sample_transformer()
        barriers = tr.stackup.primary_secondary_interfaces()
        self.assertEqual(len(barriers), 2)
        for _, _, thickness in barriers:
            self.assertAlmostEqual(thickness, 0.4e-3)
        self.assertLess(tr.stackup.total_thickness_m, 3.5e-3)

    def test_interleaved_stack_has_two_barriers(self):
        interleaved = sample_transformer(interleave=True)
        plain = sample_transformer(interleave=False)
        self.assertGreaterEqual(
            len(interleaved.stackup.primary_secondary_interfaces()),
            len(plain.stackup.primary_secondary_interfaces()),
        )

    def test_layer_count_matches_the_request(self):
        tr = sample_transformer(primary_turns=8, turns_per_primary_layer=2,
                                secondary_turns=2, secondary_parallel=3)
        self.assertEqual(tr.stackup.layer_count, 4 + 2 * 3)

    def test_separation_accumulates(self):
        tr = sample_transformer()
        total = tr.stackup.separation_between(0, tr.stackup.layer_count - 1)
        self.assertAlmostEqual(
            total, sum(d.thickness_m for d in tr.stackup.dielectrics)
        )


class LayoutTest(unittest.TestCase):
    def test_geometry_validates(self):
        self.assertEqual(sample_transformer().validate(), [])

    def test_turns_stay_inside_the_window(self):
        tr = sample_transformer()
        for turn in tr.turns:
            self.assertGreaterEqual(turn.offset_m - turn.width_m / 2, -1e-9)
            self.assertLessEqual(
                turn.offset_m + turn.width_m / 2,
                tr.core.window_radial_m + 1e-9,
            )

    def test_too_many_turns_is_caught(self):
        """Cramming turns into the window must fail validation, not silently fit."""
        tr = sample_transformer(primary_turns=4, turns_per_primary_layer=4)
        tr.trace_spacing_m = 5e-3   # impossible spacing for this window
        self.assertTrue(tr.validate())

    def test_each_turn_has_its_own_length(self):
        tr = sample_transformer(primary_turns=4, turns_per_primary_layer=4,
                                secondary_parallel=2)
        primary = tr.stackup.by_winding("primary")[0]
        lengths = sorted(t.length_m for t in tr.turns_on(primary.index))
        self.assertGreater(len(set(lengths)), 1)
        self.assertLess(lengths[0], lengths[-1])

    def test_board_is_large_enough_for_the_copper(self):
        tr = sample_transformer()
        long_extent, short_extent = tr.core.winding_extent_m()
        board_x, board_y = tr.board_size_m
        self.assertGreaterEqual(board_y, long_extent)
        self.assertGreaterEqual(board_x, short_extent)

    def test_unknown_layer_raises(self):
        with self.assertRaises(GeometryError):
            sample_transformer().layer(99)


class RacetrackTest(unittest.TestCase):
    def test_polyline_length_matches_the_analytic_perimeter(self):
        tr = sample_transformer()
        turn = tr.turns[0]
        points = _racetrack_points(turn, 256)
        traced = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
        # The open segment means the traced path is one chord short.
        self.assertAlmostEqual(traced / turn.length_m, 1.0, delta=0.02)


class BoardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.tr = sample_transformer()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_project_carries_the_brief_constraints(self):
        """DRC must check this design's minimums, not KiCad's stock ones."""
        import json
        path = write_project(self.dir / "cell.kicad_pro", 0.15e-3, 0.1e-3,
                             0.2e-3, 0.4e-3)
        rules = json.loads(path.read_text())["board"]["design_settings"]["rules"]
        self.assertAlmostEqual(rules["min_through_hole_diameter"], 0.2)
        self.assertAlmostEqual(rules["min_clearance"], 0.15)

    def test_board_declares_the_pinned_format(self):
        path = self.dir / "cell.kicad_pcb"
        write_board(self.tr, path)
        text = path.read_text()
        self.assertIn(f"(version {BOARD_FORMAT_VERSION})", text)
        self.assertIn('(generator "forge")', text)

    def test_every_copper_layer_is_declared_and_used(self):
        path = self.dir / "cell.kicad_pcb"
        result = write_board(self.tr, path)
        text = path.read_text()
        self.assertEqual(result.layers, self.tr.stackup.layer_count)
        for copper in self.tr.stackup.copper:
            self.assertIn(f'"{copper.name}"', text)

    @unittest.skipUnless(shutil.which("kicad-cli"), "kicad-cli not installed")
    def test_kicad_accepts_the_board_and_drc_is_clean(self):
        path = self.dir / "cell.kicad_pcb"
        write_board(self.tr, path)
        write_project(self.dir / "cell.kicad_pro", 0.15e-3, 0.1e-3,
                      0.2e-3, 0.4e-3)
        write_design_rules(self.dir / "cell.kicad_dru", 0.15e-3, 0.1e-3,
                           0.2e-3, 0.4e-3)
        verification = verify_board(path)
        self.assertTrue(verification.passed, verification.summary())
        self.assertEqual(verification.violations_by_type, {})

    @unittest.skipUnless(shutil.which("kicad-cli"), "kicad-cli not installed")
    def test_all_copper_layers_are_plotted(self):
        path = self.dir / "cell.kicad_pcb"
        write_board(self.tr, path)
        write_project(self.dir / "cell.kicad_pro", 0.15e-3, 0.1e-3,
                      0.2e-3, 0.4e-3)
        verification = verify_board(path)
        gerber_check = next(
            c for c in verification.checks if c.name == "gerber export"
        )
        self.assertTrue(gerber_check.passed)
        self.assertIn(
            f"{self.tr.stackup.layer_count} copper layers", gerber_check.detail
        )


class FemmWriterTest(unittest.TestCase):
    def test_equivalent_radius_preserves_turn_length(self):
        tr = sample_transformer()
        turn = tr.turns[0]
        radius = equivalent_radius(tr, turn)
        self.assertAlmostEqual(2 * math.pi * radius, turn.length_m, places=12)

    def test_study_declares_what_it_cannot_model(self):
        tr = sample_transformer()
        with tempfile.TemporaryDirectory() as tmp:
            study = write_winding_study(
                tr, Path(tmp) / "oc.lua", 2e6, {"primary": 1.0}
            )
            text = study.lua_path.read_text()
            self.assertIn("mi_probdef", text)
            self.assertIn('"axi"', text)
            self.assertIn("mi_analyze", text)
            self.assertTrue(study.unsupported)
            self.assertIn("racetrack", study.caveats())

    def test_unsupported_list_mentions_vias_and_capacitance(self):
        joined = " ".join(unsupported_features())
        self.assertIn("via", joined)
        self.assertIn("capacitance", joined)


class Peec3DTest(unittest.TestCase):
    def test_conductor_lengths_match_the_model(self):
        tr = sample_transformer()
        geometry = export_geometry(tr)
        modelled = tr.conductor_length("primary")
        exported = geometry.total_conductor_length("primary")
        self.assertAlmostEqual(exported / modelled, 1.0, delta=0.03)

    def test_vias_are_exported(self):
        geometry = export_geometry(sample_transformer())
        self.assertTrue(geometry.vias)

    def test_export_states_remaining_gaps(self):
        geometry = export_geometry(sample_transformer())
        self.assertTrue(geometry.closes_2d_gaps)
        self.assertTrue(geometry.still_unbounded)

    def test_fasthenry_deck_is_written(self):
        geometry = export_geometry(sample_transformer())
        with tempfile.TemporaryDirectory() as tmp:
            path = write_fasthenry(geometry, Path(tmp) / "c.inp", 2e6)
            text = path.read_text()
            self.assertIn(".units m", text)
            self.assertIn(".freq", text)
            self.assertIn(".end", text)


if __name__ == "__main__":
    unittest.main()
