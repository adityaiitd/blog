"""A local web server exposing the real physics to the browser.

The browser does not reimplement any modelling. Every number on screen comes
from a call into ``forge.solve.design_point``, which is the same code the
report generator uses. Moving a slider re-runs the actual models.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from ..data.catalog import Catalog
from ..solve.design_point import DesignInputs, evaluate

STATIC = Path(__file__).resolve().parent / "static"

#: One catalog per thread.
#:
#: SQLite connections are bound to the thread that created them, and this is a
#: threading server, so a single shared instance fails on every request handled
#: by a different worker. That failure is invisible locally when requests
#: happen to land on one thread, and shows up as an intermittent 500 under any
#: real concurrency.
_LOCAL = threading.local()


def catalog() -> Catalog:
    existing = getattr(_LOCAL, "catalog", None)
    if existing is None:
        existing = Catalog()
        _LOCAL.catalog = existing
    return existing


def options_payload() -> Dict[str, Any]:
    cat = catalog()
    cores = []
    for core in cat.cores():
        cores.append({
            "part": core.part,
            "label": f"{core.part}  (Ae {core.ae_mm2:.0f} mm2, {core.height_mm:.1f} mm tall)",
            "ae_mm2": core.ae_mm2,
            "height_mm": core.height_mm,
            "fits_height": core.height_mm <= 8.0,
        })
    materials = []
    for name in cat.materials():
        model = cat.material(name)
        fit = model.fit_at(100.0)
        materials.append({
            "name": name,
            "manufacturer": model.manufacturer,
            "band_lo_MHz": model.intended_band_hz[0] / 1e6,
            "band_hi_MHz": model.intended_band_hz[1] / 1e6,
            "alpha": fit.alpha,
            "beta": fit.beta,
            "alpha_assumed": fit.alpha_assumed,
            "f_lo_MHz": fit.f_domain[0] / 1e6,
            "f_hi_MHz": fit.f_domain[1] / 1e6,
            "b_lo_mT": fit.b_domain[0] * 1e3,
            "b_hi_mT": fit.b_domain[1] * 1e3,
        })
    unavailable = [
        n for n in cat.materials(characterised_only=False)
        if n not in cat.materials()
    ]
    return {
        "cores": cores,
        "materials": materials,
        "unavailable_materials": unavailable,
        "copper_weights": [1.0, 2.0, 3.0, 4.0],
        "defaults": DesignInputs().__dict__,
        "fixed": {
            "v_cell_V": 100.0, "v_out_V": 12.5, "i_out_A": 60.0,
            "p_out_W": 750.0, "turns_ratio": 4.0, "cells": 8,
            "max_layers": 14, "max_height_mm": 8.0,
        },
    }


def sourcing_payload(volume: int = 1000) -> Dict[str, Any]:
    """Cost model, quotes and risks, with quoted and estimated kept apart."""
    from ..sourcing.cost import (
        STRUCTURAL_RISKS, PcbEstimate, build_cost_model, supply_risks,
    )
    from ..sourcing.harvest import CELL_BOM, load

    quotes_path = Path(__file__).resolve().parents[1] / "data" / "quotes.json"
    if not quotes_path.exists():
        return {"error": "no quotes harvested yet; run forge.sourcing.harvest"}

    quotes = load(quotes_path)
    pcb = PcbEstimate(layers=12, copper_oz=2.0, area_mm2=22.0 * 24.1)
    model = build_cost_model(quotes, volume=volume, pcb=pcb)
    by_mpn = {q.mpn: q for q in quotes}

    lines = []
    for line in sorted(model.lines, key=lambda l: -(l.extended_usd or 0.0)):
        quote = by_mpn.get(line.mpn)
        lines.append({
            "mpn": line.mpn,
            "role": line.role,
            "qty": line.qty_per_converter,
            "unit_usd": line.unit_usd,
            "extended_usd": line.extended_usd,
            "basis": line.basis,
            "confidence": line.confidence,
            "note": line.note,
            "stock": quote.stock if quote else None,
            "url": quote.url if quote else "",
            "manufacturer": quote.manufacturer if quote else "",
            "retrieved_at": quote.retrieved_at if quote else "",
        })

    risks = [
        {"part": r.part, "concern": r.concern, "severity": r.severity,
         "mitigation": r.mitigation}
        for r in supply_risks(quotes) + STRUCTURAL_RISKS
    ]
    volumes = {}
    for v in (10, 100, 1000, 10000):
        m = build_cost_model(quotes, volume=v, pcb=pcb)
        volumes[v] = {
            "total_usd": m.total_usd, "usd_per_kw": m.usd_per_kw,
            "components_usd": m.component_cost_usd,
        }
    return {
        "summary": model.summary(),
        "lines": lines,
        "risks": risks,
        "pcb": {"description": pcb.describe(),
                "unit_usd": pcb.unit_cost_usd(volume), "boards": 8},
        "adders": model.adders,
        "volume_curve": volumes,
        "bom_size": len(CELL_BOM),
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter console
        pass

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: Dict[str, Any], status: int = 200) -> None:
        self._send(status, json.dumps(payload).encode(), "application/json")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/options":
            self._json(options_payload())
            return
        if path.startswith("/api/sourcing"):
            from urllib.parse import parse_qs
            query = parse_qs(urlparse(self.path).query)
            volume = int(query.get("volume", ["1000"])[0])
            self._json(sourcing_payload(volume))
            return
        if path in ("/", "/index.html"):
            self._serve_static("index.html", "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            name = path[len("/static/"):]
            kind = (
                "text/css" if name.endswith(".css")
                else "application/javascript" if name.endswith(".js")
                else "text/plain"
            )
            self._serve_static(name, kind)
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json({"error": "invalid JSON"}, 400)
            return

        if path == "/api/evaluate":
            try:
                inputs = DesignInputs.from_dict(payload)
                result = evaluate(inputs, catalog())
                self._json(result.to_dict())
            except Exception as exc:  # surfaced in the UI, not swallowed
                self._json({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
            return
        self._send(404, b"not found", "text/plain")

    def _serve_static(self, name: str, content_type: str) -> None:
        target = (STATIC / name).resolve()
        if not str(target).startswith(str(STATIC.resolve())) or not target.exists():
            self._send(404, b"not found", "text/plain")
            return
        self._send(200, target.read_bytes(), content_type)


def serve(port: int = 8765, open_browser: bool = False) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"FORGE design explorer on {url}")
    print("Every value shown is computed by the Python models, not the browser.")
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="FORGE interactive explorer")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    serve(args.port, args.open)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
