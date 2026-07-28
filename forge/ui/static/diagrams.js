/* Schematic diagrams, drawn from primitives so they stay accurate.
 *
 * These are wiring diagrams, not decoration: the component counts, the turns
 * ratio and the isolation boundaries match the design the rest of the tool
 * evaluates. If the architecture changes, these change with it.
 */

const SCH = {
  wire: "#8b96a5",
  hot: "#f85149",        // hazardous primary side
  cold: "#4aa3ff",       // low-voltage secondary side
  core: "#a06cd5",
  barrier: "#6b4bb8",
  ink: "#e6edf3",
  dim: "#6e7d8f"
};

function sline(s, x1, y1, x2, y2, stroke = SCH.wire, w = 1.6) {
  s.appendChild(svg("line", { x1, y1, x2, y2, stroke, "stroke-width": w,
    "stroke-linecap": "round" }));
}

function spath(s, d, stroke = SCH.wire, w = 1.6, fill = "none") {
  s.appendChild(svg("path", { d, stroke, "stroke-width": w, fill,
    "stroke-linejoin": "round", "stroke-linecap": "round" }));
}

function sdot(s, x, y, color = SCH.wire) {
  s.appendChild(svg("circle", { cx: x, cy: y, r: 3, fill: color }));
}

function stext(s, x, y, t, fill = SCH.ink, anchor = "start", size = 11, weight = 500) {
  const el = svg("text", { x, y, fill, "text-anchor": anchor,
    "font-size": size, "font-weight": weight });
  el.textContent = t; s.appendChild(el); return el;
}

/** N-channel MOSFET / GaN switch, drain up. */
function smosfet(s, x, y, label_, color = SCH.hot, tip = null) {
  const g = svg("g", {});
  s.appendChild(g);
  const put = (el) => g.appendChild(el);
  // Gate bar and channel bar
  put(svg("line", { x1: x - 14, y1: y - 10, x2: x - 14, y2: y + 10,
    stroke: color, "stroke-width": 1.6 }));
  put(svg("line", { x1: x - 8, y1: y - 11, x2: x - 8, y2: y - 4,
    stroke: color, "stroke-width": 2.4 }));
  put(svg("line", { x1: x - 8, y1: y - 3, x2: x - 8, y2: y + 3,
    stroke: color, "stroke-width": 2.4 }));
  put(svg("line", { x1: x - 8, y1: y + 4, x2: x - 8, y2: y + 11,
    stroke: color, "stroke-width": 2.4 }));
  // Drain, source, gate leads
  put(svg("line", { x1: x - 8, y1: y - 8, x2: x + 10, y2: y - 8,
    stroke: color, "stroke-width": 1.6 }));
  put(svg("line", { x1: x + 10, y1: y - 8, x2: x + 10, y2: y - 20,
    stroke: color, "stroke-width": 1.6 }));
  put(svg("line", { x1: x - 8, y1: y + 8, x2: x + 10, y2: y + 8,
    stroke: color, "stroke-width": 1.6 }));
  put(svg("line", { x1: x + 10, y1: y + 8, x2: x + 10, y2: y + 20,
    stroke: color, "stroke-width": 1.6 }));
  put(svg("line", { x1: x - 26, y1: y, x2: x - 14, y2: y,
    stroke: color, "stroke-width": 1.6 }));
  // Channel arrow
  put(svg("polygon", { points: `${x - 3},${y} ${x - 8},${y - 3} ${x - 8},${y + 3}`,
    fill: color }));
  if (label_) stext(s, x + 16, y + 3, label_, color, "start", 10.5, 600);
  if (tip) attachTip(g, tip[0], tip[1], tip[2] || "");
  return { drain: [x + 10, y - 20], source: [x + 10, y + 20], gate: [x - 26, y] };
}

/** Capacitor, vertical by default. */
function scap(s, x, y, label_, color = SCH.wire, horizontal = false, tip = null) {
  const g = svg("g", {}); s.appendChild(g);
  if (horizontal) {
    g.appendChild(svg("line", { x1: x - 3, y1: y - 11, x2: x - 3, y2: y + 11,
      stroke: color, "stroke-width": 2.2 }));
    g.appendChild(svg("line", { x1: x + 3, y1: y - 11, x2: x + 3, y2: y + 11,
      stroke: color, "stroke-width": 2.2 }));
  } else {
    g.appendChild(svg("line", { x1: x - 11, y1: y - 3, x2: x + 11, y2: y - 3,
      stroke: color, "stroke-width": 2.2 }));
    g.appendChild(svg("line", { x1: x - 11, y1: y + 3, x2: x + 11, y2: y + 3,
      stroke: color, "stroke-width": 2.2 }));
  }
  if (label_) stext(s, x + 15, y + 4, label_, color, "start", 10.5, 600);
  if (tip) attachTip(g, tip[0], tip[1], tip[2] || "");
}

