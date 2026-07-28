/* FORGE design explorer.
 *
 * This file draws things and sends the slider values to the server. It does no
 * physics: every number rendered here came back from the Python models.
 */

const SVG = "http://www.w3.org/2000/svg";
const $ = (id) => document.getElementById(id);

let OPTIONS = null;
let STATE = null;
let PENDING = null;

/* ------------------------------------------------------------- controls */

const CONTROLS = [
  {
    key: "core_part", type: "select", label: "Ferrite core",
    why: "The core is the magnetic path. A bigger cross-section carries flux " +
         "more easily, so you need fewer turns, but it has to fit inside the " +
         "8 mm the converter is allowed.",
    lever: "Bigger core lowers flux and core loss but costs height and space."
  },
  {
    key: "material", type: "select", label: "Core material",
    why: "Ferrite formulations are tuned for different frequency bands. Run one " +
         "outside its band and its losses climb steeply.",
    lever: "Match the material's band to your switching frequency."
  },
  {
    key: "frequency_hz", type: "range", label: "Switching frequency",
    min: 5e5, max: 3e6, step: 1e5, unit: "MHz", scale: 1e-6, digits: 2,
    why: "How fast the transistors switch. Higher frequency means less flux per " +
         "cycle, so the magnetics shrink. But copper loss rises, because at high " +
         "frequency current crowds into the surface of the conductor.",
    lever: "Raising it shrinks the core and cuts flux; it worsens copper loss."
  },
  {
    key: "primary_turns", type: "range", label: "Primary turns",
    min: 4, max: 16, step: 4, unit: "turns", scale: 1, digits: 0,
    why: "Turns on the high-voltage side. The ratio to the secondary is fixed at " +
         "4:1 by the voltage conversion, so this moves in steps of four.",
    lever: "More turns cuts flux density, but adds resistance and eats layers."
  },
  {
    key: "turns_per_primary_layer", type: "range", label: "Turns per primary layer",
    min: 1, max: 4, step: 1, unit: "", scale: 1, digits: 0,
    why: "How many turns are squeezed onto each copper layer. Packing more per " +
         "layer saves layers but makes each turn narrower and more resistive.",
    lever: "Increase it to free up layers for the secondary."
  },
  {
    key: "secondary_parallel", type: "range", label: "Parallel secondary layers",
    min: 1, max: 6, step: 1, unit: "layers", scale: 1, digits: 0,
    why: "The secondary carries 60 A. No single PCB layer can do that without " +
         "cooking, so the same turn is duplicated across several layers wired " +
         "in parallel, each carrying a share.",
    lever: "More parallel layers cuts secondary loss sharply but uses up the " +
           "14-layer budget."
  },
  {
    key: "copper_oz", type: "select", label: "Copper weight",
    why: "Thickness of the copper foil, quoted in ounces per square foot. " +
         "1 oz is 35 microns, 3 oz is 104 microns.",
    lever: "Thicker copper only helps up to about one skin depth; past that " +
           "the extra metal carries almost no current."
  },
  {
    key: "interleave", type: "toggle", label: "Interleave the windings",
    why: "Alternate primary and secondary layers instead of stacking each in " +
         "one block. This resets the magnetic field between layers and can cut " +
         "AC resistance several-fold.",
    lever: "Big loss win; costs interwinding capacitance and therefore noise."
  },
  {
    key: "dielectric_um", type: "range", label: "Layer-to-layer dielectric",
    min: 50, max: 400, step: 25, unit: "µm", scale: 1, digits: 0,
    why: "Insulation thickness between ordinary adjacent layers.",
    lever: "Thinner packs the board tighter; thicker reduces capacitance."
  },
  {
    key: "barrier_um", type: "range", label: "Safety barrier thickness",
    min: 200, max: 800, step: 50, unit: "µm", scale: 1, digits: 0,
    why: "Insulation where the stack crosses between high and low voltage. " +
         "This one is a safety barrier, not just a spacer: the top cell's " +
         "primary floats near the full 800 V bus relative to the output.",
    lever: "Thicker is safer and lowers capacitance, but raises leakage " +
           "inductance and weakens coupling."
  },
  {
    key: "deadtime_ns", type: "range", label: "Switching deadtime",
    min: 5, max: 60, step: 2.5, unit: "ns", scale: 1, digits: 1,
    why: "The pause where both transistors are off. During this gap the tank " +
         "current has to drain the switch node so the next device turns on at " +
         "zero volts.",
    lever: "Longer deadtime makes lossless switching easier but wastes duty cycle."
  },
  {
    key: "lm_fraction_of_limit", type: "range", label: "Magnetising inductance",
    min: 0.3, max: 1.2, step: 0.05, unit: "× ZVS limit", scale: 1, digits: 2,
    why: "Set as a fraction of the largest value that still permits lossless " +
         "switching. Below 1.0 you have margin; above 1.0 you have lost it.",
    lever: "Lower gives switching margin and costs circulating current at all loads."
  },
  {
    key: "ln_ratio", type: "range", label: "Lm / Lr ratio",
    min: 3, max: 12, step: 0.5, unit: "", scale: 1, digits: 1,
    why: "How the two inductances relate. A low ratio gives a steep, controllable " +
         "gain curve; a high ratio gives a flatter one that is more tolerant of " +
         "component spread — which matters when eight cells must share.",
    lever: "Higher flattens the gain curve and helps the cells balance."
  },
  {
    key: "ambient_c", type: "range", label: "Inlet air temperature",
    min: 20, max: 60, step: 5, unit: "°C", scale: 1, digits: 0,
    why: "Air temperature arriving at the module. Not specified anywhere, so " +
         "the design is swept around whatever you set.",
    lever: "Hotter inlet eats directly into your temperature headroom."
  },
  {
    key: "airflow_m_s", type: "range", label: "Airflow",
    min: 0.5, max: 8, step: 0.5, unit: "m/s", scale: 1, digits: 1,
    why: "Air velocity over the module. The single largest unknown in the " +
         "thermal answer, which is why results are shown as a range.",
    lever: "More airflow buys temperature headroom cheaply, if you have it."
  },
  {
    key: "heatsink_k_w", type: "range", label: "Heatsink path",
    min: 0.5, max: 10, step: 0.5, unit: "K/W", scale: 1, digits: 1,
    why: "Thermal resistance from the transformer out to ambient through the " +
         "board and any heatsink. The core is only a couple of square " +
         "centimetres, so air alone cannot carry the heat away.",
    lever: "This is usually the difference between feasible and not."
  }
];

