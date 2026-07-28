"""Read access to the component and material catalog."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ..physics.coreloss import MaterialLossModel, SteinmetzFit

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DB = Path(__file__).resolve().parent / "catalog.sqlite"


@dataclass(frozen=True)
class Core:
    part: str
    family: str
    manufacturer: str
    combination: str
    ae_mm2: float
    amin_mm2: Optional[float]
    le_mm: float
    ve_mm3: float
    height_mm: float
    length_mm: Optional[float]
    width_mm: Optional[float]
    window_h_mm: Optional[float]
    window_w_mm: Optional[float]
    mass_g: Optional[float]
    source_key: str
    provenance: str

    @property
    def ae_m2(self) -> float:
        return self.ae_mm2 * 1e-6

    @property
    def ve_m3(self) -> float:
        return self.ve_mm3 * 1e-9

    @property
    def le_m(self) -> float:
        return self.le_mm * 1e-3

    def fits_height(self, max_height_mm: float) -> bool:
        return self.height_mm <= max_height_mm


@dataclass(frozen=True)
class Device:
    part: str
    manufacturer: str
    role: str
    v_ds_max_v: float
    r_ds_on_mohm: float
    q_g_nc: Optional[float]
    q_oss_nc: Optional[float]
    q_oss_at_v: Optional[float]
    package: str
    source_key: str

    def q_oss_scaled(self, v: float) -> float:
        """Output charge at another voltage.

        GaN output capacitance is strongly non-linear, and Qoss grows
        sub-linearly with voltage. Scaling the datasheet point as sqrt(V) is a
        common approximation for a graded junction; it is an approximation, and
        the ZVS margin carries uncertainty because of it.
        """
        if self.q_oss_nc is None or not self.q_oss_at_v:
            raise ValueError(f"{self.part} has no Qoss reference point")
        return float(self.q_oss_nc) * (v / float(self.q_oss_at_v)) ** 0.5


class Catalog:
    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA_PATH.read_text())
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Catalog":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    # ------------------------------------------------------------------ read

    def cores(self, max_height_mm: Optional[float] = None) -> List[Core]:
        rows = self._conn.execute("SELECT * FROM cores ORDER BY ae_mm2").fetchall()
        cores = [
            Core(
                part=r["part"], family=r["family"], manufacturer=r["manufacturer"],
                combination=r["combination"], ae_mm2=r["ae_mm2"],
                amin_mm2=r["amin_mm2"], le_mm=r["le_mm"], ve_mm3=r["ve_mm3"],
                height_mm=r["height_mm"], length_mm=r["length_mm"],
                width_mm=r["width_mm"], window_h_mm=r["window_h_mm"],
                window_w_mm=r["window_w_mm"], mass_g=r["mass_g"],
                source_key=r["source_key"], provenance=r["provenance"],
            )
            for r in rows
        ]
        if max_height_mm is not None:
            cores = [c for c in cores if c.fits_height(max_height_mm)]
        return cores

    def core(self, part: str) -> Core:
        found = [c for c in self.cores() if c.part == part]
        if not found:
            raise KeyError(f"core '{part}' is not in the catalog")
        return found[0]

    def devices(self, role: Optional[str] = None) -> List[Device]:
        sql = "SELECT * FROM devices"
        args: tuple = ()
        if role:
            sql += " WHERE role = ?"
            args = (role,)
        return [
            Device(
                part=r["part"], manufacturer=r["manufacturer"], role=r["role"],
                v_ds_max_v=r["v_ds_max_v"], r_ds_on_mohm=r["r_ds_on_mohm"],
                q_g_nc=r["q_g_nc"], q_oss_nc=r["q_oss_nc"],
                q_oss_at_v=r["q_oss_at_v"], package=r["package"] or "",
                source_key=r["source_key"],
            )
            for r in self._conn.execute(sql, args).fetchall()
        ]

    def device(self, part: str) -> Device:
        found = [d for d in self.devices() if d.part == part]
        if not found:
            raise KeyError(f"device '{part}' is not in the catalog")
        return found[0]

    def material(self, name: str) -> MaterialLossModel:
        row = self._conn.execute(
            "SELECT * FROM materials WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            raise KeyError(f"material '{name}' is not in the catalog")
        if row["status"] != "characterised":
            raise KeyError(
                f"material '{name}' is registered but has no usable loss data "
                f"({row['notes'] or 'source unavailable'})"
            )
        fits: Dict[float, SteinmetzFit] = {}
        for f in self._conn.execute(
            "SELECT * FROM loss_fits WHERE material = ?", (name,)
        ):
            fits[f["temperature_c"]] = SteinmetzFit(
                k=f["k"], alpha=f["alpha"], beta=f["beta"],
                f_domain=(f["f_lo_hz"], f["f_hi_hz"]),
                b_domain=(f["b_lo_t"], f["b_hi_t"]),
                temperature_c=f["temperature_c"], n_points=f["n_points"],
                max_residual=f["max_residual"],
                alpha_assumed=bool(f["alpha_assumed"]),
                notes=f["notes"] or "",
            )
        rel = self._conn.execute(
            "SELECT MAX(rel_uncertainty) AS u FROM loss_fits WHERE material = ?",
            (name,),
        ).fetchone()["u"]
        return MaterialLossModel(
            material=row["name"], manufacturer=row["manufacturer"],
            density_kg_m3=row["density_kg_m3"],
            b_sat_25c_t=(row["b_sat_25c_mt"] or 0.0) * 1e-3,
            b_sat_100c_t=(row["b_sat_100c_mt"] or 0.0) * 1e-3,
            curie_c=row["curie_c"] or 0.0,
            resistivity_ohm_m=row["resistivity_ohm_m"] or 0.0,
            mu_i=row["mu_i"] or 0.0,
            fits=fits, relative_uncertainty=rel or 0.25,
            intended_band_hz=(row["band_lo_hz"] or 0.0,
                              row["band_hi_hz"] or float("inf")),
            source_key=row["source_key"], notes=row["notes"] or "",
        )

    def materials(self, characterised_only: bool = True) -> List[str]:
        sql = "SELECT name FROM materials"
        if characterised_only:
            sql += " WHERE status = 'characterised'"
        return [r["name"] for r in self._conn.execute(sql + " ORDER BY name")]

    def laminate(self, name: str) -> sqlite3.Row:
        row = self._conn.execute(
            "SELECT * FROM laminates WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            raise KeyError(f"laminate '{name}' is not in the catalog")
        return row

    def copper_thickness_um(self, ounces: float) -> float:
        row = self._conn.execute(
            "SELECT thickness_um FROM copper_weights WHERE ounces = ?",
            (ounces,),
        ).fetchone()
        if row is None:
            raise KeyError(f"copper weight {ounces} oz is not in the catalog")
        return float(row["thickness_um"])

    def summary(self) -> Dict[str, int]:
        def count(table: str) -> int:
            return int(
                self._conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
            )

        return {
            "cores": count("cores"),
            "materials": count("materials"),
            "loss_points": count("loss_points"),
            "loss_fits": count("loss_fits"),
            "devices": count("devices"),
            "laminates": count("laminates"),
        }
