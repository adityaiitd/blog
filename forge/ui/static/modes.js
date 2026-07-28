/* Renderers for Learn, Parts and Sourcing modes. */

/* --------------------------------------------------------------- scope */

function renderScope() {
  const s = SCOPE;
  const list = (items) => `<ul class="scope-list">${
    items.map(i => `<li>${i}</li>`).join("")}</ul>`;
  const pairs = (items) => `<dl class="scope-pairs">${
    items.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>`;

  return `
  <section class="scope">
    <div class="scope-hero">
      <h1>${s.problem.title}</h1>
      <p>${s.problem.body}</p>
      <h2>${s.why_now.title}</h2>
      <p>${s.why_now.body}</p>
    </div>
    <div class="scope-cols">
      <div class="scope-card in">
        <h3>${s.in_scope.title}</h3>${list(s.in_scope.items)}
      </div>
      <div class="scope-card out">
        <h3>${s.out_of_scope.title}</h3>${list(s.out_of_scope.items)}
      </div>
    </div>
    <div class="scope-cols">
      <div class="scope-card solved">
        <h3>${s.solved.title}</h3>${pairs(s.solved.items)}
      </div>
      <div class="scope-card unsolved">
        <h3>${s.unsolved.title}</h3>${pairs(s.unsolved.items)}
      </div>
    </div>
    <p class="scope-foot">
      Everything below builds the reasoning from first principles. Each step
      has one thing you can change; the numbers update as you do.
    </p>
  </section>`;
}

/* ---------------------------------------------------------- mini diagrams */

function diagramChain(host) {
  const W = 460, H = 130;
  const s = frame(host, W, H);
  const blocks = [
    ["800 V\nDC", "#2a3342"],
    ["chop to\nAC", "#c97b3c"],
    ["trans-\nformer", "#a06cd5"],
    ["rectify\nto DC", "#4aa3ff"],
    ["12.5 V\nDC", "#2a3342"]
  ];
  const bw = 74, gap = 22, y = 34, h = 56;
  let x = 8;
  blocks.forEach(([text, color], i) => {
    s.appendChild(svg("rect", { x, y, width: bw, height: h, rx: 7,
      fill: color, opacity: 0.9 }));
    text.split("\n").forEach((ln, j) => {
      label(s, x + bw / 2, y + 24 + j * 14, ln, "#e6edf3", "middle", 11);
    });
    if (i < blocks.length - 1) {
      const ax = x + bw + 4;
      s.appendChild(svg("line", { x1: ax, y1: y + h / 2, x2: ax + gap - 8,
        y2: y + h / 2, stroke: "#6e7d8f", "stroke-width": 2 }));
      s.appendChild(svg("polygon", {
        points: `${ax + gap - 8},${y + h / 2} ${ax + gap - 14},${y + h / 2 - 4} ` +
                `${ax + gap - 14},${y + h / 2 + 4}`, fill: "#6e7d8f" }));
    }
    x += bw + gap;
  });
  label(s, W / 2, 18, "the three stages inside one cell", "#6e7d8f", "middle", 11);
  label(s, W / 2, H - 10,
    "a transformer only responds to change, so DC must be chopped first",
    "#6e7d8f", "middle", 10.5);
}