/* ------------------------------------------------------------ tooltips */

const tip = $("tooltip");
function showTip(html, ev) {
  tip.innerHTML = html;
  tip.hidden = false;
  const pad = 14;
  let x = ev.clientX + pad, y = ev.clientY + pad;
  const r = tip.getBoundingClientRect();
  if (x + r.width > innerWidth - 10) x = ev.clientX - r.width - pad;
  if (y + r.height > innerHeight - 10) y = ev.clientY - r.height - pad;
  tip.style.left = x + "px";
  tip.style.top = y + "px";
}
function hideTip() { tip.hidden = true; }

function attachTip(el, title, why, lever) {
  el.addEventListener("mousemove", (ev) => showTip(
    `<div class="t-title">${title}</div><div class="t-why">${why}</div>` +
    (lever ? `<div class="t-lever">${lever}</div>` : ""), ev));
  el.addEventListener("mouseleave", hideTip);
}

/* ------------------------------------------------------------- helpers */

const svg = (tag, attrs = {}) => {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
};
const fmt = (v, d = 2) => (v === null || v === undefined || !isFinite(v))
  ? "—" : Number(v).toFixed(d);

function frame(host, w, h) {
  host.innerHTML = "";
  const s = svg("svg", { viewBox: `0 0 ${w} ${h}`, preserveAspectRatio: "xMidYMid meet" });
  host.appendChild(s);
  return s;
}

function axes(s, x0, y0, x1, y1, xlabel, ylabel) {
  s.appendChild(svg("line", { x1: x0, y1: y1, x2: x1, y2: y1, class: "ax" }));
  s.appendChild(svg("line", { x1: x0, y1: y0, x2: x0, y2: y1, class: "ax" }));
  if (xlabel) {
    const t = svg("text", { x: (x0 + x1) / 2, y: y1 + 30, class: "axlabel",
      "text-anchor": "middle" });
    t.textContent = xlabel; s.appendChild(t);
  }
  if (ylabel) {
    const t = svg("text", { x: x0 - 34, y: (y0 + y1) / 2, class: "axlabel",
      "text-anchor": "middle",
      transform: `rotate(-90 ${x0 - 34} ${(y0 + y1) / 2})` });
    t.textContent = ylabel; s.appendChild(t);
  }
}

function polyline(s, pts, stroke, width = 2, dash = null) {
  const p = svg("polyline", {
    points: pts.map(([x, y]) => `${x},${y}`).join(" "),
    fill: "none", stroke, "stroke-width": width,
    "stroke-linejoin": "round", "stroke-linecap": "round"
  });
  if (dash) p.setAttribute("stroke-dasharray", dash);
  s.appendChild(p);
  return p;
}

function label(s, x, y, text, fill, anchor = "start", size = 10.5) {
  const t = svg("text", { x, y, fill, "text-anchor": anchor,
    "font-size": size, "font-weight": 600 });
  t.textContent = text; s.appendChild(t); return t;
}

const WINDING_COLOR = {
  primary: "#c97b3c",
  secondary_a: "#4aa3ff",
  secondary_b: "#2d7fd0",
  none: "#3a4插"
};
const windingName = (w) => ({
  primary: "Primary (high voltage)",
  secondary_a: "Secondary A",
  secondary_b: "Secondary B"
}[w] || w);

/* ------------------------------------------------------- build controls */

