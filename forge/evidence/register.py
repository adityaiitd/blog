"""The evidence register: every number FORGE uses must come from here.

Two tables. ``sources`` records where a document came from and what may be
done with it. ``facts`` records individual values pulled out of a source,
each tagged with how it was obtained, where on the page it lives, how
uncertain it is, and over what domain it is valid.

The register enforces three rules that the rest of the pipeline relies on:

1. A fact classified ``SOURCED`` must point at a real source row. Only
   ``ASSUMED`` and ``DERIVED`` facts may stand alone.
2. Publication is checked against the source licence, not against intent.
3. A fact carrying a validity domain refuses to be evaluated outside it,
   so digitized material curves cannot be silently extrapolated.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from . import licenses


class ValueClass(str, Enum):
    """Where a value came from. Reports must show this next to every number."""

    SOURCED = "sourced"     # read directly out of a cited document
    DERIVED = "derived"     # computed from other registered facts
    ASSUMED = "assumed"     # a project decision, not backed by a source


class RetrievalMethod(str, Enum):
    DIRECT_HTTP = "direct_http"
    OFFICIAL_API = "official_api"
    BROWSER_CDP = "browser_cdp"
    MANUAL_GATE = "manual_gate"   # a human cleared a challenge or supplied it
    LOCAL_ENTRY = "local_entry"   # typed in from a licensed copy


class ExtractionMethod(str, Enum):
    PDF_TEXT = "pdf_text"
    PDF_TABLE = "pdf_table"
    CURVE_DIGITIZED = "curve_digitized"
    HTML_PARSE = "html_parse"
    API_FIELD = "api_field"
    HUMAN_READ = "human_read"
    COMPUTED = "computed"


class SourceStatus(str, Enum):
    RETRIEVED = "retrieved"
    BLOCKED = "blocked"           # challenge/CAPTCHA, not circumvented
    UNAVAILABLE = "unavailable"   # 404, withdrawn, paywalled
    LICENSED_OFFLINE = "licensed_offline"  # standard held under licence


class EvidenceError(RuntimeError):
    pass


class DomainError(EvidenceError):
    """Raised when a fact is used outside its stated validity domain."""


@dataclass(frozen=True)
class Uncertainty:
    """How wrong a value might be, and why.

    ``kind`` is one of ``absolute``, ``relative`` or ``interval``. ``basis``
    explains the origin: instrument spec, datasheet tolerance, digitization
    error, fit residual, or an engineering judgement.
    """

    kind: str
    value: float = 0.0
    low: Optional[float] = None
    high: Optional[float] = None
    confidence: float = 0.95
    basis: str = ""

    def bounds(self, nominal: float) -> Tuple[float, float]:
        if self.kind == "absolute":
            return nominal - self.value, nominal + self.value
        if self.kind == "relative":
            delta = abs(nominal) * self.value
            return nominal - delta, nominal + delta
        if self.kind == "interval":
            if self.low is None or self.high is None:
                raise EvidenceError("interval uncertainty needs low and high")
            return self.low, self.high
        raise EvidenceError(f"unknown uncertainty kind: {self.kind}")

    def relative_to(self, nominal: float) -> float:
        """Half-width as a fraction of the nominal value."""
        lo, hi = self.bounds(nominal)
        if nominal == 0:
            return float("inf") if hi != lo else 0.0
        return (hi - lo) / 2.0 / abs(nominal)

    @staticmethod
    def none() -> "Uncertainty":
        return Uncertainty(kind="absolute", value=0.0, basis="exact by definition")


@dataclass(frozen=True)
class Locator:
    """Where in the document the value sits."""

    page: Optional[int] = None
    figure: Optional[str] = None
    table: Optional[str] = None
    section: Optional[str] = None
    bbox: Optional[Sequence[float]] = None   # x0, y0, x1, y1 in PDF points

    def describe(self) -> str:
        bits = []
        if self.page is not None:
            bits.append(f"p.{self.page}")
        if self.section:
            bits.append(f"§{self.section}")
        if self.table:
            bits.append(f"Table {self.table}")
        if self.figure:
            bits.append(f"Figure {self.figure}")
        return ", ".join(bits) if bits else "location not recorded"


@dataclass
class Source:
    key: str
    url: str
    owner: str
    title: str
    license_id: str
    revision: str = ""
    final_url: str = ""
    access_time: str = ""
    sha256: str = ""
    media_type: str = ""
    size_bytes: int = 0
    retrieval_method: str = RetrievalMethod.DIRECT_HTTP.value
    status: str = SourceStatus.RETRIEVED.value
    cache_path: str = ""
    notes: str = ""

    def policy(self) -> licenses.LicensePolicy:
        return licenses.get(self.license_id)

    def citation(self) -> str:
        rev = f", rev {self.revision}" if self.revision else ""
        return f"{self.owner}, \"{self.title}\"{rev} ({self.url})"


@dataclass
class Fact:
    key: str
    value: Any
    unit: str = ""
    value_class: str = ValueClass.SOURCED.value
    source_key: Optional[str] = None
    extraction_method: str = ExtractionMethod.HUMAN_READ.value
    locator: Locator = field(default_factory=Locator)
    uncertainty: Uncertainty = field(default_factory=Uncertainty.none)
    domain: Dict[str, Sequence[float]] = field(default_factory=dict)
    typical: bool = True          # typical vs guaranteed/limit value
    notes: str = ""

    def check_domain(self, **conditions: float) -> None:
        """Raise if the requested conditions fall outside the stated domain."""
        for name, value in conditions.items():
            if name not in self.domain:
                continue
            lo, hi = self.domain[name][0], self.domain[name][1]
            if value < lo or value > hi:
                raise DomainError(
                    f"fact '{self.key}' is only valid for {name} in "
                    f"[{lo:g}, {hi:g}]; asked for {value:g}. Extrapolation is "
                    "rejected by default."
                )

    def bounds(self) -> Tuple[float, float]:
        if not isinstance(self.value, (int, float)):
            raise EvidenceError(f"fact '{self.key}' is not numeric")
        return self.uncertainty.bounds(float(self.value))


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    key              TEXT PRIMARY KEY,
    url              TEXT NOT NULL,
    final_url        TEXT,
    owner            TEXT NOT NULL,
    title            TEXT NOT NULL,
    revision         TEXT,
    license_id       TEXT NOT NULL,
    access_time      TEXT NOT NULL,
    sha256           TEXT,
    media_type       TEXT,
    size_bytes       INTEGER,
    retrieval_method TEXT NOT NULL,
    status           TEXT NOT NULL,
    cache_path       TEXT,
    notes            TEXT
);

CREATE TABLE IF NOT EXISTS facts (
    key               TEXT PRIMARY KEY,
    value_json        TEXT NOT NULL,
    unit              TEXT,
    value_class       TEXT NOT NULL,
    source_key        TEXT,
    extraction_method TEXT NOT NULL,
    locator_json      TEXT,
    uncertainty_json  TEXT,
    domain_json       TEXT,
    typical           INTEGER,
    notes             TEXT,
    recorded_at       TEXT NOT NULL,
    FOREIGN KEY (source_key) REFERENCES sources(key)
);

CREATE INDEX IF NOT EXISTS facts_by_source ON facts(source_key);
CREATE INDEX IF NOT EXISTS facts_by_class ON facts(value_class);
"""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EvidenceRegister:
    """SQLite-backed store of sources and the facts extracted from them."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "EvidenceRegister":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ---------------------------------------------------------------- sources

    def add_source(self, source: Source) -> Source:
        if not source.access_time:
            source.access_time = utc_now()
        if licenses.get(source.license_id) is licenses.UNKNOWN and (
            source.license_id != licenses.UNKNOWN.license_id
        ):
            raise EvidenceError(
                f"source '{source.key}' names licence '{source.license_id}' "
                "which is not registered. Add a LicensePolicy first so the "
                "report generator knows what may be published."
            )
        self._conn.execute(
            """INSERT OR REPLACE INTO sources
               (key, url, final_url, owner, title, revision, license_id,
                access_time, sha256, media_type, size_bytes,
                retrieval_method, status, cache_path, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                source.key, source.url, source.final_url, source.owner,
                source.title, source.revision, source.license_id,
                source.access_time, source.sha256, source.media_type,
                source.size_bytes, source.retrieval_method, source.status,
                source.cache_path, source.notes,
            ),
        )
        self._conn.commit()
        return source

    def get_source(self, key: str) -> Optional[Source]:
        row = self._conn.execute(
            "SELECT * FROM sources WHERE key = ?", (key,)
        ).fetchone()
        return _row_to_source(row) if row else None

    def sources(self) -> List[Source]:
        rows = self._conn.execute("SELECT * FROM sources ORDER BY key").fetchall()
        return [_row_to_source(r) for r in rows]

    # ------------------------------------------------------------------ facts

    def add_fact(self, fact: Fact) -> Fact:
        if fact.value_class == ValueClass.SOURCED.value:
            if not fact.source_key:
                raise EvidenceError(
                    f"fact '{fact.key}' is SOURCED but names no source"
                )
            if self.get_source(fact.source_key) is None:
                raise EvidenceError(
                    f"fact '{fact.key}' points at unknown source "
                    f"'{fact.source_key}'"
                )
        self._conn.execute(
            """INSERT OR REPLACE INTO facts
               (key, value_json, unit, value_class, source_key,
                extraction_method, locator_json, uncertainty_json,
                domain_json, typical, notes, recorded_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                fact.key, json.dumps(fact.value), fact.unit, fact.value_class,
                fact.source_key, fact.extraction_method,
                json.dumps(asdict(fact.locator)),
                json.dumps(asdict(fact.uncertainty)),
                json.dumps({k: list(v) for k, v in fact.domain.items()}),
                int(fact.typical), fact.notes, utc_now(),
            ),
        )
        self._conn.commit()
        return fact

    def add_facts(self, facts: Iterable[Fact]) -> None:
        for fact in facts:
            self.add_fact(fact)

    def get_fact(self, key: str) -> Optional[Fact]:
        row = self._conn.execute(
            "SELECT * FROM facts WHERE key = ?", (key,)
        ).fetchone()
        return _row_to_fact(row) if row else None

    def require(self, key: str, **conditions: float) -> Fact:
        """Fetch a fact, refusing use outside its validity domain."""
        fact = self.get_fact(key)
        if fact is None:
            raise EvidenceError(
                f"required fact '{key}' is not in the register. Record it as "
                "SOURCED with a citation, or explicitly as ASSUMED."
            )
        if conditions:
            fact.check_domain(**conditions)
        return fact

    def value(self, key: str, **conditions: float) -> Any:
        return self.require(key, **conditions).value

    def facts(self, prefix: str = "") -> List[Fact]:
        if prefix:
            rows = self._conn.execute(
                "SELECT * FROM facts WHERE key LIKE ? ORDER BY key",
                (f"{prefix}%",),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM facts ORDER BY key"
            ).fetchall()
        return [_row_to_fact(r) for r in rows]

    # ------------------------------------------------------------- publishing

    def assert_publishable(self, fact_key: str) -> None:
        """Refuse to publish a value whose source forbids it."""
        fact = self.require(fact_key)
        if fact.value_class != ValueClass.SOURCED.value:
            return
        source = self.get_source(fact.source_key or "")
        if source is None:
            raise EvidenceError(f"fact '{fact_key}' has no resolvable source")
        licenses.assert_publishable_value(source.license_id, source.citation())

    def publication_audit(self) -> Dict[str, List[str]]:
        """List facts that may not be published, grouped by reason."""
        blocked: Dict[str, List[str]] = {}
        for fact in self.facts():
            if fact.value_class != ValueClass.SOURCED.value:
                continue
            source = self.get_source(fact.source_key or "")
            if source is None:
                blocked.setdefault("unresolved source", []).append(fact.key)
                continue
            policy = source.policy()
            if not policy.publish_derived_values:
                blocked.setdefault(policy.license_id, []).append(fact.key)
        return blocked

    # ---------------------------------------------------------------- summary

    def summary(self) -> Dict[str, Any]:
        counts = {
            row["value_class"]: row["n"]
            for row in self._conn.execute(
                "SELECT value_class, COUNT(*) AS n FROM facts GROUP BY value_class"
            )
        }
        statuses = {
            row["status"]: row["n"]
            for row in self._conn.execute(
                "SELECT status, COUNT(*) AS n FROM sources GROUP BY status"
            )
        }
        return {
            "sources": sum(statuses.values()),
            "sources_by_status": statuses,
            "facts": sum(counts.values()),
            "facts_by_class": counts,
            "unpublishable": self.publication_audit(),
        }

    def provenance_table(self) -> List[Dict[str, str]]:
        """Citation rows for the report appendix, with no protected content."""
        out: List[Dict[str, str]] = []
        for fact in self.facts():
            source = self.get_source(fact.source_key or "") if fact.source_key else None
            out.append(
                {
                    "fact": fact.key,
                    "value": f"{fact.value} {fact.unit}".strip(),
                    "class": fact.value_class,
                    "citation": source.citation() if source else "(no source)",
                    "locator": fact.locator.describe(),
                    "method": fact.extraction_method,
                    "uncertainty": fact.uncertainty.basis or "not stated",
                }
            )
        return out


def _row_to_source(row: sqlite3.Row) -> Source:
    return Source(
        key=row["key"], url=row["url"], final_url=row["final_url"] or "",
        owner=row["owner"], title=row["title"], revision=row["revision"] or "",
        license_id=row["license_id"], access_time=row["access_time"],
        sha256=row["sha256"] or "", media_type=row["media_type"] or "",
        size_bytes=row["size_bytes"] or 0,
        retrieval_method=row["retrieval_method"], status=row["status"],
        cache_path=row["cache_path"] or "", notes=row["notes"] or "",
    )


def _row_to_fact(row: sqlite3.Row) -> Fact:
    loc = json.loads(row["locator_json"] or "{}")
    unc = json.loads(row["uncertainty_json"] or "{}")
    dom = json.loads(row["domain_json"] or "{}")
    return Fact(
        key=row["key"],
        value=json.loads(row["value_json"]),
        unit=row["unit"] or "",
        value_class=row["value_class"],
        source_key=row["source_key"],
        extraction_method=row["extraction_method"],
        locator=Locator(**loc) if loc else Locator(),
        uncertainty=Uncertainty(**unc) if unc else Uncertainty.none(),
        domain={k: tuple(v) for k, v in dom.items()},
        typical=bool(row["typical"]),
        notes=row["notes"] or "",
    )