function diagramSkin(host, skinUm) {
  const W = 460, H = 150;
  const s = frame(host, W, H);
  const thicknesses = [[34.8, "1 oz"], [69.6, "2 oz"], [104.4, "3 oz"]];
  const scale = 0.62, x0 = 96;
  let y = 26;
  for (const [t, name] of thicknesses) {
    const h = t * scale;
    const depth = Math.min(skinUm * scale, h / 2);
    s.appendChild(svg("rect", { x: x0, y, width: 250, height: h,
      fill: "#3a4453", rx: 1 }));
    // Conducting shells at both surfaces.
    s.appendChild(svg("rect", { x: x0, y, width: 250, height: depth,
      fill: "#e0a56a" }));
    s.appendChild(svg("rect", { x: x0, y: y + h - depth, width: 250,
      height: depth, fill: "#e0a56a" }));
    label(s, x0 - 10, y + h / 2 + 4, `${name}, ${t} µm`, "#c3ccd8", "end", 11);
    const dead = Math.max(h - 2 * depth, 0);
    label(s, x0 + 258, y + h / 2 + 4,
      dead > 1 ? `${(dead / scale).toFixed(0)} µm carrying little`
               : "fully used", dead > 1 ? "#f85149" : "#3fb950", "start", 10.5);
    y += h + 16;
  }
  label(s, W / 2, H - 6,
    `orange is the conducting shell, one skin depth (${skinUm.toFixed(0)} µm) deep`,
    "#6e7d8f", "middle", 10.5);
}

function diagramStack(host) {
  const W = 460, H = 160;
  const s = frame(host, W, H);
  const rows = [
    ["ferrite", "#55606f", 14],
    ["secondary ×4", "#4aa3ff", 9],
    ["barrier", "#6b4bb8", 11],
    ["primary ×4", "#c97b3c", 9],
    ["barrier", "#6b4bb8", 11],
    ["secondary ×4", "#4aa3ff", 9],
    ["ferrite", "#55606f", 14]
  ];
  let y = 14;
  for (const [name, color, h] of rows) {
    s.appendChild(svg("rect", { x: 120, y, width: 230, height: h,
      fill: color, rx: 2 }));
    label(s, 112, y + h / 2 + 4, name, "#c3ccd8", "end", 10.5);
    y += h + 3;
  }
  label(s, W / 2, H - 8,
    "the board is the transformer: copper layers between two core halves",
    "#6e7d8f", "middle", 10.5);
}

/* ---------------------------------------------------------- learn steps */

const LEARN_STATE = {};

function renderLearn() {
  const host = document.createElement("div");
  host.className = "learn";
  host.innerHTML = renderScope();

  STEPS.forEach((step, index) => {
    const sec = document.createElement("section");
    sec.className = "step";
    sec.innerHTML = `
      <div class="step-num">${index + 1}</div>
      <div class="step-body">
        <h2>${step.title}</h2>
        <p class="lead">${step.lead}</p>
        <div class="lenses">
          <div class="lens mech"><h4>Mechanical picture</h4><p>${step.mech || ""}</p></div>
          <div class="lens elec"><h4>What is actually happening</h4><p>${step.elec || ""}</p></div>
        </div>
        ${step.breaks ? `<div class="breaks"><h4>Where the analogy breaks</h4>
          <p>${step.breaks}</p></div>` : ""}
      </div>
      <div class="step-side">
        <div class="step-viz" id="viz_${step.id}"></div>
        <div class="step-ctrl" id="ctrl_${step.id}"></div>
        <div class="step-read" id="read_${step.id}"></div>
        <div class="step-punch" id="punch_${step.id}"></div>
      </div>`;
    host.appendChild(sec);
  });

  const foot = document.createElement("section");
  foot.className = "learn-foot";
  foot.innerHTML = `
    <h2>That is the whole chain</h2>
    <p>
      A rack needs a megawatt, so power is distributed at 800 V to keep the
      current down. Chips need 12 V, so it must be stepped down close to the
      load. Transformers need AC, so the DC is chopped, transformed and
      rectified. One 64:1 step would need expensive slow transistors, so it is
      split into eight series cells of 8:1. The transformer for one cell is
      etched into a circuit board because nothing else fits in 8 mm or repeats
      well enough. And then every design choice fights with three others.
    </p>
    <p>
      Switch to <b>Explore</b> to change any of it and watch the real models
      recompute, <b>Parts</b> to see what physically goes in, or
      <b>Sourcing</b> for what it costs and where the supply risk sits.
    </p>`;
  host.appendChild(foot);
  return host;
}