function buildControls() {
  const host = $("control-list");
  host.innerHTML = "";
  for (const c of CONTROLS) {
    const wrap = document.createElement("div");
    wrap.className = "ctrl" + (c.type === "toggle" ? " toggle" : "");

    if (c.type === "toggle") {
      const lab = document.createElement("label");
      const box = document.createElement("input");
      box.type = "checkbox"; box.id = "c_" + c.key;
      box.checked = !!STATE[c.key];
      box.addEventListener("change", () => { STATE[c.key] = box.checked; run(); });
      const span = document.createElement("span");
      span.className = "ctrl-label"; span.textContent = c.label;
      attachTip(span, c.label, c.why, c.lever);
      lab.append(box, span);
      wrap.appendChild(lab);
    } else {
      const head = document.createElement("div");
      head.className = "ctrl-head";
      const lab = document.createElement("span");
      lab.className = "ctrl-label"; lab.textContent = c.label;
      attachTip(lab, c.label, c.why, c.lever);
      const val = document.createElement("span");
      val.className = "ctrl-value"; val.id = "v_" + c.key;
      head.append(lab, val);
      wrap.appendChild(head);

      if (c.type === "range") {
        const input = document.createElement("input");
        input.type = "range"; input.id = "c_" + c.key;
        input.min = c.min; input.max = c.max; input.step = c.step;
        input.value = STATE[c.key];
        const paint = () => {
          val.textContent = fmt(input.value * (c.scale || 1), c.digits) +
            (c.unit ? " " + c.unit : "");
        };
        paint();
        input.addEventListener("input", () => {
          STATE[c.key] = parseFloat(input.value); paint(); run();
        });
        wrap.appendChild(input);
      } else if (c.type === "select") {
        const sel = document.createElement("select");
        sel.id = "c_" + c.key;
        let items = [];
        if (c.key === "core_part") {
          items = OPTIONS.cores.map(o => ({
            value: o.part,
            text: o.label + (o.fits_height ? "" : "  — too tall")
          }));
        } else if (c.key === "material") {
          items = OPTIONS.materials.map(m => ({
            value: m.name,
            text: `${m.name} (${m.manufacturer}, ${m.band_lo_MHz}–${m.band_hi_MHz} MHz)`
          }));
        } else if (c.key === "copper_oz") {
          items = OPTIONS.copper_weights.map(o => ({
            value: o, text: `${o} oz  (${(o * 34.8).toFixed(0)} µm)`
          }));
        }
        for (const it of items) {
          const opt = document.createElement("option");
          opt.value = it.value; opt.textContent = it.text;
          if (String(STATE[c.key]) === String(it.value)) opt.selected = true;
          sel.appendChild(opt);
        }
        sel.addEventListener("change", () => {
          STATE[c.key] = c.key === "copper_oz" ? parseFloat(sel.value) : sel.value;
          run();
        });
        val.textContent = "";
        wrap.appendChild(sel);
      }
    }

    if (c.key === "material" && OPTIONS.unavailable_materials.length) {
      const note = document.createElement("div");
      note.className = "ctrl-note";
      note.textContent = "Not selectable (no retrievable loss data): " +
        OPTIONS.unavailable_materials.join(", ");
      wrap.appendChild(note);
    }
    host.appendChild(wrap);
  }
}

/* ------------------------------------------------------------- rendering */

function renderVerdict(res) {
  const el = $("verdict");
  el.className = "verdict " + (res.ok ? "pass" : "fail");
  const failed = res.gates.filter(g => !g.passed);
  $("verdict-text").textContent = res.ok
    ? "All gates pass"
    : `${failed.length} gate${failed.length > 1 ? "s" : ""} failing: ${failed[0].name}`;
}

function renderGates(res) {
  const host = $("gatebar");
  host.innerHTML = "";
  for (const g of res.gates) {
    const el = document.createElement("div");
    el.className = "gate " + (g.passed ? "pass" : "fail");
    el.innerHTML = `<span class="ico">${g.passed ? "✓" : "✕"}</span>` +
      `<span>${g.name}</span>`;
    attachTip(el, g.name,
      `<b>${g.value}</b> against a limit of <b>${g.limit}</b>.<br><br>${g.why}`,
      "Lever: " + g.lever);
    host.appendChild(el);
  }
}

function renderCards(res) {
  const m = res.metrics;
  const cards = [
    { k: "Efficiency", v: (m.efficiency * 100).toFixed(2), u: "%",
      good: m.efficiency > 0.985 },
    { k: "Total loss", v: fmt(m.total_loss_W, 2), u: "W" },
    { k: "Peak flux", v: fmt(m.b_peak_mT, 1), u: "mT",
      good: m.b_peak_mT < m.b_limit_mT },
    { k: "Hot spot", v: fmt(m.winding_c, 0), u: "°C",
      bad: m.winding_c > 125 },
    { k: "ZVS margin", v: (m.zvs_margin * 100).toFixed(0), u: "%",
      good: m.zvs_margin > 0, bad: m.zvs_margin <= 0 },
    { k: "Coupling cap", v: fmt(m.c_ps_pF, 1), u: "pF" },
    { k: "Layers used", v: m.layers, u: `of ${OPTIONS.fixed.max_layers}`,
      bad: m.layers > OPTIONS.fixed.max_layers },
    { k: "Board", v: fmt(m.board_thickness_mm, 2), u: "mm thick" }
  ];
  $("cards").innerHTML = cards.map(c =>
    `<div class="card ${c.bad ? "bad" : c.good ? "good" : ""}">
       <div class="k">${c.k}</div>
       <div class="v">${c.v}<span class="u"> ${c.u}</span></div>
     </div>`).join("");
}

/* -------- cross-section: the single most useful picture for a newcomer */

