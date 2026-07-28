"""Real prices, stock and lead times for the parts in one converter cell.

Most large distributors block automated browsing outright: Mouser returns an
explicit "access denied" page to a real headful browser, Digi-Key serves a
managed challenge, Arrow and RS return 403. Rather than fight that, this module
buys from the people who publish prices themselves. EPC, Texas Instruments,
Monolithic Power and Microchip all sell direct and publish quantity ladders.

Anything that cannot be retrieved becomes a manual gate with a named reason. A
missing price is never estimated, because a made-up cost is worse than an
obvious hole in a cost model.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class PriceBreak:
    quantity: int
    unit_price_usd: float


@dataclass
class PartQuote:
    """What one vendor says a part costs today."""

    mpn: str
    manufacturer: str
    role: str
    qty_per_cell: int
    source: str
    url: str
    breaks: List[PriceBreak] = field(default_factory=list)
    stock: Optional[int] = None
    lead_time_weeks: Optional[float] = None
    currency: str = "USD"
    retrieved_at: str = ""
    sha256: str = ""
    status: str = "quoted"          # quoted | blocked | unavailable
    note: str = ""

    def price_at(self, quantity: int) -> Optional[float]:
        """Unit price at a given order quantity, using the applicable break."""
        applicable = [b for b in self.breaks if b.quantity <= quantity]
        if not applicable:
            return self.breaks[0].unit_price_usd if self.breaks else None
        return max(applicable, key=lambda b: b.quantity).unit_price_usd

    def extended_at(self, cells: int, quantity_basis: int) -> Optional[float]:
        """Cost of this part per converter, at a build volume."""
        unit = self.price_at(quantity_basis)
        if unit is None:
            return None
        return unit * self.qty_per_cell * cells

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["breaks"] = [asdict(b) for b in self.breaks]
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(markup: str) -> str:
    stripped = re.sub(r"<script.*?</script>", " ", markup, flags=re.S | re.I)
    stripped = re.sub(r"<style.*?</style>", " ", stripped, flags=re.S | re.I)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", stripped)).split())


def _int(raw: str) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else None


# ----------------------------------------------------------- extractors

def extract_epc(markup: str) -> Tuple[List[PriceBreak], Optional[int], str]:
    """EPC publishes a `priceBreaks` table and a live stock figure."""
    breaks: List[PriceBreak] = []
    table = re.search(r'<table id="priceBreaks".*?</table>', markup, re.S | re.I)
    if table:
        for qty, price in re.findall(
            r'<td class="qty">([\d,]+)</td>\s*<td class="price">\$?([\d.]+)</td>',
            table.group(0), re.I,
        ):
            quantity = _int(qty)
            if quantity:
                breaks.append(PriceBreak(quantity, float(price)))
    stock = None
    match = re.search(r'id="dkStock"[^>]*>([\d,]+)<', markup)
    if match:
        stock = _int(match.group(1))
    return breaks, stock, "manufacturer direct, fulfilled through Digi-Key"


def extract_ti(markup: str) -> Tuple[List[PriceBreak], Optional[int], str]:
    """TI shows a quantity ladder and its own inventory on the product page."""
    breaks: List[PriceBreak] = []
    text = _text(markup)
    for qty, price in re.findall(
        r"(\d[\d,]*)\s*(?:-|to)?\s*[\d,]*\s*\|?\s*\$\s?([\d.]+)", text
    ):
        quantity = _int(qty)
        if quantity and 1 <= quantity <= 1_000_000 and float(price) < 1000:
            breaks.append(PriceBreak(quantity, float(price)))
    seen: Dict[int, float] = {}
    for b in breaks:
        seen.setdefault(b.quantity, b.unit_price_usd)
    ordered = [PriceBreak(q, p) for q, p in sorted(seen.items())][:8]
    stock = None
    match = re.search(r"([\d,]+)\s*(?:in stock|available)", text, re.I)
    if match:
        stock = _int(match.group(1))
    return ordered, stock, "manufacturer direct"


def extract_generic(markup: str) -> Tuple[List[PriceBreak], Optional[int], str]:
    text = _text(markup)
    breaks: List[PriceBreak] = []
    for qty, price in re.findall(
        r"(\d[\d,]*)\s*\+?\s*\$\s?([\d.]+)", text
    ):
        quantity = _int(qty)
        if quantity and float(price) < 10000:
            breaks.append(PriceBreak(quantity, float(price)))
    stock = None
    match = re.search(r"([\d,]+)\s*in stock", text, re.I)
    if match:
        stock = _int(match.group(1))
    return breaks[:8], stock, "generic extraction"


def validate_ladder(breaks: Sequence[PriceBreak]) -> Tuple[bool, str]:
    """Reject a price ladder that does not behave like one.

    Scraping a page for "number near a dollar sign" happily returns shipping
    thresholds, part numbers and unrelated products. A genuine quantity ladder
    rises in quantity and never rises in unit price. Anything else means the
    extraction grabbed the wrong numbers, and a wrong price is worse than a
    missing one.
    """
    if len(breaks) < 2:
        return len(breaks) == 1, "single price point, no ladder to check"
    ordered = sorted(breaks, key=lambda b: b.quantity)
    for earlier, later in zip(ordered, ordered[1:]):
        if later.unit_price_usd > earlier.unit_price_usd * 1.001:
            return False, (
                f"unit price rises from ${earlier.unit_price_usd:.4f} at qty "
                f"{earlier.quantity} to ${later.unit_price_usd:.4f} at qty "
                f"{later.quantity}, so this is not a quantity ladder"
            )
    if ordered[0].unit_price_usd <= 0:
        return False, "zero or negative price"
    spread = ordered[0].unit_price_usd / ordered[-1].unit_price_usd
    if spread > 100:
        return False, f"implausible {spread:.0f}x spread across the ladder"
    return True, "monotonic and plausible"


DENIAL_MARKERS = (
    "access to this page has been denied",
    "are you a human",
    "verify you are human",
    "just a moment",
    "unusual traffic",
)


@dataclass(frozen=True)
class BomLine:
    mpn: str
    manufacturer: str
    role: str
    qty_per_cell: int
    url: str
    extractor: str = "generic"
    note: str = ""


#: One ISOP cell of the EPC91123-like converter. Quantities per cell come from
#: the published kit bill of materials; the transformer itself is the PCB and
#: the core, not a purchased component.
CELL_BOM: List[BomLine] = [
    BomLine("EPC2305", "EPC", "Primary half-bridge GaN FET, 150 V", 2,
            "https://epc-co.com/epc/products/gan-fets-and-ics/epc2305", "epc"),
    BomLine("EPC2366", "EPC", "Secondary synchronous rectifier GaN FET, 40 V", 4,
            "https://epc-co.com/epc/products/gan-fets-and-ics/epc2366", "epc"),
    BomLine("LMG1020", "Texas Instruments", "Low-side gate driver", 2,
            "https://www.ti.com/product/LMG1020", "ti"),
    BomLine("ISO7740", "Texas Instruments", "Four-channel digital isolator", 0,
            "https://www.ti.com/product/ISO7740", "ti",
            "Two per converter, shared across the eight cells"),
    BomLine("MP18831", "Monolithic Power Systems",
            "Isolated two-channel gate driver", 1,
            "https://www.monolithicpower.com/en/products/mp18831.html",
            "generic"),
    BomLine("DSPIC33CK256MP605", "Microchip", "Converter controller", 0,
            "https://www.microchip.com/en-us/product/dspic33ck256mp605",
            "generic", "One per converter, shared across the eight cells"),
    BomLine("MIE1W0505BGLVH", "Murata", "Isolated 5 V bias supply, 1 W", 1,
            "https://www.murata.com/en-eu/products/productdetail?partno=MIE1W0505BGLVH",
            "generic"),
    BomLine("ELP18/4/10-3F46", "Ferroxcube",
            "Planar ferrite core set for the transformer", 2,
            "https://www.ferroxcube.com/en-global/products_ferroxcube/stepTwo/planar_e_cores",
            "generic",
            "Core geometry is catalogued from the TDK equivalent; Ferroxcube "
            "does not publish prices and distributors block automation"),
]

EXTRACTORS: Dict[str, Callable[[str], Tuple[List[PriceBreak], Optional[int], str]]] = {
    "epc": extract_epc,
    "ti": extract_ti,
    "generic": extract_generic,
}


def harvest(
    lines: Sequence[BomLine] = tuple(CELL_BOM),
    display: Optional[str] = ":1",
    wait_seconds: float = 10.0,
) -> List[PartQuote]:
    """Fetch every line through a real browser and parse what it publishes."""
    from ..browser.session import ChromeSession

    quotes: List[PartQuote] = []
    session = ChromeSession(
        user_data_dir=Path("/tmp/forge-src-profile"), display=display
    ).start()
    try:
        for line in lines:
            quote = PartQuote(
                mpn=line.mpn, manufacturer=line.manufacturer, role=line.role,
                qty_per_cell=line.qty_per_cell, source=line.manufacturer,
                url=line.url, retrieved_at=_now(), note=line.note,
            )
            try:
                page = session.fetch(line.url, wait_seconds=wait_seconds)
            except Exception as exc:
                quote.status = "unavailable"
                quote.note = f"{quote.note} [fetch failed: {exc}]".strip()
                quotes.append(quote)
                continue

            quote.sha256 = hashlib.sha256(page.html.encode()).hexdigest()
            lowered = _text(page.html).lower()
            if page.challenged or any(m in lowered for m in DENIAL_MARKERS):
                quote.status = "blocked"
                quote.note = (
                    f"{quote.note} [vendor blocked automated access; a price "
                    "needs an API key or a human]"
                ).strip()
                quotes.append(quote)
                continue

            breaks, stock, how = EXTRACTORS[line.extractor](page.html)
            quote.stock = stock
            valid, reason = validate_ladder(breaks)
            if breaks and valid:
                quote.breaks = breaks
                quote.status = "quoted"
                quote.note = f"{quote.note} [{how}]".strip()
            elif breaks and not valid:
                quote.status = "unavailable"
                quote.note = (
                    f"{quote.note} [extraction rejected: {reason}]"
                ).strip()
            else:
                quote.status = "unavailable"
                quote.note = (
                    f"{quote.note} [page retrieved but published no price ladder]"
                ).strip()
            quotes.append(quote)
    finally:
        session.stop()
    return quotes


def save(quotes: Sequence[PartQuote], path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(
        {"retrieved_at": _now(), "quotes": [q.to_dict() for q in quotes]},
        indent=1,
    ))
    return path


def load(path: Path | str) -> List[PartQuote]:
    payload = json.loads(Path(path).read_text())
    out: List[PartQuote] = []
    for row in payload.get("quotes", []):
        breaks = [PriceBreak(**b) for b in row.pop("breaks", [])]
        out.append(PartQuote(breaks=breaks, **row))
    return out
