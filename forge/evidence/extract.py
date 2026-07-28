"""Retrieval and extraction helpers feeding the evidence register.

Raw source files land in a local cache that is deliberately excluded from
version control, because most of the useful datasheets are all-rights-reserved.
What gets committed is the register row: URL, hash, locator and the extracted
number.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .register import (
    EvidenceError,
    RetrievalMethod,
    Source,
    SourceStatus,
    Uncertainty,
    sha256_bytes,
    utc_now,
)

BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)

#: Signals that a response is an anti-bot interstitial rather than content.
_CHALLENGE_MARKERS = (
    b"cf-browser-verification",
    b"Just a moment...",
    b"Checking your browser",
    b"__cf_chl",
    b"Enable JavaScript and cookies to continue",
)


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    body: bytes
    media_type: str
    blocked: bool
    reason: str = ""

    @property
    def sha256(self) -> str:
        return sha256_bytes(self.body)

    @property
    def size(self) -> int:
        return len(self.body)


class EvidenceCache:
    """Content-addressed store for retrieved source files.

    Never published. The register keeps the hash so a future run can prove it
    read the same bytes without the repository carrying the document.
    """

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        gitignore = self.root / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(
                "# Retrieved source documents are mostly all-rights-reserved.\n"
                "# The evidence register keeps hashes and citations instead.\n"
                "*\n!.gitignore\n"
            )

    def path_for(self, digest: str, suffix: str = "") -> Path:
        return self.root / f"{digest[:16]}{suffix}"

    def store(self, body: bytes, suffix: str = "") -> Path:
        digest = sha256_bytes(body)
        path = self.path_for(digest, suffix)
        if not path.exists():
            path.write_bytes(body)
        return path

    def has(self, digest: str, suffix: str = "") -> bool:
        return self.path_for(digest, suffix).exists()


def fetch_direct(
    url: str,
    timeout: float = 45.0,
    accept: str = "text/html,application/xhtml+xml,application/pdf,*/*",
) -> FetchResult:
    """Plain HTTP GET with browser-like headers.

    Returns ``blocked=True`` rather than raising when the far side serves a
    challenge page, so the caller can record a manual gate instead of
    pretending the retrieval succeeded.
    """
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": BROWSER_UA,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ctx) as resp:
            body = resp.read()
            final_url = resp.geturl()
            media = resp.headers.get_content_type()
            status = resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        return FetchResult(
            url=url, final_url=url, status=exc.code, body=body,
            media_type="", blocked=exc.code in (403, 406, 429),
            reason=f"HTTP {exc.code} {exc.reason}",
        )
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as exc:
        return FetchResult(
            url=url, final_url=url, status=0, body=b"", media_type="",
            blocked=True, reason=f"transport error: {exc}",
        )

    blocked = any(marker in body[:20000] for marker in _CHALLENGE_MARKERS)
    return FetchResult(
        url=url, final_url=final_url, status=status, body=body,
        media_type=media, blocked=blocked,
        reason="anti-bot interstitial" if blocked else "",
    )


def source_from_fetch(
    key: str,
    result: FetchResult,
    owner: str,
    title: str,
    license_id: str,
    revision: str = "",
    cache: Optional[EvidenceCache] = None,
    retrieval_method: str = RetrievalMethod.DIRECT_HTTP.value,
    notes: str = "",
) -> Source:
    """Build a register Source row from a retrieval attempt."""
    cache_path = ""
    if cache is not None and result.body and not result.blocked:
        suffix = ".pdf" if "pdf" in result.media_type else ""
        cache_path = str(cache.store(result.body, suffix))

    if result.blocked:
        status = SourceStatus.BLOCKED.value
    elif result.status == 200 and result.body:
        status = SourceStatus.RETRIEVED.value
    else:
        status = SourceStatus.UNAVAILABLE.value

    combined_notes = notes
    if result.reason:
        combined_notes = f"{notes} [{result.reason}]".strip()

    return Source(
        key=key,
        url=result.url,
        final_url=result.final_url,
        owner=owner,
        title=title,
        license_id=license_id,
        revision=revision,
        access_time=utc_now(),
        sha256=result.sha256 if result.body else "",
        media_type=result.media_type,
        size_bytes=result.size,
        retrieval_method=retrieval_method,
        status=status,
        cache_path=cache_path,
        notes=combined_notes,
    )


# --------------------------------------------------------------------- PDF

def pdf_text_pymupdf(path: Path) -> Optional[List[str]]:
    """Per-page text via PyMuPDF, or None when the library is unavailable."""
    try:
        import fitz  # type: ignore
    except ImportError:
        return None
    pages: List[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            pages.append(page.get_text())
    return pages


def pdf_text_fallback(path: Path) -> List[str]:
    """Crude stdlib text recovery for when PyMuPDF is not installed.

    Inflates FlateDecode streams and pulls literal strings out of the content
    operators. Page boundaries are approximate, so any fact extracted this way
    should record ``ExtractionMethod.PDF_TEXT`` with a wider uncertainty and a
    human check.
    """
    raw = path.read_bytes()
    chunks: List[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        try:
            chunks.append(zlib.decompress(match.group(1)).decode("latin-1"))
        except Exception:
            continue
    text: List[str] = []
    for chunk in chunks:
        literals = re.findall(r"\((?:[^()\\]|\\.)*\)", chunk)
        if literals:
            text.append(" ".join(lit[1:-1] for lit in literals))
    return text


def pdf_pages(path: Path) -> List[str]:
    pages = pdf_text_pymupdf(path)
    if pages is not None:
        return pages
    return pdf_text_fallback(path)


def find_in_pdf(pages: Sequence[str], pattern: str) -> List[Tuple[int, str]]:
    """Return (page_number, matching line) for a regex across a PDF."""
    hits: List[Tuple[int, str]] = []
    regex = re.compile(pattern, re.I)
    for index, page in enumerate(pages, start=1):
        for line in page.splitlines():
            if regex.search(line):
                hits.append((index, line.strip()))
    return hits


# ------------------------------------------------------- curve digitization

@dataclass
class DigitizedCurve:
    """A datasheet graph read back into numbers.

    Datasheet loss curves are printed as log-log plots. Reading them costs
    accuracy, and that cost has to travel with the numbers, so this class
    carries an explicit relative uncertainty and the domain it was read over.
    """

    name: str
    x: List[float]
    y: List[float]
    x_unit: str
    y_unit: str
    x_log: bool = True
    y_log: bool = True
    relative_uncertainty: float = 0.15
    conditions: Dict[str, Any] = None  # type: ignore[assignment]
    source_key: str = ""

    def __post_init__(self) -> None:
        if self.conditions is None:
            self.conditions = {}
        if len(self.x) != len(self.y):
            raise EvidenceError(f"curve '{self.name}': x and y length mismatch")
        if len(self.x) < 2:
            raise EvidenceError(f"curve '{self.name}': need at least two points")
        if any(a >= b for a, b in zip(self.x, self.x[1:])):
            raise EvidenceError(f"curve '{self.name}': x must increase strictly")

    @property
    def domain(self) -> Tuple[float, float]:
        return self.x[0], self.x[-1]

    def uncertainty(self) -> Uncertainty:
        return Uncertainty(
            kind="relative",
            value=self.relative_uncertainty,
            basis=(
                f"log-log graph digitization of {self.name}; includes reading "
                "error and typical-value spread"
            ),
        )

    def interpolate(self, x: float, allow_extrapolation: bool = False) -> float:
        lo, hi = self.domain
        if not allow_extrapolation and not (lo <= x <= hi):
            raise EvidenceError(
                f"curve '{self.name}' covers {self.x_unit} in [{lo:g}, {hi:g}]; "
                f"asked for {x:g}. Extrapolation is rejected by default."
            )
        x = min(max(x, lo), hi)
        for i in range(len(self.x) - 1):
            x0, x1 = self.x[i], self.x[i + 1]
            if x0 <= x <= x1:
                y0, y1 = self.y[i], self.y[i + 1]
                if self.x_log and self.y_log and x0 > 0 and y0 > 0 and y1 > 0:
                    import math
                    t = (math.log(x) - math.log(x0)) / (math.log(x1) - math.log(x0))
                    return math.exp(math.log(y0) + t * (math.log(y1) - math.log(y0)))
                t = (x - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)
        return self.y[-1]

    def to_json(self) -> str:
        return json.dumps(
            {
                "name": self.name, "x": self.x, "y": self.y,
                "x_unit": self.x_unit, "y_unit": self.y_unit,
                "x_log": self.x_log, "y_log": self.y_log,
                "relative_uncertainty": self.relative_uncertainty,
                "conditions": self.conditions, "source_key": self.source_key,
            }
        )

    @staticmethod
    def from_json(payload: str) -> "DigitizedCurve":
        return DigitizedCurve(**json.loads(payload))