function renderStackup(res) {
  const g = res.geometry;
  const host = $("viz-stackup");
  const W = 900, H = 340, padL = 150, padR = 210, padT = 20;
  const s = frame(host, W, H);

  const totalMm = g.layers.reduce((a, l) => a + l.thickness_mm, 0) +
    g.dielectrics.reduce((a, d) => a + d.thickness_mm, 0);
  const drawH = H - padT - 30;
  const scale = drawH / Math.max(totalMm, 0.001);
  const x0 = padL, x1 = W - padR;

  // Ferrite above and below: the core wraps the board.
  const coreH = 26;
  for (const y of [padT - coreH - 2, padT + drawH + 2]) {
    s.appendChild(svg("rect", { x: x0 - 40, y, width: (x1 - x0) + 80,
      height: coreH, fill: "var(--ferrite)", rx: 3 }));
  }
  label(s, x0 - 46, padT - coreH + 15, "ferrite core", "#c3ccd8", "end");
  label(s, x0 - 46, padT + drawH + 20, "ferrite core", "#c3ccd8", "end");

  // Layers from the top of the stack downward.
  const ordered = [...g.layers].sort((a, b) => b.z_mm - a.z_mm);
  let y = padT;
  const dielByBelow = Object.fromEntries(g.dielectrics.map(d => [d.below, d]));

  for (let i = 0; i < ordered.length; i++) {
    const layer = ordered[i];
    const h = Math.max(layer.thickness_mm * scale, 3);
    const color = WINDING_COLOR[layer.winding] || "#556";
    const rect = svg("rect", { x: x0, y, width: x1 - x0, height: h,
      fill: color, rx: 1.5 });
    attachTip(rect, `${layer.name} — ${windingName(layer.winding)}`,
      `${layer.turns} turn(s), ${fmt(layer.thickness_mm * 1000, 0)} µm copper.<br>` +
      `Mean turn length ${fmt(layer.mlt_mm, 1)} mm.`,
      "Copper thickness is set by the copper-weight control.");
    s.appendChild(rect);

    label(s, x0 - 10, y + h / 2 + 3.5, layer.name, "#c3ccd8", "end");
    label(s, x1 + 12, y + h / 2 + 3.5,
      `${windingName(layer.winding)} · ${layer.turns}T`, color, "start");
    y += h;

    const d = dielByBelow[layer.index] ||
      dielByBelow[ordered[i + 1] ? ordered[i + 1].index : -1];
    if (i < ordered.length - 1) {
      const between = g.dielectrics.find(dd => {
        const lo = Math.min(layer.index, ordered[i + 1].index);
        const hi = Math.max(layer.index, ordered[i + 1].index);
        return dd.below >= lo && dd.below < hi;
      });
      if (between) {
        const dh = Math.max(between.thickness_mm * scale, 2);
        const isBar = between.is_barrier;
        const r = svg("rect", { x: x0, y, width: x1 - x0, height: dh,
          fill: isBar ? "var(--barrier)" : "var(--dielectric)", rx: 1.5,
          opacity: isBar ? 0.95 : 0.8 });
        attachTip(r, isBar ? "Safety isolation barrier" : "Dielectric",
          isBar
            ? `${fmt(between.thickness_mm * 1000, 0)} µm. This is the barrier ` +
              `between hazardous voltage and the low-voltage output. Because ` +
              `eight cells stack in series, the top cell's primary sits near ` +
              `the full 800 V bus relative to this output — not 100 V.`
            : `${fmt(between.thickness_mm * 1000, 0)} µm between adjacent layers.`,
          isBar ? "Thicker is safer, but raises leakage inductance."
                : "Thinner packs the board; thicker cuts capacitance.");
        s.appendChild(r);
        if (isBar && dh > 7) {
          label(s, (x0 + x1) / 2, y + dh / 2 + 3.5,
            `isolation barrier  ${fmt(between.thickness_mm * 1000, 0)} µm`,
            "#e3d9ff", "middle", 10);
        }
        y += dh;
      }
    }
  }

  const cap = $("stackup-caption");
  const barriers = g.dielectrics.filter(d => d.is_barrier).length;
  cap.innerHTML =
    `Board is <b>${fmt(totalMm, 2)} mm</b> thick across ` +
    `<b>${g.layers.length}</b> copper layers, with <b>${barriers}</b> ` +
    `isolation barrier${barriers === 1 ? "" : "s"} (purple). Orange is the ` +
    `high-voltage primary, blue the 60 A secondary. Thick insulation is placed ` +
    `only where the stack actually crosses between them — putting it everywhere ` +
    `would make the board unbuildably thick for no safety gain.`;
}

/* ------------------------------------- top view: what the copper looks like */