/** Inductor as a run of arcs. */
function sind(s, x, y, label_, color = SCH.wire, horizontal = true, tip = null) {
  const g = svg("g", {}); s.appendChild(g);
  let d = "";
  if (horizontal) {
    d = `M ${x - 18} ${y}`;
    for (let i = 0; i < 4; i++) d += ` a 4.5 4.5 0 0 1 9 0`;
  } else {
    d = `M ${x} ${y - 18}`;
    for (let i = 0; i < 4; i++) d += ` a 4.5 4.5 0 0 0 0 9`;
  }
  g.appendChild(svg("path", { d, stroke: color, "stroke-width": 1.8, fill: "none" }));
  if (label_) stext(s, x + (horizontal ? 0 : 14), y + (horizontal ? -12 : 4),
    label_, color, horizontal ? "middle" : "start", 10.5, 600);
  if (tip) attachTip(g, tip[0], tip[1], tip[2] || "");
}

/* ------------------------------------------------- 1. ISOP architecture */

function diagramIsop(host) {
  const W = 900, H = 430;
  const s = frame(host, W, H);
  const cells = 8, cx = 150, top = 44, cellH = 40, gap = 5;

  stext(s, W / 2, 22, "Eight cells: inputs in series, outputs in parallel",
    SCH.ink, "middle", 13, 700);

  // 800 V rail down the left
  sline(s, 60, top - 14, 60, top + cells * (cellH + gap) - gap + 14, SCH.hot, 2.4);
  stext(s, 54, top - 20, "800 V DC", SCH.hot, "end", 11.5, 700);
  stext(s, 54, top - 7, "from the rack", SCH.dim, "end", 10);

  // 12.5 V output bus down the right
  const outX = 720;
  sline(s, outX, top - 14, outX, top + cells * (cellH + gap) - gap + 14, SCH.cold, 3.4);
  stext(s, outX + 12, top - 20, "12.5 V DC", SCH.cold, "start", 11.5, 700);
  stext(s, outX + 12, top - 7, "480 A to the compute", SCH.dim, "start", 10);

  for (let i = 0; i < cells; i++) {
    const y = top + i * (cellH + gap);
    const potentialTop = 800 - i * 100;
    const potentialBot = 800 - (i + 1) * 100;

    const g = svg("g", {});
    s.appendChild(g);
    g.appendChild(svg("rect", { x: cx, y, width: 420, height: cellH, rx: 6,
      fill: "#161b23", stroke: SCH.wire, "stroke-width": 1.2 }));

    // Inside each cell: bridge, transformer, rectifier
    stext(s, cx + 46, y + cellH / 2 + 4, "half bridge", SCH.hot, "middle", 9.5, 600);
    svgTransformerGlyph(s, cx + 170, y + cellH / 2);
    stext(s, cx + 300, y + cellH / 2 + 4, "sync rectifier", SCH.cold, "middle", 9.5, 600);

    attachTip(g, `Cell ${i + 1} of 8`,
      `Its primary floats between <b>${potentialBot} V</b> and ` +
      `<b>${potentialTop} V</b> with respect to the output.<br><br>` +
      `Locally it only switches 100 V, which is why cheap 150 V transistors ` +
      `work. But the insulation between this primary and the shared secondary ` +
      `has to withstand the full stack potential, not 100 V.`,
      i === cells - 1
        ? "This is the top cell: its barrier sees the whole bus."
        : "");

    // Series input taps
    sline(s, 60, y + cellH / 2, cx, y + cellH / 2, SCH.hot);
    sdot(s, 60, y + cellH / 2, SCH.hot);
    stext(s, 66, y + cellH / 2 - 5, `${potentialTop} V`, SCH.dim, "start", 9);

    // Parallel output taps
    sline(s, cx + 420, y + cellH / 2, outX, y + cellH / 2, SCH.cold);
    sdot(s, outX, y + cellH / 2, SCH.cold);
  }

  const bottomY = top + cells * (cellH + gap) - gap;
  sline(s, 60, bottomY + 14, 60, bottomY + 30, SCH.hot, 2.4);
  stext(s, 66, bottomY + 34, "0 V return", SCH.dim, "start", 10);

  stext(s, W / 2, H - 26,
    "Series inputs force the same current through every cell; parallel outputs force the same voltage.",
    SCH.dim, "middle", 11);
  stext(s, W / 2, H - 10,
    "Neither directly forces equal input voltages — whether the cells share is a question this design has to answer.",
    "#d29922", "middle", 11);
}