function wireLearn() {
  for (const step of STEPS) {
    const vizHost = $(`viz_${step.id}`);
    if (step.diagram === "chain") diagramChain(vizHost);
    if (step.diagram === "stack") diagramStack(vizHost);

    if (!step.control) {
      if (step.diagram === "skin") diagramSkin(vizHost, 56);
      continue;
    }
    const c = step.control;
    LEARN_STATE[c.key] = c.value;
    const ctrl = $(`ctrl_${step.id}`);
    ctrl.innerHTML = `
      <div class="ctrl-head">
        <span class="ctrl-label">${c.label}</span>
        <span class="ctrl-value" id="lv_${step.id}"></span>
      </div>
      <input type="range" id="ls_${step.id}" min="${c.min}" max="${c.max}"
             step="${c.step}" value="${c.value}">`;

    const update = () => {
      const val = parseFloat($(`ls_${step.id}`).value);
      LEARN_STATE[c.key] = val;
      $(`lv_${step.id}`).textContent =
        (Number.isInteger(c.step) ? val.toFixed(0) : val.toFixed(2)) + c.unit;
      const r = step.compute(LEARN_STATE);
      $(`read_${step.id}`).innerHTML = `<table class="readout">${
        step.readout(r).map(([k, v]) =>
          `<tr><td>${k}</td><td>${v}</td></tr>`).join("")}</table>`;
      $(`punch_${step.id}`).innerHTML = step.punch(r);
      if (step.diagram === "skin") diagramSkin(vizHost, r.skin);
    };
    $(`ls_${step.id}`).addEventListener("input", update);
    update();
  }
}

/* --------------------------------------------------------------- parts */

