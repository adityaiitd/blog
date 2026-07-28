"""Benchmarks, pre-registered so the comparison cannot be tuned after the fact.

The protocol is committed and hashed before any comparison runs. That is the
whole point: without it, a model that misses can be adjusted until it hits, and
the resulting agreement means nothing.

The published designs used here disclose their construction and their
converter-level performance. None of them publishes a measured transformer
loss, an inductance or a winding temperature. So none of them can validate a
transformer model, and this module refuses to describe them as validation.
They are consistency checks: if the model cannot reproduce a whole-converter
figure to within a stated band, something is wrong; if it can, that is
necessary but nowhere near sufficient.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

HERE = Path(__file__).resolve().parent
PROTOCOL_PATH = HERE.parent / "data" / "benchmark_protocol.json"


class Role(str, Enum):
    """What a reference is allowed to be used for."""

    ANALYTIC = "analytic"          # reproduce an equation the author published
    CONSISTENCY = "consistency"    # converter-level figure, model must be near it
    PLAUSIBILITY = "plausibility"  # topology and envelope only, no numeric claim
    CALIBRATION = "calibration"    # may tune parameters against this one
    HOLDOUT = "holdout"            # must not be touched before it is scored


@dataclass(frozen=True)
class Observable:
    """One thing that will be compared, and how."""

    key: str
    description: str
    unit: str
    #: Acceptance band. Absolute where the quantity is a percentage, relative
    #: otherwise; whichever is stated here is the one applied.
    tolerance: float
    tolerance_kind: str            # "absolute" | "relative"
    source_disclosed: bool
    note: str = ""


@dataclass
class Benchmark:
    key: str
    title: str
    source_key: str
    role: str
    what_is_published: List[str]
    what_is_not_published: List[str]
    observables: List[Observable]
    why_it_cannot_validate: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["observables"] = [asdict(o) for o in self.observables]
        return payload


#: The three published designs, and exactly what each may be used for.
BENCHMARKS: List[Benchmark] = [
    Benchmark(
        key="ti_eighth_brick",
        title="TI 1 MHz, 1 kW eighth-brick LLC bus converter",
        source_key="ti_ssztd94",
        role=Role.ANALYTIC.value,
        what_is_published=[
            "matrix transformer structure and PWB layer stackup",
            "a closed-form AC winding resistance expression",
            "a statement that the expression agreed with a transient FEA "
            "model to within one percent",
            "measured converter efficiency, loss and regulation against load",
        ],
        what_is_not_published=[
            "measured transformer loss separated from converter loss",
            "measured inductances or AC resistance against frequency",
            "core material, core part number or complete core dimensions",
            "airflow rate, heatsink or thermal boundary conditions",
            "winding or core temperature",
        ],
        observables=[
            Observable(
                "winding_loss_equation", "Reproduce the published closed-form "
                "AC resistance expression for a stated geometry", "ohm",
                0.02, "relative", True,
                "This checks arithmetic against a published equation. It says "
                "nothing about whether the equation matches hardware.",
            ),
            Observable(
                "converter_efficiency", "Total converter efficiency against "
                "load", "fraction", 0.01, "absolute", True,
                "Includes semiconductors, gate drive and control. The "
                "transformer is a minority of this number, so agreement is a "
                "weak constraint on the transformer model.",
            ),
        ],
        why_it_cannot_validate=(
            "The one percent agreement TI reports is between its own equation "
            "and its own finite element model. Both are simulations. Treating "
            "that as hardware validation would be a category error, and the "
            "measured figure it does publish is converter-level."
        ),
    ),
    Benchmark(
        key="epc_isop",
        title="EPC 800 VDC to 12.5 V, 6 kW ISOP converter",
        source_key="epc91123_kit_guide",
        role=Role.CONSISTENCY.value,
        what_is_published=[
            "the eight-cell ISOP architecture and 4:1:1 turns ratio",
            "100 V and 750 W per cell, roughly 1 MHz resonance",
            "converter footprint of 4982 mm2 and 8 mm height",
            "14-layer transformer board, 6-layer power board",
            "core type and material by name",
            "efficiency against output current, and housekeeping power",
        ],
        what_is_not_published=[
            "winding artwork, trace widths or via construction",
            "dielectric thicknesses or complete layer stackup",
            "magnetising and leakage inductance",
            "loss broken down by mechanism",
            "any thermal test condition",
        ],
        observables=[
            Observable(
                "architecture_match", "Cell count, turns ratio and cell power "
                "agree with the published architecture", "", 0.0, "absolute",
                True, "Exact match expected; these are integers.",
            ),
            Observable(
                "converter_efficiency_full_load", "Efficiency near full load",
                "fraction", 0.015, "absolute", True,
                "Read from a plotted curve, so the reference itself carries "
                "reading error of roughly half a point.",
            ),
            Observable(
                "footprint", "Converter area", "mm2", 0.25, "relative", True,
                "A loose band: layout is not disclosed, so this only catches "
                "an answer that is wildly the wrong size.",
            ),
        ],
        why_it_cannot_validate=(
            "No transformer-level measurement is published at all. Matching "
            "the converter efficiency would leave the transformer model "
            "unconstrained, because semiconductor loss dominates and is not "
            "separable from the outside."
        ),
    ),
    Benchmark(
        key="navitas_crps",
        title="Navitas 1.5 kW CRPS LLC module with a planar matrix transformer",
        source_key="navitas_crps_planar",
        role=Role.PLAUSIBILITY.value,
        what_is_published=[
            "10-layer interleaved planar transformer concept",
            "three transformer elements at 5:1 each",
            "module envelope of 90 by 30.5 by 11 mm",
            "switching above 600 kHz and efficiency above 97.5 percent",
        ],
        what_is_not_published=[
            "trace dimensions, copper weight or dielectric thickness",
            "core material or dimensions",
            "numeric loss breakdown",
            "thermal model or test conditions",
            "full-power test results; the paper reports partial power",
        ],
        observables=[
            Observable(
                "stackup_plausibility", "Layer count and interleaving scheme "
                "are of the same order as a real design", "", 0.0, "absolute",
                False, "Qualitative. No numeric claim is made against this.",
            ),
        ],
        why_it_cannot_validate=(
            "The experimental section reports roughly 1.25 kW, not the headline "
            "1.5 kW, with full-power testing described as future work. It "
            "supports plausibility of the approach and nothing quantitative."
        ),
    ),
]


@dataclass
class Protocol:
    """The frozen agreement about what will be compared and how."""

    version: int
    benchmarks: List[Benchmark]
    frozen_parameters: List[str]
    calibration_allowed_against: List[str]
    holdout: List[str]
    rules: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "benchmarks": [b.to_dict() for b in self.benchmarks],
            "frozen_parameters": self.frozen_parameters,
            "calibration_allowed_against": self.calibration_allowed_against,
            "holdout": self.holdout,
            "rules": self.rules,
        }

    def content_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode()
        ).hexdigest()

    def save(self, path: Path | str = PROTOCOL_PATH) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_dict()
        payload["content_hash"] = self.content_hash()
        path.write_text(json.dumps(payload, indent=1) + "\n")
        return path


def build_protocol() -> Protocol:
    return Protocol(
        version=1,
        benchmarks=BENCHMARKS,
        frozen_parameters=[
            "Steinmetz coefficients fitted only to published datasheet points",
            "Dowell porosity factor",
            "via plating thickness",
            "switch-node stray capacitance",
            "thermal interface resistances in the lumped network",
        ],
        calibration_allowed_against=["ti_eighth_brick"],
        holdout=["epc_isop", "navitas_crps"],
        rules=[
            "This protocol is committed and hashed before any comparison runs.",
            "Model parameters may be adjusted only against the calibration "
            "reference, and only before hold-out references are scored.",
            "A hold-out reference that misses its band is reported as a miss. "
            "Tolerances are not widened afterwards.",
            "Only quantities the source actually published may be compared.",
            "Residual converter loss may never be attributed to the "
            "transformer to make a comparison work.",
            "No reference here can validate the transformer model, because "
            "none publishes a transformer-level measurement.",
        ],
    )


@dataclass
class Comparison:
    observable: str
    benchmark: str
    predicted: Optional[float]
    reference: Optional[float]
    within_band: Optional[bool]
    detail: str

    @property
    def scored(self) -> bool:
        return self.within_band is not None


def compare(
    benchmark: Benchmark, observable_key: str,
    predicted: Optional[float], reference: Optional[float],
) -> Comparison:
    """Score one observable, or record why it cannot be scored."""
    observable = next(
        (o for o in benchmark.observables if o.key == observable_key), None
    )
    if observable is None:
        raise KeyError(
            f"'{observable_key}' is not a pre-registered observable of "
            f"'{benchmark.key}'. Adding one now would defeat the protocol."
        )
    if predicted is None or reference is None:
        return Comparison(
            observable_key, benchmark.key, predicted, reference, None,
            "not scored: the source does not publish this quantity",
        )
    if observable.tolerance_kind == "absolute":
        error = abs(predicted - reference)
        ok = error <= observable.tolerance
        detail = (
            f"{error:.4g} {observable.unit} apart, band "
            f"{observable.tolerance:.4g}"
        )
    else:
        error = abs(predicted - reference) / abs(reference) if reference else 1e9
        ok = error <= observable.tolerance
        detail = f"{error:.2%} apart, band {observable.tolerance:.0%}"
    return Comparison(observable_key, benchmark.key, predicted, reference,
                      ok, detail)


def summary_lines(protocol: Protocol) -> List[str]:
    lines = [f"protocol v{protocol.version}, hash {protocol.content_hash()[:16]}"]
    for bench in protocol.benchmarks:
        lines.append(
            f"  {bench.key:<18}{bench.role:<14}"
            f"{len(bench.observables)} observable(s)"
        )
        lines.append(f"      {bench.why_it_cannot_validate[:96]}...")
    lines.append(f"  calibration: {', '.join(protocol.calibration_allowed_against)}")
    lines.append(f"  hold-out:    {', '.join(protocol.holdout)}")
    return lines
