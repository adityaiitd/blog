# FORGE

A design tool for the planar transformer inside an 800 VDC to 12.5 V AI rack
converter, built so that every number is traceable to either a cited source or
an explicit assumption.

**Everything it produces is a simulation-backed preliminary design.** It is not
production-qualified, no hardware exists, and the voltages involved are
hazardous. Independent safety and regulatory review is required before anything
is built.

---

## Getting to the app

### 1. Standalone file, no setup

Download **`build/forge-explorer.html`** from this branch and open it in any
browser. It is one self-contained 7 MB file with 864 precomputed design points
embedded. Sliders snap to the nearest computed point rather than moving
continuously; everything else works, including all four modes.

### 2. Run it locally, with live physics

```bash
git clone <this repo> && cd <repo>
git checkout cursor/forge-planar-transformer-design-agent-ca34

python3 -m venv .venv && source .venv/bin/activate
pip install numpy scipy matplotlib pymupdf pyyaml websocket-client

python -m forge ui --open      # http://127.0.0.1:8765
```

Now every slider move re-runs the actual Python models. Only the browser-driven
sourcing harvest needs Chrome; the explorer itself does not.

### 3. Run the whole pipeline

```bash
python -m forge all
```

Seven stages, about eight seconds: toolchain check, evidence register, catalog
build, requirement validation, design screening, board generation with KiCad
verification, and the cost model.

---

## The four modes

| Mode | What it is for |
|---|---|
| **Learn** | Scope, then ten steps from "a rack needs a megawatt" to "the windings are etched into a circuit board". Each gives the mechanical picture, the electrical reality, and where the analogy breaks. Nine have live controls. |
| **Explore** | Sixteen sliders driving the real models. Cross-section, copper layout, loss split, waveforms, gain curve, thermal map, ZVS charge balance. |
| **Parts** | Every component: what it is, what it does, why this one rather than something cheaper, what happens if it is wrong. |
| **Sourcing** | Cost stack from live vendor prices where obtainable, labelled estimates where not, plus supply and design risk. |

---

## Commands

```
python -m forge doctor         check the toolchain and record capabilities
python -m forge evidence       register sources, open manual gates
python -m forge catalog        build the material and component catalog
python -m forge requirements   validate and freeze the requirement lock
python -m forge screen         enumerate and filter the design space
python -m forge geometry       emit a KiCad board and verify it with KiCad
python -m forge field          run the 2D field study (slow)
python -m forge sourcing       harvest live prices and build the cost model
python -m forge ui             serve the interactive explorer
python -m forge export         write the standalone HTML
python -m forge all            everything except field and ui
```

---

## What it currently says

Screening 3,456 candidate geometries leaves 8 feasible. The best runs at 2 MHz
on an ELP18 core in Ferroxcube 3F46, with a four-turn primary and a single-turn
secondary duplicated across four parallel layers.

| | |
|---|---|
| Transformer loss | 9.2 W of 750 W |
| Peak flux | 39.6 mT, inside the material's measured range |
| Board | 12 layers, 2.95 mm, DRC clean, Gerbers and drill file generated |
| Converter cost | $290.75 for 6 kW, $48.46/kW at 1k volume |
| Cost on real quotes | 54% |

The design is squeezed from both sides in frequency: below 2 MHz the flux
leaves the range the datasheet actually measured, and above it common-mode
current exceeds budget.

---

## Design rules this codebase follows

**A missing number stays missing.** No value is invented to complete a model.
The cost model reports what fraction rests on real quotes; unquotable lines
carry labelled estimates with a stated confidence, and the two never merge.

**Extrapolation is refused by default.** A material loss fit knows the
frequency, flux and temperature range it was fitted over and raises rather than
guessing outside it.

**Sources carry their licence.** Getting past an HTTP 403 is not a
redistribution right. Retrieved documents live in a gitignored cache; the
repository keeps citations, hashes and derived values.

**Analogies declare where they break.** Every mechanical framing in Learn mode
is paired with the point at which it stops being true.

**Predicted is not confirmed.** ZVS is reported as predicted under modelled
conditions. The report generator refuses the word "validated" without hardware
results against a precommitted protocol.

---

## Layout

```
forge/
  evidence/     sources, licences, extraction provenance
  browser/      headful Chrome over CDP, manual gates
  requirements/ Diablo rack interface and converter brief, kept separate
  data/         catalog, evidence register, harvested quotes
  physics/      LLC tank, core loss, windings, capacitance, thermal
  solve/        screening and full design-point evaluation
  geometry/     canonical model, KiCad writer, FEMM writer, 3D export
  verify/       KiCad verification, FEMM runner
  sourcing/     price harvest and cost model
  ui/           server, static app, standalone export
  tests/        158 tests
```

## Known gaps

- The 2D field study is slow at fine mesh and is not yet wired into the
  reported figures; inductances shown are analytic.
- Circuit verification in ngspice, the benchmark protocol, candidate
  down-select, the written report and the hardware gate are specified but not
  yet implemented.
- Creepage and clearance are conservative placeholders pending review against
  licensed IEC tables.
- Six of eight BOM lines are estimates, because the vendors block automation.
