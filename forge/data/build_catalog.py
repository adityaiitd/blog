"""Populate the catalog from sourced data.

Core geometry is extracted from TDK's per-core ELP datasheets. Material data
comes from Ferroxcube material specifications. Device data comes from the EPC
kit guide. Anything not backed by a retrievable document is registered with
status 'unavailable' rather than filled in from memory.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..evidence.extract import EvidenceCache, fetch_direct, source_from_fetch
from ..evidence.register import EvidenceRegister, Source, SourceStatus
from ..physics.coreloss import LossPoint, fit_steinmetz
from .catalog import Catalog

TDK_ELP_BASE = "https://www.tdk-electronics.tdk.com/inf/80/db/fer/"

#: ELP sets to characterise, with the outer dimensions the datasheet drawing
#: gives. Height is the assembled set height, which is the constraint that
#: matters against an 8 mm converter.
ELP_PARTS: List[Tuple[str, float, float]] = [
    # (datasheet stem, length_mm, width_mm)
    ("elp_18_4_10", 18.0, 10.0),
    ("elp_22_6_16", 21.8, 16.0),
    ("elp_32_6_20", 31.75, 20.32),
    ("elp_38_8_25", 38.1, 25.4),
    ("elp_43_10_28", 43.0, 27.9),
    ("elp_58_11_38", 58.3, 37.6),
]


def _parse_elp(pdf_path: Path) -> List[Dict[str, object]]:
    """Pull the per-combination magnetic characteristics out of a datasheet."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyMuPDF is required to parse core datasheets") from exc

    text = "\n".join(page.get_text() for page in fitz.open(pdf_path))
    combos: List[Dict[str, object]] = []
    seen = set()
    pattern = re.compile(
        r"Combination:\s*(.+?)\n(.{0,600}?)Approx\.\s*weight\s*([\d.]+)\s*g",
        re.S,
    )
    for match in pattern.finditer(text):
        block = match.group(2)

        def num(expr: str) -> Optional[float]:
            found = re.search(expr, block)
            return float(found.group(1)) if found else None

        name = " ".join(match.group(1).split())
        if name in seen:
            continue
        seen.add(name)
        combos.append({
            "combination": name,
            "sigma": num(r"l/A\s*=\s*([\d.]+)"),
            "le_mm": num(r"le\s*\n?=\s*([\d.]+)"),
            "ae_mm2": num(r"Ae\s*\n?=\s*([\d.]+)"),
            "amin_mm2": num(r"Amin\s*=\s*([\d.]+)"),
            "ve_mm3": num(r"Ve\s*\n?=\s*([\d.]+)"),
            "mass_g": float(match.group(3)),
        })
    return combos


def _set_height_mm(stem: str, combination: str) -> float:
    """Assembled height from the two halves named in the combination.

    ``ELP 32/6/20`` has a 6 mm half height; pairing it with ``I 32/3/20`` gives
    6 + 3 = 9 mm, while an E+E pair gives 12 mm.
    """
    heights = [float(m) for m in re.findall(r"\d+/([\d.]+)/", combination)]
    if len(heights) == 2:
        return heights[0] + heights[1]
    if len(heights) == 1:
        return heights[0] * 2.0
    parts = stem.split("_")
    return float(parts[2]) * 2.0 if len(parts) > 2 else 0.0


def _window_mm(combination: str) -> Tuple[Optional[float], Optional[float]]:
    """Winding window of an ELP half: the gap between centre post and legs.

    ELP geometry is standardised such that the window height equals the half
    height minus the centre-post base. The datasheet drawing carries the exact
    figure; here only the height is inferred and the width is left unknown
    rather than guessed.
    """
    heights = [float(m) for m in re.findall(r"\d+/([\d.]+)/", combination)]
    if not heights:
        return None, None
    # An E half of nominal height h has roughly h/2 of usable window depth.
    return round(sum(heights) / 2.0, 2), None