function svgTransformerGlyph(s, x, y) {
  // Two coils either side of a core
  spath(s, `M ${x - 16} ${y - 9} a 4 4 0 0 0 0 8 a 4 4 0 0 0 0 8`, SCH.hot, 1.6);
  spath(s, `M ${x + 16} ${y - 9} a 4 4 0 0 1 0 8 a 4 4 0 0 1 0 8`, SCH.cold, 1.6);
  sline(s, x - 4, y - 12, x - 4, y + 12, SCH.core, 1.8);
  sline(s, x + 4, y - 12, x + 4, y + 12, SCH.core, 1.8);
}

/* -------------------------------------------------- 2. One LLC cell */

function diagramCell(host) {
  const W = 900, H = 400;
  const s = frame(host, W, H);
  stext(s, W / 2, 20, "One cell: half-bridge LLC with a centre-tapped synchronous rectifier",
    SCH.ink, "middle", 13, 700);

  const railTop = 60, railBot = 300, leftX = 90;

  // Input rails
  sline(s, leftX, railTop, leftX, railBot, SCH.hot, 2);
  stext(s, leftX - 8, railTop - 8, "+100 V", SCH.hot, "end", 11, 700);
  stext(s, leftX - 8, railBot + 16, "0 V", SCH.hot, "end", 11, 700);
  scap(s, leftX, (railTop + railBot) / 2, "C_in", SCH.hot, false,
    ["Input capacitor",
     "Holds this cell's share of the bus steady. Its tolerance is one of the " +
     "things that decides whether the eight cells divide the 800 V evenly."]);

  // Half bridge
  const brX = 230;
  sline(s, leftX, railTop, brX, railTop, SCH.hot);
  const hi = smosfet(s, brX, railTop + 40, "Q1", SCH.hot,
    ["Q1, high-side GaN (EPC2305)",
     "Rated 150 V. Its source terminal swings the full 100 V every cycle, so " +
     "its gate driver has to float with it and reject that slew rate."]);
  const lo = smosfet(s, brX, railTop + 150, "Q2", SCH.hot,
    ["Q2, low-side GaN (EPC2305)",
     "The charge stored in these devices' output capacitance is exactly what " +
     "the tank current must drain during the dead time for lossless switching."]);
  sline(s, brX + 10, railTop, brX + 10, railTop + 20, SCH.hot);
  sline(s, brX + 10, railTop + 60, brX + 10, railTop + 130, SCH.hot);
  sline(s, brX + 10, railTop + 170, brX + 10, railBot, SCH.hot);
  sline(s, leftX, railBot, brX + 10, railBot, SCH.hot);

  const swNode = [brX + 10, railTop + 95];
  sdot(s, swNode[0], swNode[1], SCH.hot);
  stext(s, swNode[0] - 6, swNode[1] - 8, "switch node", SCH.dim, "end", 9.5);

  // Resonant tank
  const tankY = swNode[1];
  sline(s, swNode[0], tankY, 330, tankY, SCH.hot);
  scap(s, 350, tankY, null, SCH.hot, true,
    ["C_r, resonant capacitor",
     "With the resonant inductance it sets the frequency the converter is " +
     "designed to sit at. Its peak voltage is set by tank current, not by the " +
     "bus, and is easy to underestimate."]);
  stext(s, 350, tankY - 18, "C_r", SCH.hot, "middle", 10.5, 600);
  sline(s, 356, tankY, 390, tankY, SCH.hot);
  sind(s, 410, tankY, "L_r", SCH.hot, true,
    ["L_r, resonant inductance",
     "Drawn as a discrete part for clarity, but in this design it is the " +
     "transformer's own leakage inductance. That is why leakage here is a " +
     "functional element to be tuned, not a parasitic to be minimised."]);
  sline(s, 428, tankY, 470, tankY, SCH.hot);

  // Transformer
  const txX = 500, txTop = tankY - 60, txBot = tankY + 60;
  spath(s, `M ${txX} ${txTop + 20} a 5 5 0 0 0 0 10 a 5 5 0 0 0 0 10 ` +
    `a 5 5 0 0 0 0 10 a 5 5 0 0 0 0 10`, SCH.hot, 1.8);
  sline(s, 470, tankY, txX, txTop + 20, SCH.hot);
  sline(s, txX, txTop + 60, txX, railBot, SCH.hot);
  sline(s, brX + 10, railBot, txX, railBot, SCH.hot);
  stext(s, txX - 14, tankY + 4, "4T", SCH.hot, "end", 10.5, 700);

  // Core
  sline(s, txX + 12, txTop + 8, txX + 12, txBot - 8, SCH.core, 2);
  sline(s, txX + 20, txTop + 8, txX + 20, txBot - 8, SCH.core, 2);
  stext(s, txX + 16, txTop, "ferrite", SCH.core, "middle", 9.5, 600);

  // Centre-tapped secondary
  const secX = txX + 32;
  spath(s, `M ${secX} ${txTop + 18} a 5 5 0 0 1 0 10 a 5 5 0 0 1 0 10`,
    SCH.cold, 1.8);
  spath(s, `M ${secX} ${tankY + 6} a 5 5 0 0 1 0 10 a 5 5 0 0 1 0 10`,
    SCH.cold, 1.8);
  stext(s, secX + 14, txTop + 26, "1T", SCH.cold, "start", 10.5, 700);
  stext(s, secX + 14, tankY + 22, "1T", SCH.cold, "start", 10.5, 700);

  const ctY = tankY + 2;
  sline(s, secX, ctY, secX + 40, ctY, SCH.cold);
  sdot(s, secX, ctY, SCH.cold);
  stext(s, secX + 44, ctY + 4, "centre tap", SCH.dim, "start", 9.5);

  // Synchronous rectifiers
  const srX = 700;
  sline(s, secX, txTop + 18, srX - 26, txTop + 18, SCH.cold);
  smosfet(s, srX, txTop + 38, "SR1", SCH.cold,
    ["SR1, synchronous rectifier (EPC2366)",
     "Two of these in parallel per half. A diode would drop half a volt and " +
     "burn 30 W at 60 A; a sub-milliohm transistor drops a few millivolts."]);
  sline(s, secX, tankY + 26, srX - 26, tankY + 26, SCH.cold);
  smosfet(s, srX, tankY + 46, "SR2", SCH.cold,
    ["SR2, synchronous rectifier (EPC2366)",
     "Conducts on the opposite half cycle. If the two overlap they short the " +
     "secondary, which is why their timing is controller business."]);

  // Output
  const outX = 800;
  sline(s, srX + 10, txTop + 18, outX, txTop + 18, SCH.cold, 2.6);
  sline(s, srX + 10, tankY + 66, outX, tankY + 66, SCH.cold, 2.6);
  sline(s, outX, txTop + 18, outX, tankY + 66, SCH.cold, 2.6);
  sline(s, secX + 40, ctY, secX + 40, railBot, SCH.cold);
  sline(s, secX + 40, railBot, outX + 40, railBot, SCH.cold, 2.6);
  scap(s, outX, (txTop + 18 + railBot) / 2, "C_out", SCH.cold, false,
    ["Output capacitor", "Absorbs the rectified ripple at 60 A per cell."]);
  sline(s, outX, txTop + 18, outX + 40, txTop + 18, SCH.cold, 2.6);
  stext(s, outX + 46, txTop + 22, "12.5 V", SCH.cold, "start", 11.5, 700);
  stext(s, outX + 46, railBot + 4, "return", SCH.dim, "start", 10);

  // Isolation barrier
  const barX = txX + 16;
  s.appendChild(svg("line", { x1: barX, y1: 44, x2: barX, y2: H - 54,
    stroke: SCH.barrier, "stroke-width": 2, "stroke-dasharray": "7 5" }));
  stext(s, barX, 38, "isolation barrier", SCH.barrier, "middle", 10.5, 700);

  stext(s, 210, H - 30, "hazardous side, floats up to 800 V",
    SCH.hot, "middle", 10.5, 600);
  stext(s, 700, H - 30, "low-voltage side, shared with seven other cells",
    SCH.cold, "middle", 10.5, 600);
  stext(s, W / 2, H - 12,
    "V_out = V_cell / (2 × 4) = 12.5 V.  The half bridge applies half the cell voltage; the 4:1:1 ratio does the rest.",
    SCH.dim, "middle", 11);
}

