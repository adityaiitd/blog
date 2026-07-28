"""Toolchain discovery and capability recording.

FORGE degrades rather than guesses. Each backend is probed once, its version
recorded, and its absence turned into an explicit capability downgrade that
propagates into the release gates. A missing solver never silently becomes a
closed-form approximation presented as a field result.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ToolStatus(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    DEGRADED = "degraded"     # present but not fully usable
    UNTESTED = "untested"


@dataclass
class Tool:
    name: str
    purpose: str
    status: str = ToolStatus.UNTESTED.value
    version: str = ""
    path: str = ""
    fallback: str = ""
    detail: str = ""

    @property
    def usable(self) -> bool:
        return self.status == ToolStatus.AVAILABLE.value


def _run(cmd: List[str], timeout: float = 60.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "LC_ALL": "C"},
        )
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except FileNotFoundError:
        return 127, "not found"
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except Exception as exc:  # pragma: no cover - defensive
        return 1, str(exc)


def _first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:200]
    return ""


def probe_python_stack() -> List[Tool]:
    tools: List[Tool] = []
    for module, purpose, fallback in [
        ("numpy", "array maths", "none; required"),
        ("scipy", "optimisation, interpolation, FFT", "hand-rolled solvers"),
        ("matplotlib", "report figures", "text-only report"),
        ("fitz", "PDF text and table extraction", "stdlib zlib stream recovery"),
        ("yaml", "requirement and protocol files", "json only"),
    ]:
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "")
            if not version and module == "fitz":
                version = getattr(mod, "VersionBind", "")
            tools.append(
                Tool(name=module, purpose=purpose,
                     status=ToolStatus.AVAILABLE.value, version=str(version),
                     path=getattr(mod, "__file__", "") or "")
            )
        except ImportError:
            tools.append(
                Tool(name=module, purpose=purpose,
                     status=ToolStatus.MISSING.value, fallback=fallback)
            )
    return tools


def probe_ngspice() -> Tool:
    path = shutil.which("ngspice")
    tool = Tool(
        name="ngspice",
        purpose="FHA gain sweeps, averaged ISOP studies, switched transients",
        fallback="analytic FHA only; no switched ZVS prediction",
    )
    if not path:
        tool.status = ToolStatus.MISSING.value
        return tool
    tool.path = path
    code, out = _run(["ngspice", "-v"])
    # The banner leads with a row of asterisks; the version is on a later line.
    for line in out.splitlines():
        if "ngspice-" in line:
            tool.version = line.strip().lstrip("* ").split(":")[0].strip()
            break
    else:
        tool.version = _first_line(out)
    tool.status = (
        ToolStatus.AVAILABLE.value if code == 0 else ToolStatus.DEGRADED.value
    )
    if code != 0:
        tool.detail = out[:200]
    return tool


def probe_kicad() -> Tool:
    path = shutil.which("kicad-cli")
    tool = Tool(
        name="kicad-cli",
        purpose="DRC, Gerber/drill export and board reopen checks",
        fallback="geometry emitted but unverified; no manufacturing release",
    )
    if not path:
        tool.status = ToolStatus.MISSING.value
        return tool
    tool.path = path
    code, out = _run(["kicad-cli", "version"])
    tool.version = _first_line(out)
    tool.status = (
        ToolStatus.AVAILABLE.value if code == 0 else ToolStatus.DEGRADED.value
    )
    return tool


def probe_wine() -> Tool:
    path = shutil.which("wine64") or shutil.which("wine")
    tool = Tool(
        name="wine",
        purpose="host FEMM 4.2 (a Windows binary) for 2D field studies",
        fallback="no 2D FEA; analytic screening only, field results UNVERIFIED",
    )
    if not path:
        tool.status = ToolStatus.MISSING.value
        return tool
    tool.path = path
    code, out = _run([path, "--version"], timeout=120)
    tool.version = _first_line(out)
    tool.status = (
        ToolStatus.AVAILABLE.value if code == 0 else ToolStatus.DEGRADED.value
    )
    if code != 0:
        tool.detail = out[:200]
    return tool


def probe_femm(femm_root: Optional[Path] = None) -> Tool:
    """FEMM is present only if its solver executables are on disk."""
    tool = Tool(
        name="femm",
        purpose="2D magnetostatic and harmonic field solutions",
        fallback=(
            "Dowell/Ferreira analytics for screening; every field quantity "
            "marked UNVERIFIED and 3D omissions unbounded"
        ),
    )
    roots: List[Path] = []
    if femm_root:
        roots.append(Path(femm_root))
    home = Path.home()
    roots += [
        home / ".wine/drive_c/femm42",
        home / ".wine/drive_c/Program Files/femm42",
        home / ".wine/drive_c/Program Files (x86)/femm42",
    ]
    for root in roots:
        exe = root / "bin" / "femm.exe"
        if exe.exists():
            tool.path = str(exe)
            tool.status = ToolStatus.AVAILABLE.value
            tool.version = "4.2"
            return tool
    tool.status = ToolStatus.MISSING.value
    return tool


def probe_femm_functional(femm_tool: Tool, wine_tool: Tool) -> Tool:
    """Actually solve a problem with a known answer.

    Presence of ``femm.exe`` proves nothing under Wine: the GUI needs the
    MFC 9 runtime, and a missing dependency shows up only at load time. This
    runs a magnetostatic solve of a round copper conductor and checks the
    resistance FEMM reports against the analytic value.
    """
    tool = Tool(
        name="femm-functional",
        purpose="verified end-to-end field solve under Wine",
        fallback="analytic screening only; field quantities marked UNVERIFIED",
    )
    if not (femm_tool.usable and wine_tool.usable):
        tool.status = ToolStatus.MISSING.value
        tool.detail = "femm or wine unavailable"
        return tool

    import tempfile

    workdir = Path(tempfile.mkdtemp(prefix="forge-femm-probe-"))
    lua = workdir / "probe.lua"
    result = workdir / "probe_result.txt"
    radius_mm, depth_mm, current = 2.0, 100.0, 1.0
    lua.write_text(_FEMM_PROBE_LUA.format(
        radius=radius_mm, depth=depth_mm,
        fem=f"Z:{workdir.as_posix()}/probe.fem",
        out=f"Z:{result.as_posix()}",
    ))
    code, out = _run(
        [wine_tool.path, femm_tool.path,
         f"-lua-script=Z:{lua.as_posix()}", "-windowhide"],
        timeout=300,
    )
    if not result.exists():
        tool.status = ToolStatus.MISSING.value
        tool.detail = f"solver produced no output (rc={code}): {out[-160:]}"
        return tool

    values: Dict[str, float] = {}
    for line in result.read_text().splitlines():
        if "=" in line:
            key, _, val = line.partition("=")
            try:
                values[key.strip()] = float(val)
            except ValueError:
                pass
    volts = values.get("volts_re", 0.0)
    if volts <= 0:
        tool.status = ToolStatus.DEGRADED.value
        tool.detail = f"implausible solver output: {values}"
        return tool

    # Analytic DC resistance of the same conductor.
    rho_cu = 1.724e-8
    area = 3.141592653589793 * (radius_mm * 1e-3) ** 2
    r_expected = rho_cu * (depth_mm * 1e-3) / area
    r_femm = volts / current
    error = abs(r_femm - r_expected) / r_expected
    tool.version = f"R_femm={r_femm*1e6:.1f}uohm vs analytic {r_expected*1e6:.1f}uohm"
    if error < 0.02:
        tool.status = ToolStatus.AVAILABLE.value
        tool.detail = f"agrees within {error*100:.2f}%"
    else:
        tool.status = ToolStatus.DEGRADED.value
        tool.detail = f"disagrees by {error*100:.1f}% with the analytic value"
    return tool


_FEMM_PROBE_LUA = """-- FORGE toolchain probe: conductor with a known DC resistance.
newdocument(0)
mi_probdef(0, "millimeters", "planar", 1e-8, {depth}, 30, 0)
mi_addnode(-40,-40) mi_addnode(40,-40) mi_addnode(40,40) mi_addnode(-40,40)
mi_addsegment(-40,-40, 40,-40)
mi_addsegment(40,-40, 40,40)
mi_addsegment(40,40, -40,40)
mi_addsegment(-40,40, -40,-40)
mi_addnode(-{radius},0) mi_addnode({radius},0)
mi_addarc(-{radius},0, {radius},0, 180, 1)
mi_addarc({radius},0, -{radius},0, 180, 1)
mi_getmaterial("Air")
mi_getmaterial("Copper")
mi_addcircprop("coil", 1, 1)
mi_addblocklabel(0,0)
mi_selectlabel(0,0)
mi_setblockprop("Copper", 0, 0.25, "coil", 0, 0, 1)
mi_clearselected()
mi_addblocklabel(20,20)
mi_selectlabel(20,20)
mi_setblockprop("Air", 0, 1.0, "", 0, 0, 0)
mi_clearselected()
mi_addboundprop("azero", 0, 0, 0, 0, 0, 0, 0, 0, 0)
mi_selectsegment(0,-40) mi_selectsegment(40,0)
mi_selectsegment(0,40) mi_selectsegment(-40,0)
mi_setsegmentprop("azero", 0, 1, 0, 0)
mi_clearselected()
mi_saveas("{fem}")
mi_analyze(1)
mi_loadsolution()
local i, v, f = mo_getcircuitproperties("coil")
local h = openfile("{out}", "w")
write(h, "current_re=", i, "\\n")
write(h, "volts_re=", v, "\\n")
write(h, "flux_re=", f, "\\n")
closefile(h)
quit()
"""


def probe_chrome() -> Tool:
    path = shutil.which("google-chrome") or shutil.which("google-chrome-stable")
    tool = Tool(
        name="google-chrome",
        purpose="retrieve sources that reject plain HTTP clients",
        fallback="direct HTTP only; blocked sources recorded as manual gates",
    )
    if not path:
        tool.status = ToolStatus.MISSING.value
        return tool
    tool.path = path
    code, out = _run([path, "--version"], timeout=60)
    tool.version = _first_line(out)
    tool.status = (
        ToolStatus.AVAILABLE.value if code == 0 else ToolStatus.DEGRADED.value
    )
    return tool


def probe_display() -> Tool:
    display = os.environ.get("DISPLAY", "")
    tool = Tool(
        name="x-display",
        purpose="headful Chrome and any GUI tool",
        fallback="headless Chrome; GUI tools unavailable",
    )
    if not display:
        tool.status = ToolStatus.MISSING.value
        return tool
    tool.detail = f"DISPLAY={display}"
    code, out = _run(["xdpyinfo", "-display", display], timeout=30)
    if code == 0:
        tool.status = ToolStatus.AVAILABLE.value
        for line in out.splitlines():
            if "dimensions:" in line:
                tool.version = line.strip()
                break
    else:
        tool.status = ToolStatus.DEGRADED.value
        tool.detail += f" (xdpyinfo failed: {out[:80]})"
    return tool


@dataclass
class Toolchain:
    tools: Dict[str, Tool] = field(default_factory=dict)

    def get(self, name: str) -> Tool:
        return self.tools.get(
            name, Tool(name=name, purpose="", status=ToolStatus.MISSING.value)
        )

    def usable(self, name: str) -> bool:
        return self.get(name).usable

    def capabilities(self) -> Dict[str, bool]:
        """What the pipeline may claim, given what is installed."""
        return {
            "field_2d_fea": self.usable("femm-functional"),
            "switched_circuit_sim": self.usable("ngspice"),
            "manufacturing_release": self.usable("kicad-cli"),
            "browser_retrieval": self.usable("google-chrome"),
            "pdf_table_extraction": self.usable("fitz"),
            "numeric_optimisation": self.usable("scipy"),
        }

    def downgrades(self) -> List[str]:
        notes: List[str] = []
        for tool in self.tools.values():
            if tool.status in (ToolStatus.MISSING.value, ToolStatus.DEGRADED.value):
                notes.append(
                    f"{tool.name}: {tool.status} -> {tool.fallback or 'no fallback'}"
                )
        return notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tools": {k: asdict(v) for k, v in self.tools.items()},
            "capabilities": self.capabilities(),
            "downgrades": self.downgrades(),
        }

    def save(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return path

    @staticmethod
    def load(path: Path | str) -> "Toolchain":
        data = json.loads(Path(path).read_text())
        return Toolchain(
            tools={k: Tool(**v) for k, v in data.get("tools", {}).items()}
        )


def probe_all(
    femm_root: Optional[Path] = None, functional: bool = True
) -> Toolchain:
    tools: List[Tool] = []
    tools += probe_python_stack()
    wine = probe_wine()
    femm = probe_femm(femm_root)
    tools += [
        probe_ngspice(),
        probe_kicad(),
        wine,
        femm,
        probe_chrome(),
        probe_display(),
    ]
    if functional:
        tools.append(probe_femm_functional(femm, wine))
    return Toolchain(tools={t.name: t for t in tools})


def main() -> int:
    chain = probe_all()
    out = Path(__file__).resolve().parent / "data" / "toolchain.json"
    chain.save(out)
    width = max(len(n) for n in chain.tools)
    print("FORGE toolchain probe")
    print("-" * (width + 46))
    for name, tool in sorted(chain.tools.items()):
        print(f"{name:<{width}}  {tool.status:<10}  {tool.version[:40]}")
    print("-" * (width + 46))
    print("capabilities:")
    for cap, ok in chain.capabilities().items():
        print(f"  {'yes' if ok else 'NO ':<4} {cap}")
    if chain.downgrades():
        print("downgrades:")
        for note in chain.downgrades():
            print(f"  - {note}")
    print(f"\nwritten to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