def populate_cores(
    catalog: Catalog, register: EvidenceRegister, cache: EvidenceCache
) -> int:
    added = 0
    for stem, length_mm, width_mm in ELP_PARTS:
        url = f"{TDK_ELP_BASE}{stem}.pdf"
        key = f"tdk_{stem}"
        result = fetch_direct(url)
        source = source_from_fetch(
            key=key, result=result, owner="TDK Electronics AG",
            title=f"Ferrites and accessories: {stem.upper().replace('_', ' ')}",
            license_id="tdk-datasheet", cache=cache,
        )
        register.add_source(source)
        if source.status != SourceStatus.RETRIEVED.value or not source.cache_path:
            continue

        for combo in _parse_elp(Path(source.cache_path)):
            if not combo["ae_mm2"] or not combo["le_mm"]:
                continue
            height = _set_height_mm(stem, str(combo["combination"]))
            win_h, win_w = _window_mm(str(combo["combination"]))
            part = str(combo["combination"]).replace(" ", "")
            catalog.connection.execute(
                """INSERT OR REPLACE INTO cores
                   (part, family, manufacturer, combination, ae_mm2, amin_mm2,
                    le_mm, ve_mm3, sigma_l_a_inv_mm, height_mm, width_mm,
                    length_mm, window_h_mm, window_w_mm, mass_g, source_key,
                    provenance, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    part, "ELP", "TDK Electronics AG", combo["combination"],
                    combo["ae_mm2"], combo["amin_mm2"], combo["le_mm"],
                    combo["ve_mm3"], combo["sigma"], height, width_mm,
                    length_mm, win_h, win_w, combo["mass_g"], key, "sourced",
                    "effective parameters read from the datasheet; window "
                    "height inferred from the set geometry",
                ),
            )
            added += 1
    catalog.connection.commit()
    return added


#: Ferroxcube material specifications. The loss points are the table entries,
#: which are the only anchors the vendor guarantees anything about.
FERROXCUBE_MATERIALS = [
    {
        "name": "3F36",
        "url": "https://download.ferrite.de/pdf/3f36.pdf",
        "title": "Ferroxcube 3F36 Material specification",
        "revision": "2013 Jun 06",
        "mu_i": 1600.0,
        "b_sat_25c_mt": 520.0,
        "b_sat_100c_mt": 420.0,
        "curie_c": 230.0,
        "resistivity": 12.0,
        "density": 4750.0,
        "band": (0.5e6, 1.0e6),
        "points": [
            LossPoint(500e3, 0.050, 100.0, 90e3, "table value, approximate"),
            LossPoint(500e3, 0.100, 100.0, 700e3, "table value, approximate"),
        ],
        # Both table points share one frequency, so alpha cannot be fitted.
        "assumed_alpha": 1.85,
        "alpha_note": (
            "alpha is not determinable from the datasheet table, which quotes "
            "both loss points at 500 kHz. 1.85 is a representative exponent "
            "for a MnZn power ferrite in this band and is an assumption, not a "
            "measurement; the frequency domain is pinned to the single "
            "measured frequency so it cannot be used to extrapolate."
        ),
    },
    {
        "name": "3F46",
        "url": "https://download.ferrite.de/pdf/3f46.pdf",
        "title": "Ferroxcube 3F46 Material specification",
        "revision": "2016 March 03",
        "mu_i": 750.0,
        "b_sat_25c_mt": 520.0,
        "b_sat_100c_mt": 430.0,
        "curie_c": 280.0,
        "resistivity": 5.0,
        "density": 4750.0,
        "band": (1.0e6, 3.0e6),
        "points": [
            LossPoint(1.0e6, 0.050, 100.0, 150e3, "table value, approximate"),
            LossPoint(3.0e6, 0.010, 100.0, 50e3, "table value, approximate"),
            LossPoint(3.0e6, 0.030, 100.0, 500e3, "table value, approximate"),
        ],
        "assumed_alpha": None,
        "alpha_note": (
            "three table points at two frequencies determine alpha and beta "
            "exactly, so the residual is zero by construction. That is a "
            "property of the fit, not evidence of accuracy: the datasheet "
            "quotes these values as approximate."
        ),
    },
]


def populate_materials(
    catalog: Catalog, register: EvidenceRegister, cache: EvidenceCache
) -> int:
    added = 0
    for spec in FERROXCUBE_MATERIALS:
        key = f"ferroxcube_{spec['name'].lower()}"
        result = fetch_direct(str(spec["url"]))
        source = source_from_fetch(
            key=key, result=result, owner="Ferroxcube International Holding B.V.",
            title=str(spec["title"]), license_id="ferroxcube-restricted",
            revision=str(spec["revision"]), cache=cache,
        )
        register.add_source(source)
        status = (
            "characterised"
            if source.status == SourceStatus.RETRIEVED.value
            else "unavailable"
        )
        band_lo, band_hi = spec["band"]  # type: ignore[misc]
        catalog.connection.execute(
            """INSERT OR REPLACE INTO materials
               (name, manufacturer, mu_i, b_sat_25c_mt, b_sat_100c_mt, curie_c,
                resistivity_ohm_m, density_kg_m3, band_lo_hz, band_hi_hz,
                source_key, provenance, status, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                spec["name"], "Ferroxcube", spec["mu_i"], spec["b_sat_25c_mt"],
                spec["b_sat_100c_mt"], spec["curie_c"], spec["resistivity"],
                spec["density"], band_lo, band_hi, key, "sourced", status,
                spec["alpha_note"],
            ),
        )
        if status != "characterised":
            continue

        points: List[LossPoint] = list(spec["points"])  # type: ignore[arg-type]
        for point in points:
            catalog.connection.execute(
                """INSERT INTO loss_points
                   (material, frequency_hz, b_peak_t, temperature_c, pv_w_m3,
                    typical, source_key, locator)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    spec["name"], point.frequency_hz, point.b_peak_t,
                    point.temperature_c, point.pv_w_m3, 1, key,
                    "SPECIFICATIONS table",
                ),
            )
        fit = fit_steinmetz(points, assumed_alpha=spec["assumed_alpha"])
        catalog.connection.execute(
            """INSERT OR REPLACE INTO loss_fits
               (material, temperature_c, k, alpha, beta, f_lo_hz, f_hi_hz,
                b_lo_t, b_hi_t, n_points, max_residual, alpha_assumed,
                rel_uncertainty, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                spec["name"], fit.temperature_c, fit.k, fit.alpha, fit.beta,
                fit.f_domain[0], fit.f_domain[1], fit.b_domain[0],
                fit.b_domain[1], fit.n_points, fit.max_residual,
                int(fit.alpha_assumed), 0.25, spec["alpha_note"],
            ),
        )
        added += 1
    catalog.connection.commit()
    return added


