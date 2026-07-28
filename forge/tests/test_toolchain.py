"""Tests for toolchain probing and capability downgrades."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from forge.toolchain import Tool, Toolchain, ToolStatus, probe_python_stack  # noqa: E402
from forge.browser.manual_gate import (  # noqa: E402
    GateReason,
    ManualGate,
    ManualGateLog,
)


class ToolchainTest(unittest.TestCase):
    def test_missing_solver_disables_field_capability(self):
        chain = Toolchain(tools={
            "femm-functional": Tool(
                name="femm-functional", purpose="",
                status=ToolStatus.MISSING.value,
                fallback="analytic screening only",
            ),
            "ngspice": Tool(name="ngspice", purpose="",
                            status=ToolStatus.AVAILABLE.value),
        })
        caps = chain.capabilities()
        self.assertFalse(caps["field_2d_fea"])
        self.assertTrue(caps["switched_circuit_sim"])
        self.assertTrue(any("femm-functional" in d for d in chain.downgrades()))

    def test_degraded_tool_is_not_usable(self):
        chain = Toolchain(tools={
            "kicad-cli": Tool(name="kicad-cli", purpose="",
                              status=ToolStatus.DEGRADED.value,
                              fallback="no manufacturing release")
        })
        self.assertFalse(chain.capabilities()["manufacturing_release"])
        self.assertEqual(len(chain.downgrades()), 1)

    def test_unknown_tool_reports_missing(self):
        chain = Toolchain()
        self.assertEqual(chain.get("nope").status, ToolStatus.MISSING.value)
        self.assertFalse(chain.usable("nope"))

    def test_round_trip_save_load(self):
        chain = Toolchain(tools={
            "ngspice": Tool(name="ngspice", purpose="sim",
                            status=ToolStatus.AVAILABLE.value, version="42")
        })
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "toolchain.json"
            chain.save(path)
            again = Toolchain.load(path)
            self.assertEqual(again.get("ngspice").version, "42")
            payload = json.loads(path.read_text())
            self.assertIn("capabilities", payload)

    def test_python_stack_probe_finds_numpy(self):
        tools = {t.name: t for t in probe_python_stack()}
        self.assertEqual(tools["numpy"].status, ToolStatus.AVAILABLE.value)


class ManualGateTest(unittest.TestCase):
    def test_gate_blocks_until_satisfied(self):
        gate = ManualGate(
            key="ocp_diablo", url="https://example.invalid/spec",
            reason=GateReason.MANAGED_CHALLENGE.value,
            what_it_blocks="Diablo rack interface requirements",
        )
        self.assertTrue(gate.blocking)
        gate.satisfy("operator supplied the PDF from a licensed download")
        self.assertFalse(gate.blocking)
        self.assertTrue(gate.resolved_at)

    def test_waiver_records_justification(self):
        gate = ManualGate(key="k", url="u", reason=GateReason.PAYWALL.value,
                          what_it_blocks="a nice-to-have curve")
        gate.waive("not needed; alternate source covers the same domain")
        self.assertFalse(gate.blocking)
        self.assertIn("alternate source", gate.resolution)

    def test_log_persists_and_summarises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gates.json"
            log = ManualGateLog(path)
            log.record(ManualGate(key="a", url="u1",
                                  reason=GateReason.CAPTCHA.value,
                                  what_it_blocks="core loss curve"))
            log.record(ManualGate(key="b", url="u2",
                                  reason=GateReason.CAPTCHA.value,
                                  what_it_blocks="stackup"))
            reloaded = ManualGateLog(path)
            self.assertEqual(len(reloaded.blocking()), 2)
            self.assertEqual(reloaded.summary()["by_reason"]["captcha"], 2)

    def test_satisfied_gate_is_not_reopened_by_a_later_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = ManualGateLog(Path(tmp) / "gates.json")
            first = ManualGate(key="a", url="u",
                               reason=GateReason.CAPTCHA.value,
                               what_it_blocks="x")
            log.record(first)
            first.satisfy("operator supplied it")
            log.save()
            again = ManualGateLog(Path(tmp) / "gates.json")
            again.record(ManualGate(key="a", url="u",
                                    reason=GateReason.CAPTCHA.value,
                                    what_it_blocks="x"))
            self.assertFalse(again.get("a").blocking)


if __name__ == "__main__":
    unittest.main()