function renderTop(res) {
  const g = res.geometry;
  const host = $("viz-top");
  const W = 430, H = 340;
  const s = frame(host, W, H);

  const spanY = g.board_y_mm, spanX = g.board_x_mm;
  const scale = Math.min((W - 60) / spanX, (H - 50) / spanY);
  const cx = W / 2, cy = H / 2;
  const mm = (v) => v * scale;

  s.appendChild(svg("rect", {
    x: cx - mm(spanX) / 2, y: cy - mm(spanY) / 2,
    width: mm(spanX), height: mm(spanY),
    fill: "none", stroke: "var(--line)", "stroke-width": 1.5, rx: 3
  }));

  const post = svg("rect", {
    x: cx - mm(g.core.post_short_mm) / 2, y: cy - mm(g.core.post_long_mm) / 2,
    width: mm(g.core.post_short_mm), height: mm(g.core.post_long_mm),
    fill: "var(--ferrite)", rx: 2
  });
  attachTip(post, "Centre post",
    `${fmt(g.core.post_short_mm, 2)} × ${fmt(g.core.post_long_mm, 2)} mm, ` +
    `cross-section ${fmt(g.core.ae_mm2, 0)} mm². All the flux goes through here.<br><br>` +
    `Note it is a wide rectangle, not a circle — which is why the turns are ` +
    `racetrack-shaped rather than round.`,
    "A larger post area means lower flux density.");
  s.appendChild(post);

  const primary = g.layers.find(l => l.winding === "primary");
  const secondary = g.layers.find(l => l.winding !== "primary" && l.tracks.length);

  // One primary layer and one secondary layer, drawn together so the two can
  // be compared. Turn edges get a thin dark outline, otherwise adjacent turns
  // merge into an unreadable block: the copper really does nearly fill the
  // window, which is itself worth seeing.
  const shown = [];
  for (const [layer, color] of [
    [secondary, WINDING_COLOR.secondary_a],
    [primary, WINDING_COLOR.primary]
  ]) {
    if (!layer) continue;
    shown.push(`${layer.name} (${windingName(layer.winding).toLowerCase()})`);
    for (const t of layer.tracks) {
      const rx = mm(g.core.post_short_mm / 2 + t.offset_mm);
      const ry = mm(g.core.post_long_mm / 2 + t.offset_mm);
      const band = svg("rect", {
        x: cx - rx, y: cy - ry, width: 2 * rx, height: 2 * ry,
        rx: mm(t.offset_mm), ry: mm(t.offset_mm),
        fill: "none", stroke: color,
        "stroke-width": Math.max(mm(t.width_mm), 1.5), opacity: 0.88
      });
      attachTip(band, `${windingName(layer.winding)} turn ${t.offset_mm ? "" : ""}`,
        `Track <b>${fmt(t.width_mm, 2)} mm</b> wide, <b>${fmt(t.length_mm, 1)} mm</b> ` +
        `long, sitting ${fmt(t.offset_mm, 2)} mm out from the post face.<br><br>` +
        `Each turn has its own length because it sits at a different radius, ` +
        `so the inner turn is genuinely shorter than the outer one.`,
        "Wider tracks lower resistance, but fewer of them fit in the window.");
      s.appendChild(band);

      for (const edge of [-t.width_mm / 2, t.width_mm / 2]) {
        const ex = mm(g.core.post_short_mm / 2 + t.offset_mm + edge);
        const ey = mm(g.core.post_long_mm / 2 + t.offset_mm + edge);
        s.appendChild(svg("rect", {
          x: cx - ex, y: cy - ey, width: 2 * ex, height: 2 * ey,
          rx: Math.max(mm(t.offset_mm + edge), 0),
          ry: Math.max(mm(t.offset_mm + edge), 0),
          fill: "none", stroke: "#0e1117", "stroke-width": 1, opacity: 0.85
        }));
      }
    }
  }

  label(s, 10, 18, "■ primary", WINDING_COLOR.primary);
  label(s, 10, 33, "■ secondary", WINDING_COLOR.secondary_a);
  label(s, 10, 48, "■ core post", "#8b96a5");

  const nPri = primary ? primary.tracks.length : 0;
  const nSec = secondary ? secondary.tracks.length : 0;
  $("top-caption").innerHTML =
    `Looking down through the board, showing ${shown.join(" and ")}. Copper ` +
    `wraps the centre post as <b>racetracks</b>, not circles, because an ELP ` +
    `post is a wide rectangle (${fmt(g.core.post_long_mm, 1)} × ` +
    `${fmt(g.core.post_short_mm, 1)} mm). This layer carries <b>${nPri}</b> ` +
    `primary and <b>${nSec}</b> secondary turn(s), and they very nearly fill ` +
    `the available window — which is why adding turns quickly runs out of room.`;
}

/* ----------------------------------------------------------- loss budget */