/* ------------------------------------------- 3. Winding order / stackup */

function diagramWinding(host, geometry) {
  const W = 900, H = 330;
  const s = frame(host, W, H);
  stext(s, W / 2, 20, "Layer order, and why it is not simply primary then secondary",
    SCH.ink, "middle", 13, 700);

  const layouts = [
    ["Not interleaved", ["P", "P", "P", "P", "S", "S", "S", "S"], 70,
     "Four primary layers run without a break. The proximity term grows with " +
     "the square of the layer count, so the fourth layer is punished hardest.",
     "high copper loss, low capacitance"],
    ["Interleaved", ["S", "S", "P", "P", "P", "P", "S", "S"], 480,
     "Splitting the secondary either side of the primary resets the magnetic " +
     "field twice, so no portion runs more than a few layers deep.",
     "low copper loss, higher capacitance"]
  ];

  for (const [title, order, x0, why, verdict] of layouts) {
    stext(s, x0 + 170, 46, title, SCH.ink, "middle", 12, 700);
    let y = 60;
    const h = 20;
    for (let i = 0; i < order.length; i++) {
      const isP = order[i] === "P";
      const color = isP ? "#c97b3c" : "#4aa3ff";
      const prev = i > 0 ? order[i - 1] : null;
      if (prev && prev !== order[i]) {
        s.appendChild(svg("rect", { x: x0, y, width: 340, height: 9,
          fill: SCH.barrier, rx: 2 }));
        stext(s, x0 + 170, y + 7.5, "isolation barrier", "#e3d9ff", "middle", 8.5, 700);
        y += 12;
      }
      const r = svg("rect", { x: x0, y, width: 340, height: h, rx: 2, fill: color });
      attachTip(r, isP ? "Primary layer" : "Secondary layer",
        isP ? "Carries about 19 A rms through four series turns."
            : "Carries a share of 60 A. Duplicated across parallel layers so " +
              "no single layer has to take it all.", "");
      s.appendChild(r);
      stext(s, x0 + 170, y + 14, isP ? "primary" : "secondary",
        "#0e1117", "middle", 10.5, 700);
      y += h + 3;
    }
    stext(s, x0 + 170, y + 18, verdict, SCH.dim, "middle", 10.5, 600);
    const words = why.split(" ");
    let line = "", ly = y + 36;
    for (const w of words) {
      if ((line + w).length > 46) { stext(s, x0 + 170, ly, line, SCH.dim, "middle", 10); line = w + " "; ly += 13; }
      else line += w + " ";
    }
    stext(s, x0 + 170, ly, line, SCH.dim, "middle", 10);
  }

  s.appendChild(svg("line", { x1: 440, y1: 56, x2: 440, y2: H - 30,
    stroke: SCH.wire, "stroke-width": 1, "stroke-dasharray": "3 4", opacity: 0.5 }));
}

