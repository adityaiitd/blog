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

### Option 1: one file, nothing to install

Download **`build/forge-explorer.html`** from this branch and open it in any
browser. One self-contained 7 MB file with 864 precomputed design points
embedded. Sliders snap to the nearest computed point rather than moving
continuously; everything else works, including all four modes.

### Option 2: run it, with live physics

```bash
# 1. Get the code and switch to the branch
git clone <this repo>
cd <repo>
git checkout cursor/forge-planar-transformer-design-agent-ca34

# 2. Confirm you are in the right directory.
#    You must see a folder called "forge" listed.
ls forge

# 3. Create an isolated environment
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 4. Install the project and its dependencies
pip install -e .

# 5. Run it
forge ui --open                      # http://127.0.0.1:8765
```

Every slider move now re-runs the actual Python models. Only the price harvest
needs Chrome; the explorer itself does not.

### If you see `No module named forge`

Python is looking in the wrong place. Almost always one of three things:

**You are not in the repository root.** `python -m forge` only works from the
directory that *contains* the `forge` folder. Run `ls forge` first: if that
errors, `cd` to the repository root and try again.

**You have not installed it.** After `pip install -e .` the location stops
mattering and both `forge` and `python -m forge` work from anywhere. This is
the more robust route.

**You installed into a different interpreter than you are running.** On macOS
with Homebrew Python this is common. Check they agree:

```bash
which python3 && which pip3
python3 -c "import forge; print(forge.__file__)"
```

If the last command fails, install into that exact interpreter:

```bash
python3 -m pip install -e .
```

On recent macOS and Linux, a system Python may refuse with *externally managed
environment*. Use the virtual environment in step 3 rather than
`--break-system-packages`.

### Option 3: run the whole pipeline

```bash
forge all
```

Seven stages, about eight seconds: toolchain check, evidence register, catalog
build, requirement validation, design screening, board generation with KiCad
verification, and the cost model.

Only `forge ui`, `forge export` and `forge all` are needed to see everything.
`forge doctor` reports which optional tools you have; KiCad, Wine and FEMM are
only required for board verification and field studies, and the tool degrades
explicitly rather than silently when they are absent.

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