function renderLoss(res) {
  const m = res.metrics;
  const host = $("viz-loss");
  const W = 430, H = 300;
  const s = frame(host, W, H);

  const items = [
    ["Core", m.core_loss_W, "#a06cd5",
     "Energy lost magnetising and demagnetising the ferrite every cycle."],
    ["Primary copper", m.primary_loss_W, WINDING_COLOR.primary,
     "Resistive loss in the high-voltage winding."],
    ["Secondary copper", m.secondary_loss_W, WINDING_COLOR.secondary_a,
     "Resistive loss in the 60 A winding. Usually the biggest single item."],
    ["Vias", m.via_loss_W, "#3fb950",
     "Loss in the plated holes that connect parallel secondary layers. " +
     "Frequently left out of estimates entirely."]
  ];
  const total = items.reduce((a, [, v]) => a + v, 0) || 1;

  const barY = 30, barH = 52, x0 = 20, x1 = W - 20;
  let x = x0;
  for (const [name, val, color, why] of items) {
    const w = (val / total) * (x1 - x0);
    const r = svg("rect", { x, y: barY, width: Math.max(w, 0), height: barH,
      fill: color });
    attachTip(r, name,
      `<b>${fmt(val, 2)} W</b>, ${(val / total * 100).toFixed(1)}% of the ` +
      `${fmt(total, 2)} W lost in this transformer.<br><br>${why}`, "");
    s.appendChild(r);
    if (w > 42) {
      label(s, x + w / 2, barY + barH / 2 + 4,
        `${(val / total * 100).toFixed(0)}%`, "#0e1117", "middle", 12);
    }
    x += w;
  }

  let ly = barY + barH + 34;
  for (const [name, val, color] of items) {
    s.appendChild(svg("rect", { x: x0, y: ly - 9, width: 11, height: 11,
      fill: color, rx: 2 }));
    label(s, x0 + 18, ly, name, "#c3ccd8", "start", 12);
    label(s, x1, ly, `${fmt(val, 2)} W`, "#e6edf3", "end", 12);
    ly += 22;
  }

  label(s, x0, ly + 8, "Total", "#9aa7b6", "start", 12);
  label(s, x1, ly + 8, `${fmt(total, 2)} W`, "#e6edf3", "end", 12);
  label(s, x0, ly + 28, "Efficiency (transformer only)", "#9aa7b6", "start", 12);
  label(s, x1, ly + 28, `${(m.efficiency * 100).toFixed(2)} %`,
    m.efficiency > 0.985 ? "#3fb950" : "#e6edf3", "end", 12);

  $("loss-caption").innerHTML =
    `Skin depth here is <b>${fmt(m.skin_depth_um, 0)} µm</b> and the copper is ` +
    `<b>${fmt(m.copper_thickness_um, 0)} µm</b> thick. When those are ` +
    `comparable, current stops using the middle of the conductor and adding ` +
    `metal stops helping. This is a transformer-only figure and excludes the ` +
    `transistors.`;
}

/* ------------------------------------------------------------- waveforms */

function renderWaves(res) {
  const w = res.waveforms;
  const host = $("viz-waves");
  const W = 430, H = 300, padL = 52, padR = 14, padT = 16, padB = 42;
  const s = frame(host, W, H);

  const series = [
    ["i_primary_A", "#e0a56a", "primary"],
    ["i_resonant_A", "#4aa3ff", "resonant"],
    ["i_magnetizing_A", "#f85149", "magnetising"]
  ];
  let lo = 0, hi = 0;
  for (const [k] of series) {
    lo = Math.min(lo, ...w[k]); hi = Math.max(hi, ...w[k]);
  }
  const span = Math.max(hi - lo, 1e-9);
  const X = (i) => padL + (i / (w.t_ns.length - 1)) * (W - padL - padR);
  const Y = (v) => padT + (1 - (v - lo) / span) * (H - padT - padB);

  axes(s, padL, padT, W - padR, H - padB, "time through one cycle (ns)", "amperes");
  s.appendChild(svg("line", { x1: padL, y1: Y(0), x2: W - padR, y2: Y(0),
    class: "gridline" }));

  for (const [k, color] of series) {
    polyline(s, w[k].map((v, i) => [X(i), Y(v)]), color, 2);
  }
  let ly = padT + 10;
  for (const [, color, name] of series) {
    label(s, W - padR - 6, ly, name, color, "end"); ly += 15;
  }
  label(s, padL - 6, Y(hi) + 4, fmt(hi, 0), "#6e7d8f", "end");
  label(s, padL - 6, Y(lo) + 4, fmt(lo, 0), "#6e7d8f", "end");
  label(s, padL, H - padB + 15, "0", "#6e7d8f", "middle");
  label(s, W - padR, H - padB + 15, fmt(w.t_ns[w.t_ns.length - 1], 0),
    "#6e7d8f", "middle");

  const m = res.metrics;
  $("waves-caption").innerHTML =
    `The primary current is the sum of two things: a <b>resonant</b> component ` +
    `that delivers power to the load, and a <b>magnetising</b> component that ` +
    `just circulates. At the switching instant the resonant part is at zero, ` +
    `so only the magnetising current — here ` +
    `<b>${fmt(m.i_magnetizing_peak_A, 2)} A</b> — is available to switch the ` +
    `transistors cleanly. That is the whole reason magnetising inductance is a ` +
    `design variable rather than something to maximise.`;
}

/* ------------------------------------------------------------------ flux */