/* ----------------------------------------------- 4. Isolation domains */

function diagramIsolation(host) {
  const W = 900, H = 340;
  const s = frame(host, W, H);
  stext(s, W / 2, 20,
    "Why the insulation is designed for 845 V and not 100 V",
    SCH.ink, "middle", 13, 700);

  const cells = 8, x0 = 120, boxW = 90, boxH = 26, gap = 6;
  const baseY = 60;

  for (let i = 0; i < cells; i++) {
    const y = baseY + i * (boxH + gap);
    const top = 800 - i * 100, bot = 700 - i * 100;
    const g = svg("g", {}); s.appendChild(g);
    g.appendChild(svg("rect", { x: x0, y, width: boxW, height: boxH, rx: 4,
      fill: "#3a1f1f", stroke: SCH.hot, "stroke-width": 1.2 }));
    stext(s, x0 + boxW / 2, y + 17, `cell ${i + 1} primary`, SCH.hot, "middle", 9.5, 600);
    stext(s, x0 - 8, y + 17, `${top}–${bot} V`, SCH.dim, "end", 9.5);
    attachTip(g, `Cell ${i + 1} primary`,
      `Sits between ${bot} V and ${top} V relative to the shared output.<br><br>` +
      `It switches only 100 V locally, but its insulation to the secondary ` +
      `must hold ${top} V.`, "");

    // Barrier arrow to the common secondary
    const arrowY = y + boxH / 2;
    s.appendChild(svg("line", { x1: x0 + boxW, y1: arrowY, x2: 520, y2: arrowY,
      stroke: SCH.barrier, "stroke-width": 1.4, "stroke-dasharray": "5 4" }));
    stext(s, x0 + boxW + 8, arrowY - 5, `${top} V across the barrier`,
      i === 0 ? "#d29922" : SCH.dim, "start", 9, i === 0 ? 700 : 500);
  }

  const secY = baseY + (cells * (boxH + gap)) / 2 - 40;
  s.appendChild(svg("rect", { x: 540, y: secY, width: 180, height: 80, rx: 6,
    fill: "#12283f", stroke: SCH.cold, "stroke-width": 1.5 }));
  stext(s, 630, secY + 30, "shared 12.5 V output", SCH.cold, "middle", 11.5, 700);
  stext(s, 630, secY + 48, "all eight secondaries", SCH.dim, "middle", 10);
  stext(s, 630, secY + 63, "tied together here", SCH.dim, "middle", 10);

  s.appendChild(svg("line", { x1: 520, y1: 44, x2: 520, y2: H - 46,
    stroke: SCH.barrier, "stroke-width": 2.5 }));
  stext(s, 520, 38, "isolation barrier", SCH.barrier, "middle", 11, 700);

  stext(s, W / 2, H - 24,
    "The top cell's primary floats near the whole bus with respect to the output it shares with the others.",
    "#d29922", "middle", 11, 600);
  stext(s, W / 2, H - 8,
    "Designing that barrier for the 100 V a cell switches locally would understate it roughly eightfold.",
    SCH.dim, "middle", 11);
}