const PART_DETAIL = {
  "EPC2305": {
    what: "A gallium nitride power transistor rated 150 V, two per cell.",
    does: "Forms the half bridge that chops the cell's 100 V DC into a " +
          "high-frequency square wave for the transformer.",
    why: "GaN switches far faster than silicon and stores much less charge in " +
         "its output capacitance. That charge is exactly what has to be moved " +
         "during the dead time for lossless switching, so less of it is a " +
         "direct efficiency gain.",
    wrong: "Too low a voltage rating and a single cell taking more than its " +
           "share of the bus destroys it. Too much output charge and " +
           "zero-voltage switching stops working, so loss climbs sharply."
  },
  "EPC2366": {
    what: "A 40 V gallium nitride transistor, four per cell.",
    does: "Synchronous rectification. Converts the transformer's AC secondary " +
          "back to DC, replacing diodes.",
    why: "At 60 A a diode would drop around half a volt and burn 30 W. A " +
         "transistor with sub-milliohm resistance drops a few millivolts " +
         "instead. Four in parallel share the current.",
    wrong: "Mistimed switching shoots through and shorts the secondary. " +
           "Too few in parallel and they overheat."
  },
  "LMG1020": {
    what: "A single-channel low-side gate driver.",
    does: "Turns the tiny logic signal from the controller into the current " +
          "needed to switch a GaN gate in a couple of nanoseconds.",
    why: "GaN gates need precise, fast drive with very little inductance. A " +
         "general-purpose driver is too slow and would waste the device's " +
         "main advantage.",
    wrong: "Slow or ringing gate drive causes partial turn-on, shoot-through, " +
           "or gate overvoltage, which GaN tolerates poorly."
  },
  "MP18831": {
    what: "An isolated two-channel gate driver.",
    does: "Drives the high-side transistor, whose source terminal swings " +
          "through the full cell voltage every cycle.",
    why: "The high-side device floats. Its driver needs galvanic isolation " +
         "and has to reject the high slew rate of the switching node.",
    wrong: "Poor common-mode transient immunity causes false triggering, and " +
           "a falsely triggered half bridge shorts the bus."
  },
  "ISO7740": {
    what: "A four-channel digital isolator, two per converter.",
    does: "Carries control and telemetry signals across the safety barrier " +
          "between the high-voltage side and the low-voltage control side.",
    why: "The primary side sits at hazardous potential. Every signal crossing " +
         "that boundary must cross an insulation barrier rated for the full " +
         "working voltage, not the local cell voltage.",
    wrong: "Under-rated isolation is a safety failure, not a performance one."
  },
  "DSPIC33CK256MP605": {
    what: "A 16-bit digital signal controller, one per converter.",
    does: "Generates the switching timing for all eight cells, manages " +
          "startup and dead time, monitors faults and handles telemetry.",
    why: "Eight cells must be interleaved in phase and started in a " +
         "controlled sequence. Doing that in analogue hardware is possible " +
         "but inflexible.",
    wrong: "Wrong dead time destroys efficiency or the transistors. " +
           "Uncontrolled startup lets one cell take the whole bus."
  },
  "MIE1W0505BGLVH": {
    what: "A 1 W isolated DC-DC converter module, one per cell.",
    does: "Provides the local 5 V supply for the floating high-side driver.",
    why: "Each cell's high-side circuitry floats at a different potential " +
         "along the 800 V stack, so each needs its own isolated bias.",
    wrong: "Insufficient isolation rating is a safety failure. Excess " +
           "coupling capacitance injects common-mode noise into the output."
  },
  "ELP18/4/10-3F46": {
    what: "A planar ferrite core set, two halves per transformer.",
    does: "Provides the magnetic path linking primary and secondary windings.",
    why: "ELP geometry is low profile, which is what fits inside 8 mm. The " +
         "3F46 material is formulated for 1 to 3 MHz, where this converter " +
         "runs. A standard power ferrite would lose far more here.",
    wrong: "Too small a cross-section saturates the core. The wrong material " +
           "runs hot and can go thermally unstable, since ferrite loss rises " +
           "with temperature beyond its minimum."
  },
  "PCB": {
    what: "A 12 to 14 layer printed circuit board with heavy copper.",
    does: "This is not a substrate holding a transformer. The etched copper " +
          "layers <em>are</em> the windings.",
    why: "Etched copper is repeatable to microns, which matters because the " +
         "leakage inductance is a functional part of the resonant circuit " +
         "rather than a parasitic to be minimised.",
    wrong: "Layer registration error changes leakage inductance and detunes " +
           "the tank. Insufficient dielectric between primary and secondary " +
           "is a safety failure."
  }
};

function renderParts(sourcing) {
  const host = document.createElement("div");
  host.className = "parts";
  const byMpn = Object.fromEntries((sourcing.lines || []).map(l => [l.mpn, l]));

  host.innerHTML = `
    <section class="scope-hero">
      <h1>What physically goes into one cell</h1>
      <p>
        Eight of these make the 6 kW converter. Every part answers the same
        four questions: what it is, what it does, why this one rather than
        something cheaper, and what happens if it is wrong.
      </p>
    </section>
    <div class="partgrid">
      ${Object.entries(PART_DETAIL).map(([mpn, d]) => {
        const line = byMpn[mpn];
        const price = line && line.unit_usd
          ? `$${line.unit_usd.toFixed(2)} each` : "price not published";
        const basis = line && line.basis === "estimated"
          ? `<span class="tag est">estimate</span>`
          : (line && line.unit_usd ? `<span class="tag q">quoted</span>` : "");
        const qty = line ? `${line.qty} per converter` : "";
        return `
        <article class="partcard">
          <header>
            <h3>${mpn}</h3>
            <div class="partmeta">${qty} ${basis}</div>
          </header>
          <dl>
            <dt>What it is</dt><dd>${d.what}</dd>
            <dt>What it does</dt><dd>${d.does}</dd>
            <dt>Why this one</dt><dd>${d.why}</dd>
            <dt>If it is wrong</dt><dd class="warn">${d.wrong}</dd>
          </dl>
          <footer>${price}${
            line && line.stock ? ` · ${line.stock.toLocaleString()} in stock` : ""
          }</footer>
        </article>`;
      }).join("")}
    </div>`;
  return host;
}

