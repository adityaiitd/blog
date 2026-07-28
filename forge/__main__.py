"""FORGE command line: one entry point for the whole pipeline.

    python -m forge doctor      check the toolchain
    python -m forge evidence    register sources, open manual gates
    python -m forge catalog     build the material and component catalog
    python -m forge requirements  validate and freeze the requirement lock
    python -m forge screen      enumerate and filter the design space
    python -m forge geometry    emit a KiCad board and verify it with KiCad
    python -m forge field       run the 2D field study (slow)
    python -m forge sourcing    harvest live prices and build the cost model
    python -m forge ui          serve the interactive explorer
    python -m forge export      write a standalone HTML that needs no server
    python -m forge all         everything except field and ui
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

#: Import name -> what to install, for a readable failure instead of a
#: bare ModuleNotFoundError three frames deep.
REQUIRED = {
    "numpy": "numpy",
    "scipy": "scipy",
    "yaml": "pyyaml",
}
OPTIONAL = {
    "fitz": ("pymupdf", "parsing datasheet PDFs"),
    "matplotlib": ("matplotlib", "report figures"),
    "websocket": ("websocket-client", "browser-driven price harvesting"),
}


def check_dependencies() -> int:
    missing = [pkg for mod, pkg in REQUIRED.items() if not _importable(mod)]
    if missing:
        print("FORGE cannot start: missing required packages.\n")
        print(f"    pip install {' '.join(missing)}\n")
        print("Or install the project and all its dependencies at once:\n")
        print("    pip install -e .\n")
        return 1
    absent = [
        (pkg, why) for mod, (pkg, why) in OPTIONAL.items()
        if not _importable(mod)
    ]
    for pkg, why in absent:
        print(f"note: {pkg} is not installed, so {why} is unavailable")
    return 0


def _importable(module: str) -> bool:
    import importlib.util

    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _rule(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m\n" + "-" * max(len(title), 40))


def cmd_doctor(args: argparse.Namespace) -> int:
    from .toolchain import probe_all

    _rule("toolchain")
    chain = probe_all(functional=not args.fast)
    width = max(len(n) for n in chain.tools)
    for name, tool in sorted(chain.tools.items()):
        mark = "ok " if tool.usable else "MISSING"
        print(f"  {mark:<8}{name:<{width}}  {tool.version[:46]}")
    print("\n  capabilities")
    for cap, ok in chain.capabilities().items():
        print(f"    {'yes' if ok else 'NO '}  {cap}")
    for note in chain.downgrades():
        print(f"    downgrade: {note}")
    chain.save(DATA / "toolchain.json")
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    from .browser.manual_gate import ManualGateLog
    from .evidence.bootstrap import bootstrap
    from .evidence.extract import EvidenceCache
    from .evidence.register import EvidenceRegister

    _rule("evidence register")
    register = EvidenceRegister(DATA / "evidence.sqlite")
    gates = ManualGateLog(DATA / "manual_gates.json")
    cache = EvidenceCache(DATA / "evidence_cache")
    outcomes = bootstrap(register, gates, cache, use_browser=not args.no_browser)
    for key, status in outcomes.items():
        print(f"  {status:<18}{key}")
    summary = gates.summary()
    print(f"\n  {summary['blocking']} manual gate(s) open: "
          f"{', '.join(summary['blocked_keys']) or 'none'}")
    return 0


def cmd_catalog(args: argparse.Namespace) -> int:
    from .data.build_catalog import build

    _rule("catalog")
    for key, count in build().items():
        print(f"  {key:<14}{count}")
    return 0


def cmd_requirements(args: argparse.Namespace) -> int:
    from .evidence.register import EvidenceRegister
    from .requirements import build, build_basis, summarise

    _rule("requirements")
    register = EvidenceRegister(DATA / "evidence.sqlite")
    lock = build(register=register)
    print("  " + summarise(lock).replace("\n", "\n  "))
    print(f"  errors {len(lock.report.errors)}, warnings {len(lock.report.warnings)}")
    for err in lock.report.errors:
        print(f"    ERROR {err}")
    if lock.report.ok:
        path = lock.save(HERE / "requirements" / "requirements.lock.yaml")
        print(f"  locked -> {path.name}  ({lock.content_hash[:16]})")
    basis = build_basis(lock.converter, lock.diablo)
    print("\n  insulation basis")
    print("    " + basis.summary().replace("\n", "\n    "))
    return 0 if lock.report.ok else 1


def cmd_screen(args: argparse.Namespace) -> int:
    from .data.catalog import Catalog
    from .requirements import build
    from .solve.screen import ScreenInputs, screen

    _rule("design space screening")
    report = screen(Catalog(), ScreenInputs.from_lock(build()))
    print("  " + report.summary().replace("\n", "\n  "))
    for candidate in report.best(5):
        print(f"    {candidate.total_loss_w:6.2f} W  "
              f"eta {candidate.efficiency:.4f}  {candidate.key}")
    return 0


def cmd_geometry(args: argparse.Namespace) -> int:
    from .data.catalog import Catalog
    from .geometry.kicad_writer import write_board, write_design_rules, write_project
    from .geometry.model import build_planar_transformer, core_from_catalog
    from .geometry.peec_writer import export_geometry, write_fasthenry
    from .verify.geometry import verify_board

    _rule("geometry and manufacturing output")
    out = Path(args.out)
    core = core_from_catalog(Catalog().core(args.core), args.material)
    transformer = build_planar_transformer(
        "cell", core, 4, 1, 1, 4, 104.4e-6, 0.1e-3, barrier_thickness_m=0.4e-3
    )
    problems = transformer.validate()
    print(f"  layout: {len(problems)} problem(s), "
          f"{transformer.stackup.layer_count} layers, "
          f"{transformer.stackup.total_thickness_m*1e3:.2f} mm thick")
    result = write_board(transformer, out / "cell.kicad_pcb")
    write_project(out / "cell.kicad_pro", 0.15e-3, 0.1e-3, 0.2e-3, 0.4e-3)
    write_design_rules(out / "cell.kicad_dru", 0.15e-3, 0.1e-3, 0.2e-3, 0.4e-3)
    print(f"  board: {result.segments} track segments, {result.vias} vias")
    geometry = export_geometry(transformer)
    geometry.save(out / "geometry3d.json")
    write_fasthenry(geometry, out / "cell.inp", 2e6)
    verification = verify_board(out / "cell.kicad_pcb")
    print("  " + verification.summary().replace("\n", "\n  "))
    print(f"\n  artifacts in {out}")
    return 0 if verification.passed else 1


def cmd_field(args: argparse.Namespace) -> int:
    from .data.catalog import Catalog
    from .geometry.model import build_planar_transformer, core_from_catalog
    from .verify.femm import characterise, femm_available

    _rule("2D field study")
    if not femm_available():
        print("  FEMM unavailable; field quantities stay UNVERIFIED")
        return 1
    core = core_from_catalog(Catalog().core(args.core), args.material)
    transformer = build_planar_transformer(
        "cell", core, 4, 1, 1, 4, 104.4e-6, 0.1e-3, barrier_thickness_m=0.4e-3
    )
    result = characterise(transformer, args.frequency, Path(args.out))
    print("  " + result.describe())
    print(f"  mesh converged: {result.mesh_converged} ({result.mesh_detail})")
    for order, resistance in result.r_ac_ohm.items():
        print(f"    harmonic {order}: R_ac {resistance*1e3:.3f} mohm")
    print("\n  not represented by this 2D section:")
    for item in result.unsupported:
        print(f"    - {item}")
    return 0


def cmd_sourcing(args: argparse.Namespace) -> int:
    from .sourcing.cost import PcbEstimate, build_cost_model, supply_risks
    from .sourcing.harvest import harvest, load, save

    _rule("sourcing")
    path = DATA / "quotes.json"
    if args.refresh or not path.exists():
        print("  harvesting live prices through a real browser...")
        quotes = harvest()
        save(quotes, path)
    else:
        quotes = load(path)
        print(f"  using cached quotes from {path.name} (--refresh to re-harvest)")

    pcb = PcbEstimate(layers=12, copper_oz=2.0, area_mm2=22.0 * 24.1)
    model = build_cost_model(quotes, volume=args.volume, pcb=pcb)
    print(f"\n  {'part':<20}{'qty':>4}{'unit':>9}{'ext':>9}  basis")
    for line in sorted(model.lines, key=lambda l: -(l.extended_usd or 0)):
        unit = f"${line.unit_usd:.3f}" if line.unit_usd else "-"
        ext = f"${line.extended_usd:.2f}" if line.extended_usd else "-"
        print(f"  {line.mpn:<20}{line.qty_per_converter:>4}{unit:>9}{ext:>9}  "
              f"{line.basis}")
    summary = model.summary()
    print(f"\n  components ${summary['component_cost_usd']:.2f} "
          f"(quoted ${summary['quoted_cost_usd']:.2f}, "
          f"estimated ${summary['estimated_cost_usd']:.2f})")
    print(f"  boards ${summary['pcb_cost_usd']:.2f}   "
          f"assembly ${summary['adder_cost_usd']:.2f}")
    print(f"  TOTAL ${summary['total_usd']:.2f} = "
          f"${summary['usd_per_kw']:.2f}/kW at {args.volume} units")
    print(f"  {summary['caveat']}")
    high = [r for r in supply_risks(quotes) if r.severity == "high"]
    for risk in high:
        print(f"  HIGH RISK {risk.part}: {risk.concern[:90]}")
    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    from .ui.server import serve

    serve(args.port, args.open)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    from .ui.export import export_static

    _rule("standalone export")
    path = export_static(Path(args.out))
    size = path.stat().st_size / 1e6
    print(f"  wrote {path}  ({size:.1f} MB)")
    print("  open it in any browser; no Python needed")
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    steps = [
        ("doctor", cmd_doctor, argparse.Namespace(fast=True)),
        ("evidence", cmd_evidence, argparse.Namespace(no_browser=args.no_browser)),
        ("catalog", cmd_catalog, argparse.Namespace()),
        ("requirements", cmd_requirements, argparse.Namespace()),
        ("screen", cmd_screen, argparse.Namespace()),
        ("geometry", cmd_geometry, argparse.Namespace(
            out="build", core="ELP18/4/10withI18/2/10", material="3F46")),
        ("sourcing", cmd_sourcing, argparse.Namespace(
            volume=1000, refresh=args.refresh)),
    ]
    failures = []
    for name, fn, ns in steps:
        try:
            if fn(ns) != 0:
                failures.append(name)
        except Exception as exc:
            print(f"  {name} FAILED: {type(exc).__name__}: {exc}")
            failures.append(name)
    _rule("summary")
    print(f"  {len(steps) - len(failures)}/{len(steps)} stages clean")
    if failures:
        print(f"  problems in: {', '.join(failures)}")
    print("\n  next: python -m forge ui        (interactive explorer)")
    print("        python -m forge export    (standalone HTML)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="forge", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="check the toolchain")
    p.add_argument("--fast", action="store_true",
                   help="skip the functional FEMM solve")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("evidence", help="register sources")
    p.add_argument("--no-browser", action="store_true")
    p.set_defaults(func=cmd_evidence)

    sub.add_parser("catalog", help="build the catalog").set_defaults(func=cmd_catalog)
    sub.add_parser("requirements", help="freeze the requirement lock").set_defaults(
        func=cmd_requirements)
    sub.add_parser("screen", help="screen the design space").set_defaults(
        func=cmd_screen)

    p = sub.add_parser("geometry", help="emit and verify a board")
    p.add_argument("--out", default="build")
    p.add_argument("--core", default="ELP18/4/10withI18/2/10")
    p.add_argument("--material", default="3F46")
    p.set_defaults(func=cmd_geometry)

    p = sub.add_parser("field", help="run the 2D field study")
    p.add_argument("--out", default="build/femm")
    p.add_argument("--core", default="ELP18/4/10withI18/2/10")
    p.add_argument("--material", default="3F46")
    p.add_argument("--frequency", type=float, default=2e6)
    p.set_defaults(func=cmd_field)

    p = sub.add_parser("sourcing", help="prices and cost model")
    p.add_argument("--volume", type=int, default=1000)
    p.add_argument("--refresh", action="store_true", help="re-harvest live prices")
    p.set_defaults(func=cmd_sourcing)

    p = sub.add_parser("ui", help="serve the interactive explorer")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--open", action="store_true")
    p.set_defaults(func=cmd_ui)

    p = sub.add_parser("export", help="standalone HTML")
    p.add_argument("--out", default="build/forge-explorer.html")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("all", help="run the whole pipeline")
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--refresh", action="store_true")
    p.set_defaults(func=cmd_all)

    args = parser.parse_args(argv)
    if check_dependencies() != 0:
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
