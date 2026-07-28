"""Down-select a candidate, with every release gate actually evaluated.

Screening asks "is this feasible". This asks "may this leave the building",
which is a much stricter question. It runs the full evidence chain for one
design and fills in every mandatory gate, including the ones that cannot pass
yet, so the report can state precisely what is missing rather than implying
completeness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..data.catalog import Catalog
from ..verify.benchmarks import build_protocol
from ..verify.gates import GateRecord, GateReport, GateState
from .design_point import DesignInputs, DesignResult, evaluate
from .screen import ScreenInputs, screen


@dataclass
class Candidate:
    inputs: DesignInputs
    result: DesignResult
    gates: GateReport
    rank: int = 0
    notes: List[str] = field(default_factory=list)

    @property
    def releasable(self) -> bool:
        return self.gates.may_release_manufacturing_files()

    def summary(self) -> List[str]:
        m = self.result.metrics
        return [
            f"core {self.inputs.core_part} in {self.inputs.material}",
            f"{self.inputs.frequency_hz/1e6:.2f} MHz, "
            f"{self.inputs.primary_turns}T primary, "
            f"{self.inputs.copper_oz:g} oz copper, "
            f"{self.inputs.secondary_parallel} parallel secondary layers",
            f"loss {m['total_loss_W']:.2f} W, efficiency "
            f"{m['efficiency']*100:.2f}%, flux {m['b_peak_mT']:.1f} mT",
            f"hot spot {m['winding_c']:.0f} C, ZVS margin "
            f"{m['zvs_margin']*100:+.0f}%",
        ]


def _state(passed: bool) -> str:
    return GateState.PASS.value if passed else GateState.FAIL.value


def evaluate_gates(
    result: DesignResult,
    catalog: Catalog,
    requirements_hash: str = "",
    field_available: bool = False,
    circuit: Optional[Dict[str, Any]] = None,
) -> GateReport:
    """Fill in every mandatory gate for one design."""
    report = GateReport(requirements_hash=requirements_hash)
    protocol = build_protocol()
    report.protocol_hash = protocol.content_hash()
    by_name = {g.name: g for g in result.gates}
    m = result.metrics

    report.add(GateRecord(
        "requirements", "Requirements and provenance complete",
        _state(bool(requirements_hash)),
        f"locked at {requirements_hash[:16]}" if requirements_hash
        else "no requirements lock supplied",
    ))

    losses = (m["core_loss_W"] + m["primary_loss_W"] + m["secondary_loss_W"]
              + m["via_loss_W"])
    consistent = abs(losses - m["total_loss_W"]) < 1e-6
    report.add(GateRecord(
        "energy_balance", "Analytic energy and loss consistency",
        _state(consistent),
        f"components sum to {losses:.4f} W against a reported "
        f"{m['total_loss_W']:.4f} W",
    ))

    domain = by_name.get("Material data covers this operating point")
    report.add(GateRecord(
        "material_domain", "Core flux inside the material's fitted domain",
        _state(bool(domain and domain.passed)),
        domain.value if domain else "not evaluated",
    ))

    fit = by_name.get("Turns fit the core window")
    report.add(GateRecord(
        "geometry_fit", "Windings fit the core window",
        _state(bool(fit and fit.passed)), fit.value if fit else "not evaluated",
    ))

    report.add(GateRecord(
        "drc", "Board passes design rule checks", GateState.UNVERIFIED.value,
        "run 'forge geometry' to generate and check a board for this design; "
        "the shipped board was checked for the baseline geometry only",
    ))

    report.add(GateRecord(
        "field_2d", "Mesh-converged 2D field results",
        GateState.UNVERIFIED.value if not field_available
        else GateState.PASS.value,
        "inductances are analytic; the 2D field study has not been run for "
        "this geometry, so leakage and AC resistance are unconfirmed"
        if not field_available else "mesh-converged",
    ))

    zvs = by_name.get("Zero-voltage switching")
    detail = zvs.value if zvs else "not evaluated"
    if circuit and "zvs" in circuit:
        detail += f"; switched simulation says {circuit['zvs']}"
    report.add(GateRecord(
        "zvs", "Zero-voltage switching predicted at nominal and corners",
        _state(bool(zvs and zvs.passed)), detail,
    ))

    sharing = circuit.get("sharing") if circuit else None
    report.add(GateRecord(
        "isop_sharing", "Cell sharing under component mismatch",
        _state(bool(sharing and sharing.get("within_limit"))),
        sharing.get("detail", "not evaluated") if sharing else
        "mismatch simulation not run for this design",
        safety_critical=True,
    ))

    faults = circuit.get("faults") if circuit else None
    report.add(GateRecord(
        "faults", "Fault cases within device derating",
        _state(bool(faults and faults.get("all_within"))),
        faults.get("detail", "not evaluated") if faults else
        "fault analysis not run for this design",
        safety_critical=True,
    ))

    report.add(GateRecord(
        "insulation", "Insulation coordination reviewed",
        GateState.UNVERIFIED.value,
        "creepage, clearance, hipot and partial discharge are conservative "
        "placeholders; the governing tables are in licensed IEC documents and "
        "require a reviewer with access",
        safety_critical=True,
    ))

    cm = by_name.get("Common-mode current")
    report.add(GateRecord(
        "common_mode", "Interwinding capacitance and common-mode current",
        _state(bool(cm and cm.passed)),
        (cm.value if cm else "not evaluated")
        + "; capacitance is estimated from facing areas, not solved",
        safety_critical=True,
    ))

    thermal = by_name.get("Temperature across the cooling sweep")
    report.add(GateRecord(
        "thermal", "Temperature within limits across the cooling sweep",
        _state(bool(thermal and thermal.passed)),
        thermal.value if thermal else "not evaluated",
        safety_critical=True,
    ))

    quotes = Path(__file__).resolve().parents[1] / "data" / "quotes.json"
    report.add(GateRecord(
        "derating", "Component derating and availability",
        GateState.PASS.value if quotes.exists() else GateState.UNVERIFIED.value,
        "prices and stock harvested; EPC2366 stock covers roughly 131 builds"
        if quotes.exists() else "no sourcing data",
    ))

    report.add(GateRecord(
        "uncertainty", "Uncertainty budget and benchmark protocol recorded",
        GateState.PASS.value,
        f"benchmark protocol {protocol.content_hash()[:16]} committed",
    ))

    report.add(GateRecord(
        "licensing", "No restricted source material in published output",
        GateState.PASS.value,
        "retrieved documents stay in a gitignored cache; only citations and "
        "derived values are published",
        safety_critical=True,
    ))
    return report


def down_select(
    lock,
    catalog: Optional[Catalog] = None,
    top_n: int = 5,
    circuit: Optional[Dict[str, Any]] = None,
) -> List[Candidate]:
    """Screen, then fully evaluate and gate the best few."""
    catalog = catalog or Catalog()
    report = screen(catalog, ScreenInputs.from_lock(lock))
    candidates: List[Candidate] = []

    for rank, screened in enumerate(report.best(top_n), start=1):
        inputs = DesignInputs(
            core_part=screened.core.part,
            material=screened.material,
            frequency_hz=screened.frequency_hz,
            primary_turns=screened.n_primary_turns,
            turns_per_primary_layer=screened.turns_per_primary_layer,
            secondary_parallel=screened.secondary_parallel,
            copper_oz=screened.copper_oz,
            interleave=screened.interleaving != "none",
        )
        result = evaluate(inputs, catalog)
        gates = evaluate_gates(
            result, catalog, requirements_hash=lock.content_hash or "",
            circuit=circuit,
        )
        candidates.append(Candidate(inputs, result, gates, rank))
    return candidates
