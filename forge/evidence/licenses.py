"""Redistribution policy for every evidence source.

A browser that gets past an HTTP 403 has not acquired a redistribution right.
This module is the single place where "may we republish this?" is decided, so
that the report generator can mechanically refuse to emit protected material.

Three permissions are tracked separately because publishers grant them
separately:

``redistribute_source``
    May the original file (PDF, image) be committed or shipped in a report?
``redistribute_excerpt``
    May verbatim tables, figures or artwork be reproduced?
``publish_derived_values``
    May numeric facts extracted from the document be published with citation?

The default for an unknown source is the most restrictive combination, so a
source that nobody has classified cannot leak into published output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class LicensePolicy:
    """Redistribution terms for one publisher or document family."""

    license_id: str
    owner: str
    summary: str
    redistribute_source: bool
    redistribute_excerpt: bool
    publish_derived_values: bool
    terms_url: Optional[str] = None
    notes: str = ""

    def blocks_publication_of_source(self) -> bool:
        return not self.redistribute_source

    def describe(self) -> str:
        flags = []
        flags.append("source" if self.redistribute_source else "no-source")
        flags.append("excerpt" if self.redistribute_excerpt else "no-excerpt")
        flags.append("derived" if self.publish_derived_values else "no-derived")
        return f"{self.license_id} ({', '.join(flags)})"


#: Most restrictive fallback. Any source not explicitly classified gets this.
UNKNOWN = LicensePolicy(
    license_id="unknown",
    owner="unclassified",
    summary=(
        "Source has not been classified. Treated as all-rights-reserved: no "
        "redistribution of the file, no verbatim excerpts, and derived values "
        "may not be published until a policy is recorded."
    ),
    redistribute_source=False,
    redistribute_excerpt=False,
    publish_derived_values=False,
)


_POLICIES: Dict[str, LicensePolicy] = {
    policy.license_id: policy
    for policy in [
        UNKNOWN,
        LicensePolicy(
            license_id="ocp-owfa-1.0-modified",
            owner="Open Compute Project Foundation",
            summary=(
                "OCP specifications are published under a modified Open Web "
                "Foundation agreement. Specification text is broadly available "
                "but appendices may be excluded from the grant, so the safe "
                "default here is to publish derived requirements with citation "
                "rather than redistributing the document."
            ),
            redistribute_source=False,
            redistribute_excerpt=False,
            publish_derived_values=True,
            terms_url="https://www.opencompute.org/documents/"
            "ocp-specification-diablo-400-v0-7-0-final-pdf",
            notes=(
                "Verify the applicable Final Specification Agreement before "
                "reproducing any appendix content."
            ),
        ),
        LicensePolicy(
            license_id="ti-technical-resource",
            owner="Texas Instruments Incorporated",
            summary=(
                "TI grants permission to use technical resources only for "
                "developing applications that use TI products. The notice "
                "expressly prohibits other reproduction and display."
            ),
            redistribute_source=False,
            redistribute_excerpt=False,
            publish_derived_values=True,
            terms_url="https://www.ti.com/lit/ta/ssztd94/ssztd94.pdf",
            notes="Cite document number and figure; never reproduce artwork.",
        ),
        LicensePolicy(
            license_id="epc-all-rights-reserved",
            owner="Efficient Power Conversion Corporation",
            summary=(
                "EPC website and document content is all-rights-reserved. "
                "Device SPICE models are offered for design use."
            ),
            redistribute_source=False,
            redistribute_excerpt=False,
            publish_derived_values=True,
            terms_url="https://epc-co.com/epc/terms.aspx",
        ),
        LicensePolicy(
            license_id="tdk-datasheet",
            owner="TDK Electronics AG",
            summary=(
                "TDK datasheets prohibit reproduction, publication and "
                "dissemination without prior written consent."
            ),
            redistribute_source=False,
            redistribute_excerpt=False,
            publish_derived_values=True,
            notes="Record datasheet edition; values are typical unless stated.",
        ),
        LicensePolicy(
            license_id="ferroxcube-restricted",
            owner="Ferroxcube International Holding B.V.",
            summary=(
                "Ferroxcube restricts copying and display to narrow personal, "
                "non-commercial use."
            ),
            redistribute_source=False,
            redistribute_excerpt=False,
            publish_derived_values=True,
            terms_url="https://www.ferroxcube.com/en-global/Terms_of_use/index",
        ),
        LicensePolicy(
            license_id="magnetics-catalog",
            owner="Magnetics (Spang & Company)",
            summary="Copyrighted product literature, all rights reserved.",
            redistribute_source=False,
            redistribute_excerpt=False,
            publish_derived_values=True,
        ),
        LicensePolicy(
            license_id="dmegc-datasheet",
            owner="DMEGC Magnetics",
            summary="Copyrighted product literature, all rights reserved.",
            redistribute_source=False,
            redistribute_excerpt=False,
            publish_derived_values=True,
            notes="DMR51 is a DMEGC material. Do not attribute it to TDK.",
        ),
        LicensePolicy(
            license_id="navitas-paper",
            owner="Navitas Semiconductor",
            summary=(
                "Conference paper hosted by the vendor with no general "
                "redistribution grant."
            ),
            redistribute_source=False,
            redistribute_excerpt=False,
            publish_derived_values=True,
        ),
        LicensePolicy(
            license_id="iec-standard",
            owner="International Electrotechnical Commission",
            summary=(
                "IEC standards are sold under licence. Clause numbers and the "
                "fact that a requirement exists may be cited, but tables and "
                "text may not be reproduced."
            ),
            redistribute_source=False,
            redistribute_excerpt=False,
            publish_derived_values=False,
            notes=(
                "Creepage and clearance tables must be read from a licensed "
                "copy. FORGE stores only locally entered design-basis values "
                "flagged as ASSUMED until a licensed reviewer confirms them."
            ),
        ),
        LicensePolicy(
            license_id="forge-internal",
            owner="FORGE project",
            summary="Values computed or assumed inside this repository.",
            redistribute_source=True,
            redistribute_excerpt=True,
            publish_derived_values=True,
        ),
        LicensePolicy(
            license_id="public-domain-usgov",
            owner="United States Government",
            summary="US federal government work, not subject to copyright.",
            redistribute_source=True,
            redistribute_excerpt=True,
            publish_derived_values=True,
        ),
    ]
}


def get(license_id: Optional[str]) -> LicensePolicy:
    """Return a policy, falling back to the most restrictive one."""
    if not license_id:
        return UNKNOWN
    return _POLICIES.get(license_id, UNKNOWN)


def register(policy: LicensePolicy) -> None:
    """Add or replace a policy at runtime."""
    _POLICIES[policy.license_id] = policy


def all_policies() -> Dict[str, LicensePolicy]:
    return dict(_POLICIES)


class RedistributionError(RuntimeError):
    """Raised when publication of restricted material is attempted."""


def assert_publishable_value(license_id: Optional[str], what: str) -> None:
    policy = get(license_id)
    if not policy.publish_derived_values:
        raise RedistributionError(
            f"Publishing derived values from {what} is not permitted under "
            f"{policy.license_id} ({policy.owner}). {policy.summary}"
        )


def assert_publishable_source(license_id: Optional[str], what: str) -> None:
    policy = get(license_id)
    if not policy.redistribute_source:
        raise RedistributionError(
            f"Redistributing the source file for {what} is not permitted under "
            f"{policy.license_id} ({policy.owner}). {policy.summary}"
        )