function renderFlux(res) {
  const w = res.waveforms, m = res.metrics;
  const host = $("viz-flux");
  const W = 430, H = 300, padL = 56, padR = 14, padT = 16, padB = 42;
  const s = frame(host, W, H);
  if (!w.flux_mT.length) { host.innerHTML = "<p class='caption'>no flux data</p>"; return; }

  const hi = Math.max(...w.flux_mT.map(Math.abs), m.b_limit_mT * 0.35);
  const X = (i) => padL + (i / (w.flux_mT.length - 1)) * (W - padL - padR);
  const Y = (v) => padT + (1 - (v + hi) / (2 * hi)) * (H - padT - padB);

  axes(s, padL, padT, W - padR, H - padB, "time through one cycle (ns)",
    "flux density (mT)");
  s.appendChild(svg("line", { x1: padL, y1: Y(0), x2: W - padR, y2: Y(0),
    class: "gridline" }));

  polyline(s, w.flux_mT.map((v, i) => [X(i), Y(v)]), "#a06cd5", 2.4);
  label(s, padL - 6, Y(m.b_peak_mT) + 4, fmt(m.b_peak_mT, 0), "#a06cd5", "end");
  label(s, padL - 6, Y(-m.b_peak_mT) + 4, fmt(-m.b_peak_mT, 0), "#a06cd5", "end");

  $("flux-caption").innerHTML =
    `A square voltage across the winding integrates into a <b>triangular</b> ` +
    `flux, not a sine. That matters: datasheet loss figures are measured with ` +
    `sinusoids, and applying them directly would overstate this loss. FORGE ` +
    `integrates the real waveform instead. Peak is ` +
    `<b>${fmt(m.b_peak_mT, 1)} mT</b> against a derated ceiling of ` +
    `${fmt(m.b_limit_mT, 0)} mT.`;
}

/* ------------------------------------------------------------ gain curve */

function renderGain(res) {
  const c = res.curves;
  const host = $("viz-gain");
  const W = 430, H = 300, padL = 52, padR = 14, padT = 16, padB = 42;
  const s = frame(host, W, H);

  const all = c.gain_full_load.concat(c.gain_light_load);
  const hi = Math.min(Math.max(...all), 3);
  const X = (i) => padL + (i / (c.gain_fn.length - 1)) * (W - padL - padR);
  const Y = (v) => padT + (1 - Math.min(v, hi) / hi) * (H - padT - padB);

  axes(s, padL, padT, W - padR, H - padB,
    "switching frequency ÷ resonant frequency", "voltage gain");

  const oneIdx = c.gain_fn.findIndex(v => v >= 1);
  if (oneIdx > 0) {
    s.appendChild(svg("line", { x1: X(oneIdx), y1: padT, x2: X(oneIdx),
      y2: H - padB, class: "gridline" }));
    label(s, X(oneIdx) + 5, padT + 12, "resonance", "#6e7d8f");
  }

  polyline(s, c.gain_full_load.map((v, i) => [X(i), Y(v)]), "#4aa3ff", 2.2);
  polyline(s, c.gain_light_load.map((v, i) => [X(i), Y(v)]), "#3fb950", 2, "5 4");
  label(s, W - padR - 6, padT + 12, "full load", "#4aa3ff", "end");
  label(s, W - padR - 6, padT + 27, "light load", "#3fb950", "end");

  $("gain-caption").innerHTML =
    `This converter is a <b>fixed-ratio</b> stage: it is designed to sit at ` +
    `resonance, where the gain is exactly 1 regardless of load, so the output ` +
    `simply tracks the input divided by twice the turns ratio. The flatness of ` +
    `these curves near resonance is what lets eight independent cells share ` +
    `the bus without fighting each other.`;
}

/* ----------------------------------------------------------- thermal map */

function renderThermal(res) {
  const t = res.curves.thermal;
  const host = $("viz-thermal");
  const W = 430, H = 300, padL = 62, padR = 60, padT = 20, padB = 46;
  const s = frame(host, W, H);

  const rows = t.ambients.length, cols = t.velocities.length;
  const cw = (W - padL - padR) / cols, ch = (H - padT - padB) / rows;
  const flat = t.winding_c.flat();
  const lo = Math.min(...flat), hi = Math.max(...flat);
  const limit = 125;

  const color = (v) => {
    const f = Math.max(0, Math.min(1, (v - lo) / Math.max(hi - lo, 1e-6)));
    if (v > limit) return `hsl(0 70% ${34 + 16 * (1 - f)}%)`;
    return `hsl(${205 - 145 * f} 62% ${34 + 16 * (1 - f)}%)`;
  };

  for (let i = 0; i < rows; i++) {
    for (let j = 0; j < cols; j++) {
      const v = t.winding_c[i][j];
      const cell = svg("rect", { x: padL + j * cw, y: padT + i * ch,
        width: cw - 2, height: ch - 2, fill: color(v), rx: 3 });
      attachTip(cell, "Cooling corner",
        `Inlet ${fmt(t.ambients[i], 0)} °C, airflow ` +
        `${fmt(t.velocities[j], 1)} m/s.<br><br>Winding reaches ` +
        `<b>${fmt(v, 0)} °C</b> against a 125 °C limit; core reaches ` +
        `${fmt(t.core_c[i][j], 0)} °C against 100 °C.`,
        v > limit ? "This corner fails. More airflow or a better heatsink path."
                  : "This corner passes.");
      s.appendChild(cell);
      label(s, padL + j * cw + cw / 2, padT + i * ch + ch / 2 + 4,
        fmt(v, 0), v > limit ? "#fff" : "#e6edf3", "middle", 12);
    }
    label(s, padL - 8, padT + i * ch + ch / 2 + 4,
      `${fmt(t.ambients[i], 0)} °C`, "#9aa7b6", "end");
  }
  for (let j = 0; j < cols; j++) {
    label(s, padL + j * cw + cw / 2, H - padB + 16,
      `${fmt(t.velocities[j], 1)}`, "#9aa7b6", "middle");
  }
  label(s, padL + (W - padL - padR) / 2, H - padB + 34,
    "airflow (m/s)", "#6e7d8f", "middle");
  label(s, padL - 46, padT + (H - padT - padB) / 2, "inlet air",
    "#6e7d8f", "middle");

  const worst = Math.max(...flat);
  $("thermal-caption").innerHTML =
    `Nobody has specified the airflow for this converter, so a single ` +
    `temperature would be a guess dressed as a result. Every corner has to ` +
    `pass. Worst case here is <b>${fmt(worst, 0)} °C</b> ` +
    `${worst > limit ? "which <b>exceeds</b>" : "against"} the 125 °C limit.`;
}

