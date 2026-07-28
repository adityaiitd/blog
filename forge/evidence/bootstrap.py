"""Register the documents this design depends on.

Each source is attempted over plain HTTP first, then through headful Chrome if
that is refused, and finally recorded as a manual gate if a managed challenge
stands in the way. A blocked source is not a crash and not a silent default:
it is a hole with a name, and the requirements that needed it say so.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ..browser.manual_gate import GateReason, ManualGate, ManualGateLog
from .extract import EvidenceCache, fetch_direct, source_from_fetch
from .register import EvidenceRegister, RetrievalMethod, Source, SourceStatus


@dataclass(frozen=True)
class SourceSpec:
    key: str
    url: str
    owner: str
    title: str
    license_id: str
    revision: str = ""
    blocks: str = ""
    #: Sources whose content we already hold from a licensed or offline route.
    offline: bool = False


SOURCES: List[SourceSpec] = [
    SourceSpec(
        key="ocp_diablo_400_v070",
        url="https://www.opencompute.org/documents/"
            "ocp-specification-diablo-400-v0-7-0-final-pdf",
        owner="Open Compute Project Foundation",
        title="Diablo 400 Project: Rack and Power, Base Specification",
        license_id="ocp-owfa-1.0-modified",
        revision="0.7.0 (1 March 2026)",
        blocks="Diablo rack interface requirements",
    ),
    SourceSpec(
        key="ocp_diablo_400_v052",
        url="https://www.opencompute.org/documents/"
            "ocp-specification-diablo-400-v0p5p2-2025-05-30-pdf",
        owner="Open Compute Project Foundation",
        title="Diablo 400 Project: Rack and Power, Base Specification",
        license_id="ocp-owfa-1.0-modified",
        revision="0.5.2 (30 May 2025)",
        blocks="DC output voltage regulation parameters (Table 4)",
    ),
    SourceSpec(
        key="epc91123_kit_guide",
        url="https://epc-co.com/epc/portals/0/epc/documents/guides/"
            "EPC91123kit.pdf",
        owner="Efficient Power Conversion Corporation",
        title="EPC91123KIT 800 V to 12.5 V 6 kW",
        license_id="epc-all-rights-reserved",
        revision="May 2026",
        blocks="converter architecture, cell rating, device selection",
    ),
    SourceSpec(
        key="epc_800v_white_paper",
        url="https://epc-co.com/epc/portals/0/epc/documents/papers/"
            "White%20Paper%20EPC%20Nvidia%20800%20VDC%20to%2012.5.pdf",
        owner="Efficient Power Conversion Corporation",
        title="Low Cost and Low Profile 800 VDC to 12.5 V DC-DC Converter "
              "Using Low Voltage GaN in an ISOP Topology",
        license_id="epc-all-rights-reserved",
        blocks="ISOP rationale and converter-level efficiency reference",
    ),
    SourceSpec(
        key="ti_ssztd94",
        url="https://www.ti.com/lit/ta/ssztd94/ssztd94.pdf",
        owner="Texas Instruments Incorporated",
        title="Overview of a planar transformer used in a 1kW high density "
              "LLC power module",
        license_id="ti-technical-resource",
        blocks="analytic winding-loss benchmark",
    ),
    SourceSpec(
        key="navitas_crps_planar",
        url="https://navitassemi.com/wp-content/uploads/2023/06/"
            "High-Frequency-High-Efficiency-LLC-Module-with-Planar-Matrix-"
            "Transformer-for-CRPS-Application-Using-GaN-Power-IC-paper.pdf",
        owner="Navitas Semiconductor",
        title="High Frequency High Efficiency LLC Module with Planar Matrix "
              "Transformer for CRPS Application Using GaN Power IC",
        license_id="navitas-paper",
        blocks="planar stackup plausibility reference",
    ),
    SourceSpec(
        key="magnetics_ferrite_catalog",
        url="https://www.mag-inc.com/Media/Magnetics/File-Library/"
            "Product%20Literature/Ferrite%20Literature/"
            "Magnetics-2022-Ferrite-Catalog.pdf",
        owner="Magnetics (Spang & Company)",
        title="Magnetics Ferrite Cores Catalog",
        license_id="magnetics-catalog",
        revision="2022",
        blocks="planar core geometry and material loss curves",
    ),
    SourceSpec(
        key="tdk_ferrite_catalog",
        url="https://product.tdk.com/en/search/ferrite/ferrite/ferrite-core/list",
        owner="TDK Electronics AG",
        title="TDK Ferrite Cores product search",
        license_id="tdk-datasheet",
        blocks="ELP planar core geometry",
    ),
    SourceSpec(
        key="iec_62368_1",
        url="https://webstore.iec.ch/publication/27412",
        owner="International Electrotechnical Commission",
        title="IEC 62368-1 Audio/video, information and communication "
              "technology equipment - Safety requirements",
        license_id="iec-standard",
        blocks="creepage, clearance and dielectric test derivation",
        offline=True,
    ),
    SourceSpec(
        key="iec_60664_1",
        url="https://webstore.iec.ch/publication/62870",
        owner="International Electrotechnical Commission",
        title="IEC 60664-1 Insulation coordination for equipment within "
              "low-voltage supply systems",
        license_id="iec-standard",
        blocks="insulation coordination tables",
        offline=True,
    ),
    SourceSpec(
        key="proterial_ml95s",
        url="https://www.proterial.com/e/products/elec/ferrite.html",
        owner="Proterial, Ltd.",
        title="Proterial soft ferrite materials (ML95S)",
        license_id="proterial-datasheet",
        blocks="core material properties for the EPC reference core",
    ),
]


def bootstrap(
    register: EvidenceRegister,
    gate_log: ManualGateLog,
    cache: Optional[EvidenceCache] = None,
    use_browser: bool = True,
    display: Optional[str] = None,
) -> Dict[str, str]:
    """Attempt every source and record the outcome. Returns key -> status."""
    outcomes: Dict[str, str] = {}
    browser = None

    try:
        for spec in SOURCES:
            if spec.offline:
                register.add_source(Source(
                    key=spec.key, url=spec.url, owner=spec.owner,
                    title=spec.title, license_id=spec.license_id,
                    revision=spec.revision,
                    retrieval_method=RetrievalMethod.LOCAL_ENTRY.value,
                    status=SourceStatus.LICENSED_OFFLINE.value,
                    notes=(
                        "Held under licence. FORGE records clause references "
                        "and locally entered design-basis values only."
                    ),
                ))
                gate_log.record(ManualGate(
                    key=spec.key, url=spec.url,
                    reason=GateReason.LICENSED_STANDARD.value,
                    what_it_blocks=spec.blocks,
                    notes=(
                        "Satisfy by having a reviewer with a licensed copy "
                        "confirm the derived spacings and test voltages."
                    ),
                ))
                outcomes[spec.key] = SourceStatus.LICENSED_OFFLINE.value
                continue

            result = fetch_direct(spec.url)
            source = source_from_fetch(
                key=spec.key, result=result, owner=spec.owner,
                title=spec.title, license_id=spec.license_id,
                revision=spec.revision, cache=cache,
            )

            if source.status != SourceStatus.RETRIEVED.value and use_browser:
                if browser is None:
                    browser = _open_browser(display)
                if browser is not None:
                    page = browser.fetch(spec.url, wait_seconds=10)
                    if page.looks_like_content:
                        source.status = SourceStatus.RETRIEVED.value
                        source.retrieval_method = RetrievalMethod.BROWSER_CDP.value
                        source.final_url = page.final_url
                        source.size_bytes = len(page.html)
                        source.sha256 = __import__("hashlib").sha256(
                            page.html.encode()
                        ).hexdigest()
                        source.notes = "retrieved as rendered DOM via CDP"
                        if cache is not None:
                            source.cache_path = str(
                                cache.store(page.html.encode(), ".html")
                            )
                    elif page.challenged:
                        source.status = SourceStatus.BLOCKED.value
                        source.retrieval_method = RetrievalMethod.BROWSER_CDP.value
                        source.notes = "managed challenge; not circumvented"

            register.add_source(source)
            outcomes[spec.key] = source.status

            if source.status == SourceStatus.BLOCKED.value:
                gate_log.record(ManualGate(
                    key=spec.key, url=spec.url,
                    reason=GateReason.MANAGED_CHALLENGE.value,
                    what_it_blocks=spec.blocks,
                    notes=(
                        "Direct HTTP refused and the browser met a managed "
                        "challenge. Satisfy by supplying the document through "
                        "a licensed route and recording its hash."
                    ),
                ))
            elif source.status == SourceStatus.UNAVAILABLE.value:
                gate_log.record(ManualGate(
                    key=spec.key, url=spec.url,
                    reason=GateReason.WITHDRAWN.value,
                    what_it_blocks=spec.blocks,
                ))
    finally:
        if browser is not None:
            browser.stop()

    return outcomes


def _open_browser(display: Optional[str]):
    try:
        from ..browser.session import ChromeSession

        return ChromeSession(
            user_data_dir=Path("/tmp/forge-chrome-profile"), display=display
        ).start()
    except Exception:
        return None
