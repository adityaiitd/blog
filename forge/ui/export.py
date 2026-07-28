"""Write the explorer as one self-contained HTML file.

The served app calls into Python on every slider move. A file you can email
cannot do that, so this precomputes a grid of design points and embeds them.
Sliders then snap to the nearest computed point rather than moving
continuously.

That difference is stated in the exported page itself. A tool that silently
interpolated between precomputed points would be inventing physics, which is
the one thing this project is built not to do.
"""

from __future__ import annotations

import json
import itertools
from pathlib import Path
from typing import Any, Dict, List, Sequence

from ..data.catalog import Catalog
from ..solve.design_point import DesignInputs, evaluate
from .server import options_payload, sourcing_payload

STATIC = Path(__file__).resolve().parent / "static"

#: Axes varied in the export. Chosen because they are the ones that change the
#: answer most, and because their product stays small enough to embed.
GRID: Dict[str, Sequence[Any]] = {
    "frequency_hz": (700e3, 1.0e6, 1.5e6, 2.0e6, 2.5e6, 3.0e6),
    "copper_oz": (1.0, 2.0, 3.0),
    "interleave": (True, False),
    "secondary_parallel": (2, 3, 4),
    "heatsink_k_w": (1.0, 2.0, 3.0, 5.0),
}


def grid_key(values: Dict[str, Any]) -> str:
    """Key a grid point by axis *indices*, never by formatted values.

    Formatting a float on one side and parsing it on the other is a reliable
    way to miss: Python writes 700000.0 and JSON hands JavaScript 700000, and
    the lookup silently returns nothing. Indices have no such ambiguity.
    """
    parts = []
    for name in sorted(GRID):
        options = list(GRID[name])
        parts.append(str(options.index(values[name])))
    return "-".join(parts)


def build_grid(catalog: Catalog) -> Dict[str, Any]:
    """Evaluate every combination on the grid."""
    names = list(GRID)
    out: Dict[str, Any] = {}
    for combo in itertools.product(*(GRID[n] for n in names)):
        values = dict(zip(names, combo))
        inputs = DesignInputs.from_dict(values)
        result = evaluate(inputs, catalog)
        payload = result.to_dict()
        # Trim the heaviest arrays; the drawings need geometry, the charts can
        # live with fewer samples.
        wave = payload.get("waveforms", {})
        for key, series in list(wave.items()):
            if isinstance(series, list) and len(series) > 90:
                step = max(1, len(series) // 90)
                wave[key] = [round(v, 4) for v in series[::step]]
        curves = payload.get("curves", {})
        for key in ("gain_fn", "gain_full_load", "gain_light_load"):
            if key in curves:
                curves[key] = [round(v, 4) for v in curves[key][::2]]
        out[grid_key(values)] = payload
    return out


EXPORT_NOTICE = """
<div class="banner" style="background:#12243b;border-color:#274a72">
  <strong>Standalone export.</strong>
  This file has no Python behind it, so the controls snap to precomputed design
  points instead of moving continuously. Axes not on the grid are fixed at their
  baseline. For continuous evaluation run <code>python -m forge ui</code>.
</div>
"""


def export_static(out_path: Path) -> Path:
    """Bundle HTML, CSS, JS and a precomputed grid into one file."""
    catalog = Catalog()
    html = (STATIC / "index.html").read_text()
    css = (STATIC / "style.css").read_text()
    app = (STATIC / "app.js").read_text()
    learn = (STATIC / "learn.js").read_text()
    modes = (STATIC / "modes.js").read_text()

    grid = build_grid(catalog)
    options = options_payload()
    sourcing = sourcing_payload(1000)

    bundle = {
        "options": options,
        "sourcing": sourcing,
        "grid": grid,
        "grid_axes": {
            k: [int(v) if isinstance(v, bool) else v for v in vals]
            for k, vals in GRID.items()
        },
    }

    # A tiny shim replacing the two fetch calls the served app makes.
    shim = """
<script>
const FORGE_BUNDLE = __BUNDLE__;
function _gridKey(state) {
  // Snap each axis to its nearest grid index. Index-based keys avoid any
  // float formatting disagreement between the generator and this shim.
  const axes = FORGE_BUNDLE.grid_axes;
  const parts = [];
  for (const name of Object.keys(axes).sort()) {
    const options = axes[name];
    let value = state[name];
    if (typeof value === "boolean") value = value ? 1 : 0;
    let bestIndex = 0, bestD = Infinity;
    options.forEach((o, i) => {
      const d = Math.abs(Number(o) - Number(value));
      if (d < bestD) { bestD = d; bestIndex = i; }
    });
    parts.push(bestIndex);
  }
  return parts.join("-");
}
window.fetch = async (url, opts) => {
  const u = String(url);
  if (u.includes("/api/options")) {
    return { json: async () => FORGE_BUNDLE.options };
  }
  if (u.includes("/api/sourcing")) {
    return { json: async () => FORGE_BUNDLE.sourcing };
  }
  if (u.includes("/api/evaluate")) {
    const state = JSON.parse(opts.body);
    const hit = FORGE_BUNDLE.grid[_gridKey(state)];
    return { json: async () => hit ||
      { ok: false, error: "no precomputed point for this combination" } };
  }
  throw new Error("unexpected fetch in the standalone export: " + u);
};
</script>
"""
    shim = shim.replace("__BUNDLE__", json.dumps(bundle, separators=(",", ":")))

    html = html.replace(
        '<link rel="stylesheet" href="/static/style.css">',
        f"<style>\n{css}\n</style>",
    )
    html = html.replace('<script src="/static/learn.js"></script>', "")
    html = html.replace('<script src="/static/modes.js"></script>', "")
    html = html.replace(
        '<script src="/static/app.js"></script>',
        shim + f"<script>\n{learn}\n</script>\n"
        f"<script>\n{modes}\n</script>\n<script>\n{app}\n</script>",
    )
    html = html.replace('<main class="layout"', EXPORT_NOTICE + '<main class="layout"')

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    catalog.close()
    return out_path
