"""Generate the design package.

Structured so a reader can always separate four different kinds of statement:
what a source said, what was computed from it, what was assumed, and what
remains unknown. The generator checks its own output against the claim rules
before writing, so a document that overstates its evidence never reaches disk.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..evidence.register import EvidenceRegister
from ..solve.candidate import Candidate
from ..verify.gates import GateReport, assert_claim_allowed

CLAIM_BANNER = (
    "**Simulation-backed preliminary design. Not production-qualified. "
    "Hazardous high voltage. Independent safety and regulatory review is "
    "required before any hardware is built.**"
)


def _table(headers: List[str], rows: List[List[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def build_report(
    candidate: Candidate,
    register: Optional[EvidenceRegister] = None,
    sourcing: Optional[Dict[str, Any]] = None,
    field_result: Optional[Any] = None,
    circuit: Optional[Dict[str, Any]] = None,
) -> str:
    m = candidate.result.metrics
    i = candidate.inputs
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    parts: List[str] = []
    parts.append("# Planar transformer for an 800 VDC to 12.5 V rack converter")
    parts.append("")
    parts.append(CLAIM_BANNER)
    parts.append("")
    parts.append(f"Generated {now}. "
                 f"Requirements lock `{candidate.gates.requirements_hash[:16]}`, "
                 f"benchmark protocol `{candidate.gates.protocol_hash[:16]}`.")

    # ------------------------------------------------------------- verdict
    parts.append("\n## Where this stands\n")
    level = candidate.gates.level().value
    parts.append(f"Release level: **{level}**.")
    reason = candidate.gates.refusal_reason()
    if reason:
        parts.append(f"\nNot releasable as a candidate package because "
                     f"{reason}.")
    parts.append(
        "\nNo hardware exists. Every number below is a model output, and the "
        "loss, temperature and inductance figures in particular are "
        "unconfirmed until something is built and measured against the "
        "criteria in `hardware/acceptance.lock.yaml`."
    )

    # ------------------------------------------------------------- design
    parts.append("\n## The design\n")
    parts.append(_table(
        ["Parameter", "Value", "Basis"],
        [
            ["Core", i.core_part, "selected by screening"],
            ["Material", i.material, "sourced datasheet"],
            ["Switching frequency", f"{i.frequency_hz/1e6:.2f} MHz", "selected"],
            ["Primary turns", i.primary_turns, "selected"],
            ["Secondary turns per half", m["secondary_turns"], "derived from 4:1 ratio"],
            ["Parallel secondary layers", i.secondary_parallel, "selected"],
            ["Copper weight", f"{i.copper_oz:g} oz "
             f"({m['copper_thickness_um']:.0f} um)", "selected"],
            ["Interleaved", "yes" if i.interleave else "no", "selected"],
            ["Layers used", f"{m['layers']} of 14", "derived"],
            ["Board thickness", f"{m['board_thickness_mm']:.2f} mm", "derived"],
        ],
    ))

    parts.append("\n### Resonant tank\n")
    parts.append(_table(
        ["Quantity", "Value", "How it was obtained"],
        [
            ["Magnetising inductance", f"{m['l_m_uH']:.3f} uH",
             "set to a fraction of the ZVS charge limit"],
            ["Resonant inductance", f"{m['l_r_uH']:.4f} uH",
             "from the chosen Lm/Lr ratio; in practice this is transformer leakage"],
            ["Resonant capacitance", f"{m['c_r_nF']:.2f} nF", "places resonance at the switching frequency"],
            ["Resonant frequency", f"{m['f_resonant_MHz']:.3f} MHz", "derived"],
            ["Capacitor peak voltage", f"{m['capacitor_peak_V']:.0f} V",
             "from tank current, not from the bus"],
        ],
    ))

    # --------------------------------------------------------------- loss
    parts.append("\n## Loss and temperature\n")
    total = m["total_loss_W"]
    parts.append(_table(
        ["Mechanism", "Watts", "Share", "Confidence"],
        [
            ["Core", f"{m['core_loss_W']:.2f}",
             f"{m['core_loss_W']/total*100:.0f}%",
             "iGSE over the real triangular waveform, inside the fitted domain"],
            ["Primary copper", f"{m['primary_loss_W']:.2f}",
             f"{m['primary_loss_W']/total*100:.0f}%",
             "1D Dowell; the field solver has not corrected it"],
            ["Secondary copper", f"{m['secondary_loss_W']:.2f}",
             f"{m['secondary_loss_W']/total*100:.0f}%",
             "1D Dowell, divided across parallel layers"],
            ["Vias", f"{m['via_loss_W']:.2f}",
             f"{m['via_loss_W']/total*100:.0f}%",
             "barrel resistance only; current crowding not modelled"],
            ["**Total**", f"**{total:.2f}**", "100%",
             f"transformer only, {m['efficiency']*100:.2f}% efficient at 750 W"],
        ],
    ))
    parts.append(
        f"\nSkin depth at this frequency is {m['skin_depth_um']:.0f} um against "
        f"{m['copper_thickness_um']:.0f} um of copper. Loss is minimised near "
        "one skin depth, so copper weight is a real optimum rather than a "
        "case of thicker being better."
    )
    parts.append(
        f"\nWorst-case temperature across the swept cooling boundary is "
        f"{m['winding_c']:.0f} C in the winding and {m['core_c']:.0f} C in the "
        "core. The airflow and thermal path behind those numbers are "
        "assumptions, not specifications, which is why the result is a sweep."
    )

    # ------------------------------------------------------------- safety
    parts.append("\n## Insulation and common mode\n")
    parts.append(
        "The consequence of stacking cells in series is easy to understate. "
        "Each cell switches only about 100 V locally, but the top cell's "
        "primary floats near the entire bus with respect to the shared "
        "secondary. The barrier is therefore designed against **844.6 V**, "
        "roughly eight times the local figure."
    )
    parts.append(
        f"\nInterwinding capacitance is {m['c_ps_static_pF']:.1f} pF static, "
        f"driving {m['cm_rms_mA']:.0f} mA rms of common-mode current at "
        f"{m['cm_peak_A']:.1f} A peak during each edge. Interleaving lowers "
        "copper loss and raises this capacitance, so the two cannot be "
        "optimised separately."
    )

    # ------------------------------------------------------------- gates
    parts.append("\n## Gates\n")
    rows = []
    for gate in candidate.gates.gates:
        mark = {"PASS": "pass", "FAIL": "**fail**",
                "UNVERIFIED": "**unverified**", "N/A": "n/a"}[gate.state]
        rows.append([gate.title, mark,
                     ("safety" if gate.safety_critical else ""),
                     gate.detail[:110]])
    parts.append(_table(["Gate", "State", "", "Detail"], rows))
    parts.append(
        "\nAn unverified gate blocks release exactly as a failing one does. "
        "Not having checked something is a different claim from having "
        "checked it and found it acceptable."
    )

    # ------------------------------------------------------------ circuit
    if circuit:
        parts.append("\n## Circuit verification\n")
        for line in circuit.get("summary", []):
            parts.append(f"- {line}")

    # ----------------------------------------------------------- sourcing
    if sourcing and "summary" in sourcing:
        s = sourcing["summary"]
        parts.append("\n## Cost\n")
        parts.append(
            f"A 6 kW converter comes to **${s['total_usd']:.2f}**, or "
            f"${s['usd_per_kw']:.2f} per kW, at {s['volume']} units. "
            f"{s['caveat']}"
        )
        rows = [[l["mpn"], l["qty"],
                 f"${l['unit_usd']:.3f}" if l["unit_usd"] else "-",
                 f"${l['extended_usd']:.2f}" if l["extended_usd"] else "-",
                 l["basis"]]
                for l in sourcing["lines"]]
        parts.append("")
        parts.append(_table(["Part", "Qty", "Unit", "Extended", "Basis"], rows))

    # -------------------------------------------------------- assumptions
    parts.append("\n## What is assumed rather than known\n")
    for note in candidate.result.notes:
        parts.append(f"- {note}")
    parts.append(
        "- Cooling: airflow, inlet temperature and thermal path are all "
        "assumed and swept, because none is published for this class of "
        "converter."
    )
    parts.append(
        "- Insulation spacing: conservative placeholders. The governing IEC "
        "tables are licensed and may not be reproduced here."
    )
    parts.append(
        "- Interwinding capacitance: estimated from facing areas, not solved "
        "electrostatically."
    )
    parts.append(
        "- Leakage inductance: analytic. The 2D field study omits vias, "
        "corners and end effects, and has not been run for this geometry."
    )

    # -------------------------------------------------------------- next
    parts.append("\n## What would have to happen next\n")
    parts.append(
        "1. A licensed reviewer replaces the placeholder insulation spacings.\n"
        "2. The 2D field study runs on this geometry, and targeted 3D studies "
        "cover vias and corners.\n"
        "3. Prototypes are built and measured against "
        "`hardware/acceptance.lock.yaml`, whose criteria were frozen before "
        "any hardware existed.\n"
        "4. Only once every criterion in that file is met does its promotion "
        "clause apply. Production qualification is not in scope for this "
        "project at all, and passing that protocol would not imply it."
    )

    # --------------------------------------------------------- provenance
    if register is not None:
        parts.append("\n## Sources\n")
        rows = []
        for source in register.sources():
            rows.append([source.key, source.owner,
                         source.revision or "-", source.status])
        parts.append(_table(["Key", "Owner", "Revision", "Status"], rows))
        parts.append(
            "\nRetrieved documents are held in a local cache that is excluded "
            "from version control. Most are all-rights-reserved, and getting "
            "past an HTTP 403 is not a redistribution right, so only citations "
            "and derived values appear here."
        )

    text = "\n".join(parts) + "\n"
    # The generator checks its own output before it can be written.
    assert_claim_allowed(text, candidate.gates, hardware_passed=False)
    return text


def write_report(
    candidate: Candidate,
    path: Path | str,
    register: Optional[EvidenceRegister] = None,
    sourcing: Optional[Dict[str, Any]] = None,
    circuit: Optional[Dict[str, Any]] = None,
) -> Path:
    text = build_report(candidate, register, sourcing, circuit=circuit)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path