/* ------------------------------------------------------------- sourcing */

function renderSourcing(d) {
  const host = document.createElement("div");
  host.className = "sourcing";
  if (d.error) {
    host.innerHTML = `<section class="scope-hero"><h1>Sourcing</h1>
      <p>${d.error}</p></section>`;
    return host;
  }
  const s = d.summary;
  const money = (v) => v == null ? "—" : `$${v.toFixed(2)}`;

  const rows = d.lines.map(l => `
    <tr class="${l.basis}">
      <td>${l.mpn}<div class="sub">${l.role}</div></td>
      <td class="num">${l.qty}</td>
      <td class="num">${money(l.unit_usd)}</td>
      <td class="num">${money(l.extended_usd)}</td>
      <td><span class="tag ${l.basis === "quoted" ? "q" : "est"}">${
        l.basis}${l.confidence ? " · " + l.confidence : ""}</span></td>
      <td class="num">${l.stock ? l.stock.toLocaleString() : "—"}</td>
    </tr>`).join("");

  const curve = Object.entries(d.volume_curve).map(([v, x]) =>
    `<tr><td class="num">${(+v).toLocaleString()}</td>
      <td class="num">${money(x.components_usd)}</td>
      <td class="num">${money(x.total_usd)}</td>
      <td class="num">$${x.usd_per_kw.toFixed(2)}</td></tr>`).join("");

  const risks = d.risks.map(r => `
    <div class="risk ${r.severity}">
      <div class="risk-head"><span class="sev">${r.severity}</span>
        <strong>${r.part}</strong></div>
      <p>${r.concern}</p>
      <p class="mit">${r.mitigation}</p>
    </div>`).join("");

  host.innerHTML = `
    <section class="scope-hero">
      <h1>What it costs and what could go wrong</h1>
      <p>
        Prices are pulled live from vendors that publish them. Most large
        distributors block automated access outright, so where no price could
        be retrieved the line carries a labelled estimate instead. The two are
        never mixed: the summary states how much of the cost rests on real
        quotes.
      </p>
    </section>

    <div class="cards">
      <div class="card"><div class="k">Total per converter</div>
        <div class="v">${money(s.total_usd)}<span class="u"> 6 kW</span></div></div>
      <div class="card"><div class="k">Cost per kW</div>
        <div class="v">$${s.usd_per_kw.toFixed(2)}<span class="u"> /kW</span></div></div>
      <div class="card"><div class="k">On real quotes</div>
        <div class="v">${(s.quoted_fraction_of_cost * 100).toFixed(0)}<span class="u"> % of cost</span></div></div>
      <div class="card"><div class="k">Components</div>
        <div class="v">${money(s.component_cost_usd)}</div></div>
      <div class="card"><div class="k">Bare boards</div>
        <div class="v">${money(s.pcb_cost_usd)}<span class="u"> ×8</span></div></div>
      <div class="card"><div class="k">Assembly and test</div>
        <div class="v">${money(s.adder_cost_usd)}</div></div>
    </div>
    <p class="caveat-line">${s.caveat}</p>

    <div class="panelgrid">
      <figure class="panel wide">
        <figcaption><span>Bill of materials</span>
          <small>quoted lines are live vendor prices; estimates are judgement</small>
        </figcaption>
        <table class="bom">
          <thead><tr><th>Part</th><th class="num">Qty</th>
            <th class="num">Unit</th><th class="num">Extended</th>
            <th>Basis</th><th class="num">Stock</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </figure>

      <figure class="panel">
        <figcaption><span>Cost against build volume</span>
          <small>where the price breaks actually land</small></figcaption>
        <table class="bom">
          <thead><tr><th class="num">Units</th><th class="num">Components</th>
            <th class="num">Total</th><th class="num">Per kW</th></tr></thead>
          <tbody>${curve}</tbody>
        </table>
      </figure>

      <figure class="panel">
        <figcaption><span>What drives the cost</span>
          <small>where the money actually goes</small></figcaption>
        <ul class="drivers">
          <li><b>The GaN transistors.</b> 48 devices per converter, and they
            are over half the component cost. Any efficiency argument that
            needs more silicon has to pay for it here.</li>
          <li><b>Layer count.</b> The transformer board is 12 to 14 layers with
            heavy copper. Cost scales with lamination cycles and drilling, not
            with area, so a small board is not a cheap one.</li>
          <li><b>Parallel copies.</b> Each parallel secondary layer cuts loss
            and costs a layer. That trade is a cost decision as much as an
            electrical one.</li>
          <li><b>Core material.</b> A high-frequency ferrite carries a premium
            over standard power ferrite, and it is the enabler for running at
            2 MHz at all.</li>
        </ul>
      </figure>
    </div>

    <h2 class="risk-title">Supply and design risk</h2>
    <div class="riskgrid">${risks}</div>`;
  return host;
}