def register_unavailable_materials(catalog: Catalog) -> None:
    """Record materials we know are relevant but could not characterise."""
    for name, maker, source_key, note in [
        (
            "ML95S", "Proterial, Ltd.", "proterial_ml95s",
            "The material EPC uses in the reference kit. The Proterial "
            "datasheet did not resolve, so no loss data is available and this "
            "material cannot be selected by the optimiser.",
        ),
        (
            "N49", "TDK Electronics AG", "tdk_ferrite_catalog",
            "TDK's 1 MHz-class power material. The material datasheet URL "
            "returned no content; the loss curves are published as graphs "
            "that would need digitising under a licence that forbids "
            "reproducing the artwork.",
        ),
        (
            "DMR51", "DMEGC Magnetics", "proterial_ml95s",
            "A DMEGC material, not a TDK one. Registered to keep the "
            "attribution correct; no datasheet retrieved.",
        ),
    ]:
        catalog.connection.execute(
            """INSERT OR REPLACE INTO materials
               (name, manufacturer, source_key, provenance, status, notes)
               VALUES (?,?,?,?,?,?)""",
            (name, maker, source_key, "sourced", "unavailable", note),
        )
    catalog.connection.commit()


def populate_devices(catalog: Catalog) -> None:
    """GaN devices named in the EPC reference kit."""
    rows = [
        ("EPC2305", "Efficient Power Conversion Corporation", "primary_switch",
         150.0, 2.2, 22.0, 122.0, 100.0, 0.0, "QFN 3x5 mm, double-sided cooling"),
        ("EPC2366", "Efficient Power Conversion Corporation",
         "synchronous_rectifier",
         40.0, 0.84, 15.0, 18.0, 12.5, 0.0, "QFN 2.6x3.3 mm"),
    ]
    for row in rows:
        catalog.connection.execute(
            """INSERT OR REPLACE INTO devices
               (part, manufacturer, role, v_ds_max_v, r_ds_on_mohm, q_g_nc,
                q_oss_nc, q_oss_at_v, q_rr_nc, package, source_key,
                provenance, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            row + ("epc91123_kit_guide", "sourced",
                   "R_DS(on) typical at V_GS = 5 V; Qoss quoted at the stated "
                   "drain voltage"),
        )
    catalog.connection.commit()


def populate_laminates_and_copper(catalog: Catalog) -> None:
    """PCB stackup properties.

    These are typical values for common laminate classes rather than a
    specific qualified material, so they are recorded as assumed. Dielectric
    thickness and Dk set both the interwinding capacitance and the solid
    insulation, which is why they belong in the catalog rather than in code.
    """
    for row in [
        ("FR-4 standard", 4.4, 0.020, 1e9, 140.0, "IIIa", 20.0, 0.3,
         "forge-internal", "assumed",
         "Typical mid-Dk FR-4. Loss tangent is high for 1 MHz magnetics but "
         "the dielectric carries little field here; it matters mainly for "
         "interwinding capacitance."),
        ("Low-loss laminate", 3.6, 0.005, 1e9, 180.0, "IIIa", 25.0, 0.4,
         "forge-internal", "assumed",
         "Represents a Megtron/Rogers-class laminate. Lower Dk reduces "
         "interwinding capacitance, which is the common-mode lever."),
    ]:
        catalog.connection.execute(
            """INSERT OR REPLACE INTO laminates
               (name, dk, df, dk_freq_hz, tg_c, cti_group, breakdown_kv_mm,
                thermal_cond_w_mk, source_key, provenance, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            row,
        )
    # IPC nominal foil thicknesses.
    for ounces, micron in [(0.5, 17.4), (1.0, 34.8), (2.0, 69.6),
                           (3.0, 104.4), (4.0, 139.2)]:
        catalog.connection.execute(
            """INSERT OR REPLACE INTO copper_weights
               (ounces, thickness_um, provenance, notes)
               VALUES (?,?,?,?)""",
            (ounces, micron, "sourced",
             "IPC nominal foil thickness; plating adds to outer layers"),
        )
    catalog.connection.commit()


def build(
    catalog_path: Optional[Path] = None,
    evidence_path: Optional[Path] = None,
) -> Dict[str, int]:
    here = Path(__file__).resolve().parent
    catalog = Catalog(catalog_path or here / "catalog.sqlite")
    register = EvidenceRegister(evidence_path or here / "evidence.sqlite")
    cache = EvidenceCache(here / "evidence_cache")
    try:
        populate_cores(catalog, register, cache)
        populate_materials(catalog, register, cache)
        register_unavailable_materials(catalog)
        populate_devices(catalog)
        populate_laminates_and_copper(catalog)
        return catalog.summary()
    finally:
        catalog.close()
        register.close()


def main() -> int:
    summary = build()
    for key, count in summary.items():
        print(f"{key:<14} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
