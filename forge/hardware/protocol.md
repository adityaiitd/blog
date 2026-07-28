# Prototype validation protocol

Nothing in FORGE is validated. Every number it produces is a model output.
This document is what would have to happen for that to change, and it is
written before any hardware exists so that the criteria cannot be adjusted to
fit whatever the first prototype does.

**This work involves hazardous voltage.** An eight-cell stack operates with
primaries floating up to 800 V above the output. Only personnel equipped and
trained for high-voltage work should attempt any of it, and an independent
safety review must precede the first stacked-bus energisation.

---

## Order of operations

The sequence matters. Each step is designed to fail cheaply before the next
one can fail expensively.

### 1. Bare transformer, no power

Measure the component before it is asked to do anything.

- Impedance analyser sweep, 10 kHz to 10 MHz, on every winding combination.
- Open-circuit inductance with each secondary open.
- Short-circuit inductance with each secondary shorted in turn, which gives
  the leakage matrix rather than a single scalar.
- AC resistance against frequency at the harmonics that matter.
- Interwinding capacitance, primary to each secondary and to any shield.
- Repeat on at least five units from the same panel, and five from a second
  panel, because layer registration varies between panels and leakage depends
  on it.

### 2. Insulation, before any high voltage

- Review the barrier construction against IEC 62368-1 and IEC 60664-1 with a
  reviewer holding licensed copies. The placeholder spacings in the
  requirements lock are not an acceptance basis.
- Dielectric withstand test at the derived voltage for 60 s.
- Partial discharge screening. Thin solid insulation under repetitive high
  dv/dt can pass a hipot test and still erode in service, so this is not
  optional and a hipot pass does not substitute for it.

### 3. Core loss, separated from copper loss

- Measure core loss on a wound sample under the actual waveform, not a
  sinusoid, using a calorimetric or B-H loop method.
- Do it at the operating frequency and flux, and at three temperatures across
  the intended range, because ferrite loss is not monotonic in temperature.
- This is the only way to separate core from copper loss. Inferring it by
  subtracting a copper estimate from a total is circular.

### 4. One cell, low voltage first

- Bring up at reduced bus voltage through a current-limited supply.
- Double-pulse test to characterise switching before continuous operation.
- Capture the switch node with a differential high-voltage probe of adequate
  bandwidth, and the tank current with a current probe, on the same timebase.
- Confirm the node reaches zero before the next device turns on, at every
  corner of input, load and temperature. Visual near-zero is not sufficient;
  record the residual voltage and the margin.

### 5. One cell, full power

- Efficiency by calibrated input and output power measurement, with
  housekeeping supplied and measured separately.
- Thermal imaging and thermocouples on core, winding, semiconductors and
  board, with airflow rate, inlet temperature and any interface material
  documented.
- If the airflow is not measured, the thermal comparison cannot be scored.

### 6. Eight cells stacked

- Precharge and controlled startup. Observe the voltage division during
  startup, not only in steady state.
- Sharing under load steps and at light load.
- Single-cell fault injection: open, short, lost gate drive, lost synchronous
  rectification. Instrument the surviving cells' input voltage throughout.
- The simulation predicts that losing two cells drives the survivors to 133 V
  against a 120 V derated limit. This must be demonstrated to be protected
  against rather than tolerated.

### 7. Comparison

- Compare only against the criteria frozen in `acceptance.lock.yaml`.
- Hold-out quantities are scored once. Model parameters are not adjusted and
  the comparison re-run.
- A miss is reported as a miss.

---

## What is measured against what

| Quantity | Instrument | Compared against |
|---|---|---|
| Magnetising inductance | Impedance analyser | Field solution and analytic model |
| Leakage matrix | Impedance analyser, short-circuit | Field solution |
| AC resistance vs frequency | Impedance analyser | Harmonic winding model |
| Interwinding capacitance | Impedance analyser | Electrostatic estimate |
| Core loss | Calorimetry or B-H loop | iGSE over the real waveform |
| Switch node at turn-on | Differential probe | Charge-based ZVS prediction |
| Converter efficiency | Calibrated power analyser | Loss budget |
| Hot spot temperature | Thermocouple and imaging | Thermal fixed point |
| Cell voltage sharing | Isolated differential probes | Mismatch simulation |

---

## Instrumentation the results depend on

Every measurement carries its instrument's uncertainty into the comparison. If
these are not recorded, the comparison cannot be scored:

- impedance analyser basic accuracy and fixture compensation method
- current probe bandwidth, and whether it was de-skewed against the voltage
  probe
- differential probe bandwidth and common-mode rejection at the switching
  frequency, since a probe that cannot reject 800 V of common mode will
  produce confident nonsense
- power analyser bandwidth and its accuracy at the actual power factor
- thermocouple placement, which dominates thermal uncertainty in a component
  this small

---

## Promotion

Only when every criterion in `acceptance.lock.yaml` is met, against results
referencing that file's hash, may an artifact use the phrase
**model-validated prototype**.

Even then, *production-qualified* remains out of reach. That requires
independent regulatory certification, reliability qualification and
manufacturing process qualification, none of which is in this project's scope.
