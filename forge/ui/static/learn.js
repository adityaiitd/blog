/* Learn mode: the first-principles chain.
 *
 * Written for an engineer who is competent but not an electrical specialist.
 * Each step introduces exactly one idea, gives the mechanical framing and the
 * electrical reality side by side, and says plainly where the analogy stops
 * being true. An analogy you cannot see the edge of is a trap.
 */

const SCOPE = {
  problem: {
    title: "The problem being solved",
    body: `A modern AI rack draws somewhere between 100 kW and, in the designs
      being built for 2027, a megawatt. That power arrives from the building at
      medium-voltage AC and has to end up at roughly one volt inside a
      processor. Every conversion between those two points costs efficiency,
      space and money.<br><br>
      This project designs one specific link in that chain: the
      <strong>transformer inside the converter that steps 800 volts DC down to
      12.5 volts</strong>, right next to the compute. It is a component about
      the size of a large postage stamp that has to move 750 watts
      continuously, inside a module 8 mm tall, and lose almost nothing doing
      it.`
  },
  why_now: {
    title: "Why this is live right now",
    body: `Racks have historically distributed power internally at 48 or 54
      volts. That is running out of road: at a megawatt, 54 V means roughly
      18,500 amps, and the copper needed to carry it stops fitting in the rack.
      The industry response is to distribute at 800 V instead.<br><br>
      Two specifications drive this. NVIDIA's 800 VDC architecture targets its
      Kyber rack generation from 2027. The Open Compute Project's
      <strong>Diablo 400</strong> specification, authored by Google, Meta and
      Microsoft, defines the rack side of it. Neither of them specifies the
      converter this project designs — they define the bus it plugs into.`
  },
  in_scope: {
    title: "In scope",
    items: [
      "The planar transformer for one 750 W cell: core, turns, layer stackup, materials.",
      "The resonant tank around it, since the transformer's own leakage inductance is a functional part of that circuit rather than a parasitic.",
      "Loss, temperature, insulation and interwinding capacitance, each with an uncertainty rather than a single number.",
      "Manufacturable output: a real KiCad board that passes design rule checks, with Gerbers and a drill file.",
      "A bill of materials with real vendor prices where a vendor will publish one, and labelled estimates where none will."
    ]
  },
  out_of_scope: {
    title: "Out of scope",
    items: [
      "The upstream rectifier that makes 800 VDC from medium-voltage AC. That is the sidecar's job and Diablo's subject.",
      "The downstream regulators that take 12.5 V to core voltage at the processor.",
      "Control firmware, telemetry and the rack management interface.",
      "Mechanical enclosure, connectors and cold-plate design beyond a thermal boundary condition.",
      "Regulatory certification. The insulation work here is a design basis, not a compliance submission."
    ]
  },
  solved: {
    title: "What is settled",
    items: [
      ["The architecture", "Eight cells in series on the input and parallel on the output is the industry's answer, and for a good reason: it lets each cell use cheap, fast 150 V transistors instead of expensive 650 V ones."],
      ["The turns ratio", "A half bridge applying half the cell voltage, with a 4:1:1 centre-tapped secondary, lands exactly on 12.5 V from 100 V. That arithmetic is not in dispute."],
      ["Why planar", "Etched PCB windings are repeatable to a manufacturing tolerance rather than a winder's skill, and they are the only way to fit inside 8 mm."],
      ["The dominant loss", "At these frequencies copper loss, not core loss, is the problem. In the current design the core accounts for around 2% of the total."]
    ]
  },
  unsolved: {
    title: "What is genuinely open",
    items: [
      ["Cooling", "Nobody has published an airflow or thermal path for this class of converter. It is the difference between a comfortable design and an impossible one, and right now it is an assumption swept over a range."],
      ["Insulation spacing", "The governing creepage and clearance tables live in licensed IEC standards. The working voltage is computed correctly at 845 V, but the spacings themselves are conservative placeholders awaiting a licensed reviewer."],
      ["Whether the cells actually share", "Series-input stacks are claimed to balance naturally. Series inputs enforce a common current and parallel outputs a common voltage, but neither directly forces equal input voltages. This needs a mismatch study, not a claim."],
      ["Interwinding capacitance", "Estimated from facing areas. A real answer needs an electrostatic field solve, and the number drives both noise and safety."],
      ["Everything about hardware", "No prototype exists. Every figure in this tool is a model output. Loss, temperature and inductance predictions are unvalidated until something is built and measured."]
    ]
  }
};