/* -------------------------------------------------------------- diagrams */

const RENDERS = [
  ["part_planar_transformer.jpg", "The transformer itself",
   "Two ferrite core halves clamped around a multilayer board. The copper " +
   "racetracks etched into the board are the windings — there is no wire in " +
   "this component at all."],
  ["part_ferrite_core.jpg", "Planar ferrite core set",
   "An ELP-style pair. Note the wide rectangular centre post: that shape is " +
   "why the turns are racetracks rather than circles, and it sets the mean " +
   "length of every turn."],
  ["part_stackup_cutaway.jpg", "Inside the board",
   "Alternating copper and dielectric, with the two thicker layers being the " +
   "safety barriers between the hazardous primary and the low-voltage " +
   "secondary. The vertical barrels are plated vias carrying secondary current."],
  ["part_gan_fet.jpg", "Gallium nitride transistor",
   "A few millimetres across. Forty-eight of these per converter, and over " +
   "half the component cost. The charge stored in its output capacitance is " +
   "what the tank has to drain for lossless switching."],
  ["part_converter_module.jpg", "The assembled converter",
   "Eight identical cells in a row, 8 mm tall, 6 kW total. High-voltage " +
   "input at one end, a wide copper output bar at the other."]
];

function renderDiagrams() {
  const host = document.createElement("div");
  host.className = "learn";
  host.innerHTML = `
    <section class="scope-hero">
      <h1>How it goes together</h1>
      <p>
        Schematics first, then what the parts physically look like. The
        diagrams are drawn from the same architecture the rest of the tool
        evaluates, so component counts, the turns ratio and the isolation
        boundaries all match. Hover anything for what it does.
      </p>
    </section>
    <div id="diagram-list"></div>
    <section class="scope-hero" style="margin-top:34px">
      <h2>The physical parts</h2>
      <p class="render-note">
        These are illustrative renders for orientation, not engineering
        drawings. Dimensions and markings in them are not authoritative; the
        numbers in Explore and Sourcing are.
      </p>
    </section>
    <div class="rendergrid">
      ${RENDERS.map(([file, title, caption]) => `
        <figure class="rendercard">
          <img src="/static/img/${file}" alt="${title}" loading="lazy">
          <figcaption><strong>${title}</strong><span>${caption}</span></figcaption>
        </figure>`).join("")}
    </div>`;
  return host;
}

function wireDiagrams() {
  const list = $("diagram-list");
  for (const [title, sub, fn] of DIAGRAMS) {
    const fig = document.createElement("figure");
    fig.className = "panel wide diagram";
    fig.innerHTML = `<figcaption><span>${title}</span><small>${sub}</small></figcaption>
      <div class="viz"></div>`;
    list.appendChild(fig);
    try { fn(fig.querySelector(".viz")); }
    catch (e) { fig.querySelector(".viz").innerHTML =
      `<p class="caption">diagram failed: ${e.message}</p>`; }
  }
}