/* -------------------------------------------------------------- ZVS view */

function renderZvs(res) {
  const m = res.metrics;
  const host = $("viz-zvs");
  const W = 900, H = 150, padL = 150, padR = 40;
  const s = frame(host, W, H);

  const need = m.zvs_required_nC, have = m.zvs_available_nC;
  const max = Math.max(need, have) * 1.18;
  const scale = (W - padL - padR) / max;

  const bars = [
    ["Charge required", need, "#f85149", 28,
     "Charge sitting on the switch node: both transistors' output charge plus " +
     "stray capacitance. All of it must be moved during the deadtime."],
    ["Charge available", have, have >= need ? "#3fb950" : "#d29922", 76,
     "Magnetising current multiplied by the deadtime. This is the only current " +
     "available at the switching instant, because the resonant component is " +
     "passing through zero."]
  ];
  for (const [name, val, color, y, why] of bars) {
    const r = svg("rect", { x: padL, y, width: Math.max(val * scale, 2),
      height: 34, fill: color, rx: 4 });
    attachTip(r, name, `<b>${fmt(val, 0)} nC</b><br><br>${why}`, "");
    s.appendChild(r);
    label(s, padL - 12, y + 22, name, "#c3ccd8", "end", 12);
    label(s, padL + val * scale + 10, y + 22, `${fmt(val, 0)} nC`, color, "start", 12);
  }
  s.appendChild(svg("line", { x1: padL + need * scale, y1: 18,
    x2: padL + need * scale, y2: 122, stroke: "#f85149",
    "stroke-width": 1.5, "stroke-dasharray": "4 4" }));

  $("zvs-caption").innerHTML = m.zvs_margin >= 0
    ? `There is <b>${(m.zvs_margin * 100).toFixed(0)}%</b> more charge than ` +
      `needed, so the transistors are predicted to turn on at zero volts and ` +
      `waste nothing doing it. Note <b>predicted</b>: confirming this needs a ` +
      `switched simulation with real device models, and ultimately a ` +
      `double-pulse measurement on hardware.`
    : `Short by <b>${Math.abs(m.zvs_margin * 100).toFixed(0)}%</b>. The ` +
      `transistors would turn on into a charged node and burn that energy ` +
      `every cycle. Lower the magnetising inductance or lengthen the deadtime.`;
}

/* ---------------------------------------------------------- metric table */

function renderTable(res) {
  const rows = Object.entries(res.metrics).map(([k, v]) =>
    `<tr><td>${k.replace(/_/g, " ")}</td><td>${
      typeof v === "number" ? v.toPrecision(6) : v}</td></tr>`).join("");
  $("metric-table").innerHTML = `<table class="metrics">${rows}</table>`;
}

/* -------------------------------------------------------------- driver */

async function run() {
  if (PENDING) { clearTimeout(PENDING); }
  PENDING = setTimeout(async () => {
    PENDING = null;
    let res;
    try {
      const r = await fetch("/api/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(STATE)
      });
      res = await r.json();
    } catch (e) {
      $("verdict-text").textContent = "server unreachable";
      return;
    }
    if (res.error) {
      $("verdict").className = "verdict fail";
      $("verdict-text").textContent = res.error;
      return;
    }
    renderVerdict(res);
    renderGates(res);
    renderCards(res);
    renderStackup(res);
    renderTop(res);
    renderLoss(res);
    renderWaves(res);
    renderFlux(res);
    renderGain(res);
    renderThermal(res);
    renderZvs(res);
    renderTable(res);
  }, 60);
}

async function init() {
  OPTIONS = await (await fetch("/api/options")).json();
  STATE = { ...OPTIONS.defaults };
  buildControls();
  $("btn-reset").addEventListener("click", () => {
    STATE = { ...OPTIONS.defaults }; buildControls(); run();
  });
  $("btn-copy").addEventListener("click", () => {
    navigator.clipboard.writeText(JSON.stringify(STATE, null, 2));
    $("btn-copy").textContent = "Copied";
    setTimeout(() => ($("btn-copy").textContent = "Copy design as JSON"), 1400);
  });
  $("toggle-primer").addEventListener("click", () => {
    const p = $("primer");
    p.hidden = !p.hidden;
    $("toggle-primer").textContent = p.hidden
      ? "New to this? Start here →" : "Hide the primer ↑";
  });
  run();
}

init();