/* ------------------------------------------------------------------ steps */

const STEPS = [
  {
    id: "power",
    title: "Power is pressure times flow",
    lead: `Electrical power is voltage multiplied by current. That is not an
      analogy, it is the same shape of relationship as hydraulic power being
      pressure multiplied by flow rate. To move a fixed amount of power you can
      choose a lot of pressure and a little flow, or a little pressure and a
      lot of flow.`,
    mech: `A hydraulic system moving 750 W can do it at high pressure through a
      narrow line, or low pressure through a fat one. The fat low-pressure line
      wastes more energy to friction, and friction loss climbs with the
      <em>square</em> of flow rate.`,
    elec: `Identical structure. Resistive loss is I²R: double the current and
      you quadruple the loss in the same conductor. This single fact is why the
      whole industry is moving to higher distribution voltage.`,
    breaks: `The analogy holds unusually well here. It starts to fail only when
      you get to inductance and capacitance, which have no everyday hydraulic
      equivalent that most people carry around.`,
    control: { key: "bus_v", label: "Distribution voltage", min: 12, max: 800,
               step: 4, value: 48, unit: "V" },
    compute: (v) => {
      const P = 1e6, L = 20, rho = 1.72e-8, A = 500e-6;
      const I = P / v.bus_v;
      const R = rho * L / A;
      const loss = I * I * R;
      return {
        current: I, loss, lossPct: (loss / P) * 100,
        copperForOnePct: (I * I * rho * L) / (0.01 * P) * 1e6
      };
    },
    readout: (r) => ([
      ["Current for 1 MW", `${(r.current / 1000).toFixed(1)} kA`],
      ["Loss in 20 m of busbar", `${(r.loss / 1000).toFixed(1)} kW`],
      ["That is", `${r.lossPct.toFixed(1)}% of the power, as heat`],
      ["Copper to hold 1% loss", `${r.copperForOnePct.toFixed(0)} mm² cross-section`]
    ]),
    punch: (r) => r.lossPct > 5
      ? `At this voltage you are throwing away ${r.lossPct.toFixed(0)}% of a
         megawatt in the busbar alone. Drag the slider up.`
      : `This is why 800 V. The same power moves with
         ${(r.current / 1000).toFixed(1)} kA instead of tens of kiloamps, and
         the loss falls with the square of that.`
  },
  {
    id: "stepdown",
    title: "But the chips need twelve volts, then one",
    lead: `Distributing at 800 V solves the copper problem and creates a new
      one: nothing in a computer runs at 800 V. Something has to step it down,
      and it has to do that physically close to the load, otherwise you are
      back to carrying huge currents a long way.`,
    mech: `A pressure-reducing station. High pressure in the main line, stepped
      down close to the point of use so the low-pressure run is short.`,
    elec: `A DC-DC converter. The catch is that transformers, the efficient way
      to change voltage, only respond to <em>changing</em> current. They do
      nothing at all with steady DC.`,
    breaks: `A hydraulic reducer can work on steady flow. A transformer cannot
      work on steady current — this is where the mechanical picture stops being
      a guide and you have to accept the electrical reality.`,
    diagram: "chain"
  },
  {
    id: "chop",
    title: "So you chop it into AC, transform, and rectify back",
    lead: `The converter takes DC in, chops it into a high-frequency square
      wave with transistors, feeds that to a transformer which changes the
      voltage, then rectifies the result back to DC. Three stages, and each one
      costs something.`,
    mech: `Closest mechanical parallel is a reciprocating pump driving a
      gearbox driving a rectifying valve arrangement. Motion is converted to
      oscillation, geared, then converted back to one-way flow.`,
    elec: `Transistors switch at between 500 kHz and 3 MHz. Higher frequency
      means the transformer can be smaller, because the core only needs to
      store energy for half a switching period.`,
    breaks: `The pump analogy suggests the chopping is wasteful in itself. It
      need not be — the whole point of resonant conversion, a few steps down,
      is arranging for the switching to cost almost nothing.`,
    diagram: "chain"
  },
  {
    id: "ratio",
    title: "The transformer is a gearbox",
    lead: `A transformer has two windings sharing a magnetic circuit. The ratio
      of turns sets the ratio of voltages, and inversely the ratio of currents.
      Power in equals power out, minus losses.`,
    mech: `A gearbox, almost exactly. Turns ratio is gear ratio, voltage is
      angular speed, current is torque. Gear down for speed and you gain
      torque; step down voltage and you gain current.`,
    elec: `Four primary turns to one secondary turn, in a half bridge that
      applies half the cell voltage, gives 100 V ÷ (2 × 4) = 12.5 V. The
      secondary then carries four times the primary current.`,
    breaks: `A gearbox with no load draws no torque. A transformer with no load
      still draws <em>magnetising current</em> — the current needed to set up
      the magnetic field at all. That current is not delivering power, and
      later it turns out to be the thing that makes efficient switching
      possible. There is no gearbox equivalent.`,
    control: { key: "turns", label: "Primary turns per secondary turn",
               min: 1, max: 12, step: 1, value: 4, unit: ":1" },
    compute: (v) => ({
      vout: 100 / (2 * v.turns),
      iout: 750 / (100 / (2 * v.turns)),
      ipri: 750 / 100
    }),
    readout: (r) => ([
      ["Output voltage", `${r.vout.toFixed(2)} V`],
      ["Output current for 750 W", `${r.iout.toFixed(0)} A`],
      ["Primary current", `${r.ipri.toFixed(1)} A`]
    ]),
    punch: (r) => Math.abs(r.vout - 12.5) < 0.3
      ? `This is the design point. 4:1 lands on 12.5 V, and the secondary
         carries 60 A — which is why that winding gets duplicated across
         several board layers.`
      : `${r.vout.toFixed(1)} V out. The load needs 12.5 V, so the ratio is not
         a free choice.`
  },
  {
    id: "isop",
    title: "Why eight small converters instead of one big one",
    lead: `Going from 800 V to 12.5 V in one step is a 64:1 ratio. That
      demands transistors rated well above 800 V, and those are slow and
      expensive. Instead the converter is split into eight identical cells with
      their inputs wired in series and their outputs in parallel.`,
    mech: `Eight pressure-reduction stages in series, each taking one eighth of
      the total drop, with their outputs manifolded together. No single stage
      sees the full pressure.`,
    elec: `Each cell sees 800 ÷ 8 = 100 V and can use 150 V GaN transistors,
      which are roughly an order of magnitude better on the figure of merit that
      matters. The transformer ratio drops from an awkward 16:1:1 to a
      comfortable 4:1:1.`,
    breaks: `Here the analogy actively misleads. Hydraulic stages in series are
      independent. These are not: the cells must <em>share</em> the bus
      voltage, and nothing physically forces them to. If one cell takes more
      than its eighth, its transistors see overvoltage. Whether they share is
      an open question in this design, not a settled one.`,
    control: { key: "cells", label: "Number of series cells", min: 1, max: 16,
               step: 1, value: 8, unit: " cells" },
    compute: (v) => ({
      vcell: 800 / v.cells,
      pcell: 6000 / v.cells,
      device: 800 / v.cells < 100 ? 100 : (800 / v.cells < 150 ? 150 :
              (800 / v.cells < 250 ? 250 : (800 / v.cells < 650 ? 650 : 1200))),
      ratio: (800 / v.cells) / 12.5 / 2
    }),
    readout: (r) => ([
      ["Volts per cell", `${r.vcell.toFixed(0)} V`],
      ["Watts per cell", `${r.pcell.toFixed(0)} W`],
      ["Transistor rating needed", `${r.device} V class`],
      ["Transformer ratio", `${r.ratio.toFixed(1)}:1:1`]
    ]),
    punch: (r) => r.device <= 150
      ? `At ${r.vcell.toFixed(0)} V per cell you can use ${r.device} V GaN —
         cheap, fast, low charge. This is the whole reason for the
         architecture.`
      : `${r.vcell.toFixed(0)} V per cell forces ${r.device} V devices, which
         are slower and carry far more output charge. Efficiency suffers
         immediately.`
  },
  {
    id: "flux",
    title: "The core has a torque limit",
    lead: `The magnetic core carries flux between the windings. Push too much
      through it and it saturates: the material stops being able to hold more
      field, permeability collapses, and the transformer briefly behaves like a
      short circuit.`,
    mech: `A driveshaft has a torque limit. Below it, it transmits faithfully.
      Above it, it yields — and the failure is sudden rather than gradual.`,
    elec: `Peak flux density depends on volts applied, time applied, turns and
      core area: B = V·t / (N·A). More turns or a bigger core lower it; a
      higher frequency lowers it too, because there is less time per half
      cycle.`,
    breaks: `A yielded shaft is destroyed. A saturated core recovers instantly
      when the field is removed — but the current spike while it is saturated
      can destroy the transistors, so the outcome is often the same.`,
    control: { key: "freq", label: "Switching frequency", min: 0.3, max: 3,
               step: 0.05, value: 2, unit: " MHz" },
    compute: (v) => {
      const N = 4, Ae = 39.5e-6, Vo = 12.5, n = 4;
      const B = (n * Vo) / (4 * v.freq * 1e6 * N * Ae);
      return { B: B * 1000, limit: 301, fitLo: 10, fitHi: 50 };
    },
    readout: (r) => ([
      ["Peak flux density", `${r.B.toFixed(0)} mT`],
      ["Saturation limit, derated", `${r.limit} mT`],
      ["Material characterised over", `${r.fitLo}–${r.fitHi} mT`]
    ]),
    punch: (r) => r.B > r.fitHi
      ? `${r.B.toFixed(0)} mT is nowhere near saturation, but it is outside the
         range the datasheet actually measured. The honest answer is that the
         loss here is unknown, so this tool refuses to quote one.`
      : `${r.B.toFixed(0)} mT sits inside the measured range, so the loss
         figure means something.`
  },
  {
    id: "skin",
    title: "At high frequency, current abandons the middle of the wire",
    lead: `This is the one that surprises people from other disciplines.
      Alternating current does not distribute itself evenly through a
      conductor. The higher the frequency, the more it crowds into the surface,
      leaving the interior carrying almost nothing.`,
    mech: `A boundary layer, inverted. In pipe flow the fast fluid is in the
      middle and the wall drags. Here it is the opposite: the current runs at
      the surface and the middle is dead metal.`,
    elec: `The characteristic depth is δ = √(ρ / π f μ). In copper that is
      about 93 µm at 500 kHz and 66 µm at 1 MHz. Standard 2 oz PCB copper is
      70 µm thick — the same order. Adding thickness beyond roughly one skin
      depth adds weight and cost and carries almost no extra current.`,
    breaks: `There is a second effect with no fluid analogy at all. Current in
      one layer induces opposing current in its neighbours — the
      <em>proximity</em> effect — and in a stack of layers it grows roughly
      with the square of the layer count. It is usually worse than skin effect
      and it is why the layer order matters so much.`,
    control: { key: "f2", label: "Frequency", min: 0.1, max: 5, step: 0.05,
               value: 2, unit: " MHz" },
    compute: (v) => {
      const rho = 1.72e-8 * (1 + 3.93e-3 * (125 - 20)), mu0 = 4e-7 * Math.PI;
      const d = Math.sqrt(rho / (Math.PI * v.f2 * 1e6 * mu0));
      return { skin: d * 1e6, oz1: 34.8, oz2: 69.6, oz3: 104.4 };
    },
    readout: (r) => ([
      ["Skin depth in hot copper", `${r.skin.toFixed(0)} µm`],
      ["1 oz copper is", `${(r.oz1 / r.skin).toFixed(2)} skin depths`],
      ["2 oz copper is", `${(r.oz2 / r.skin).toFixed(2)} skin depths`],
      ["3 oz copper is", `${(r.oz3 / r.skin).toFixed(2)} skin depths`]
    ]),
    punch: (r) => r.oz2 / r.skin > 1.6
      ? `At this frequency even 2 oz copper is mostly dead weight in the
         middle. Thicker copper would make things worse, not better, once
         proximity effect is counted.`
      : `2 oz copper is close to one skin depth here, which is roughly where
         the loss minimum sits.`,
    diagram: "skin"
  },
  {
    id: "zvs",
    title: "Switching costs energy unless you time it right",
    lead: `Every time a transistor turns on with voltage across it, the energy
      stored in its own capacitance is dumped and lost. At two million times a
      second that adds up fast. Resonant conversion exists to make that energy
      zero.`,
    mech: `Slamming a valve shut against full line pressure. Do it once and you
      feel the hammer; do it continuously and you are pumping energy into
      noise and heat. A well-timed valve closes at the instant flow reverses,
      when there is nothing to fight.`,
    elec: `The tank current is arranged to drain the charge off the switch node
      during a brief dead time, so the transistor turns on at zero volts. The
      current available to do that is the magnetising current — the same
      current the gearbox analogy said should not exist.`,
    breaks: `The valve analogy suggests timing alone is enough. It is not: you
      need enough <em>charge</em>, and that depends on the transistors' own
      output capacitance, which is strongly non-linear with voltage. This is a
      charge budget, not just a timing problem.`,
    control: { key: "dead", label: "Dead time", min: 2, max: 60, step: 1,
               value: 20, unit: " ns" },
    compute: (v) => {
      const imag = 15.6, need = 247;
      const have = imag * v.dead;
      return { have, need, margin: (have - need) / need * 100 };
    },
    readout: (r) => ([
      ["Charge needed", `${r.need.toFixed(0)} nC`],
      ["Charge available", `${r.have.toFixed(0)} nC`],
      ["Margin", `${r.margin > 0 ? "+" : ""}${r.margin.toFixed(0)}%`]
    ]),
    punch: (r) => r.margin >= 0
      ? `Enough charge, so switching is predicted to be lossless. Longer dead
         time makes this easier but wastes conversion time.`
      : `Not enough charge. The transistors turn on into a charged node and
         burn that energy two million times a second.`
  },
  {
    id: "heat",
    title: "All of it becomes heat, in a very small space",
    lead: `Every watt lost anywhere in this component turns into heat inside a
      part the size of a postage stamp, in a module 8 mm tall. There is no
      room for a big heatsink, and the core's own surface area is only a couple
      of square centimetres.`,
    mech: `Familiar territory: conduction, convection, a thermal resistance
      network. The unusual part is the power density and the absence of space.`,
    elec: `One extra twist. Copper resistance rises about 40% between room
      temperature and 125 °C, so losses increase as the part heats, which heats
      it further. It has to be solved as a converged loop, not evaluated once.`,
    breaks: `No analogy problem here. The genuine problem is that nobody has
      published the airflow or thermal path for this class of converter, so
      any single temperature would be a guess. The tool sweeps a range
      instead.`,
    control: { key: "rth", label: "Thermal path to ambient", min: 0.5, max: 10,
               step: 0.25, value: 3, unit: " K/W" },
    compute: (v) => {
      const loss = 11.9, ambient = 45;
      const rise = loss * v.rth;
      return { rise, hot: ambient + rise, limit: 125, loss };
    },
    readout: (r) => ([
      ["Loss to remove", `${r.loss.toFixed(1)} W`],
      ["Temperature rise", `${r.rise.toFixed(0)} K`],
      ["Hot spot from 45 °C inlet", `${r.hot.toFixed(0)} °C`],
      ["Limit", `${r.limit} °C`]
    ]),
    punch: (r) => r.hot > r.limit
      ? `Over the limit by ${(r.hot - r.limit).toFixed(0)} K. Air alone over a
         few square centimetres cannot do this — a conduction path is not
         optional.`
      : `Within limits, but note how sensitive this is: the whole feasibility
         of the design rests on a number nobody has specified.`
  },
  {
    id: "planar",
    title: "Why the windings are a circuit board",
    lead: `Instead of winding wire around a bobbin, the turns are etched copper
      inside a multilayer PCB, with the ferrite core clamped through a hole in
      the middle. The board <em>is</em> the transformer.`,
    mech: `The difference between a hand-fitted assembly and a machined one.
      Wire winding is a skill with variability; etched copper is a
      photolithographic tolerance, repeatable to a few microns across
      thousands of units.`,
    elec: `It also makes the parasitics repeatable, which matters more than
      usual here because the leakage inductance is a functional circuit element.
      A hand-wound transformer whose leakage varies 20% part to part would
      detune the resonant tank.`,
    breaks: `The cost is flexibility. Every turn costs a layer, layers cost
      money, and you cannot add half a turn. The design space becomes discrete
      and quite small.`,
    diagram: "stack"
  }
];