/* ------------------------------------------------ 5. Signal / power map */

function diagramSystem(host) {
  const W = 900, H = 300;
  const s = frame(host, W, H);
  stext(s, W / 2, 20, "Where this part sits in the rack", SCH.ink, "middle", 13, 700);

  const blocks = [
    ["medium voltage AC", "13.8–35 kV", 30, "#2a3342", "the building supply"],
    ["sidecar rectifier", "→ 800 V DC", 190, "#3a2a1f",
     "OCP Diablo 400 defines this. Out of scope here."],
    ["this converter", "800 → 12.5 V", 355, "#1f3a2a",
     "Eight ISOP cells. The transformer inside one cell is what FORGE designs."],
    ["point-of-load", "12.5 → ~1 V", 520, "#2a3342",
     "Regulators at the processor. Out of scope."],
    ["processor", "~1 V, high current", 680, "#2a3342", "the actual load"]
  ];

  const y = 90, h = 74, w = 140;
  blocks.forEach(([title, sub, x, fill, why], i) => {
    const g = svg("g", {}); s.appendChild(g);
    const inScope = title === "this converter";
    g.appendChild(svg("rect", { x, y, width: w, height: h, rx: 8, fill,
      stroke: inScope ? "#3fb950" : SCH.wire,
      "stroke-width": inScope ? 2.2 : 1.2 }));
    stext(s, x + w / 2, y + 30, title, inScope ? "#3fb950" : SCH.ink,
      "middle", 11.5, 700);
    stext(s, x + w / 2, y + 48, sub, SCH.dim, "middle", 10.5);
    attachTip(g, title, why, inScope ? "This is the scope of this project." : "");
    if (i < blocks.length - 1) {
      const ax = x + w;
      sline(s, ax + 2, y + h / 2, ax + 16, y + h / 2, SCH.wire, 2);
      s.appendChild(svg("polygon", {
        points: `${ax + 18},${y + h / 2} ${ax + 11},${y + h / 2 - 4} ${ax + 11},${y + h / 2 + 4}`,
        fill: SCH.wire }));
    }
  });

  stext(s, 425, y + h + 26, "in scope", "#3fb950", "middle", 11, 700);
  stext(s, W / 2, H - 26,
    "Each conversion costs efficiency. This one is a single stage because splitting it again would cost more than it saves.",
    SCH.dim, "middle", 11);
}

const DIAGRAMS = [
  ["System context", "where this part sits between the grid and the processor", diagramSystem],
  ["ISOP architecture", "eight cells, series in, parallel out", diagramIsop],
  ["One cell", "half-bridge LLC with centre-tapped synchronous rectification", diagramCell],
  ["Winding order", "why interleaving is a trade and not a free win", diagramWinding],
  ["Isolation domains", "the number that actually governs the safety barrier", diagramIsolation]
];
