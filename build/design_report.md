# Planar transformer for an 800 VDC to 12.5 V rack converter

**Simulation-backed preliminary design. Not production-qualified. Hazardous high voltage. Independent safety and regulatory review is required before any hardware is built.**

Generated 2026-07-28 23:24 UTC. Requirements lock `b2a12fe4c5867d6c`, benchmark protocol `3c234bdece3a8552`.

## Where this stands

Release level: **research_report**.

Not releasable as a candidate package because safety-critical gate(s) open: faults, insulation, common_mode, thermal.

No hardware exists. Every number below is a model output, and the loss, temperature and inductance figures in particular are unconfirmed until something is built and measured against the criteria in `hardware/acceptance.lock.yaml`.

## The design

| Parameter | Value | Basis |
|---|---|---|
| Core | ELP18/4/10withI18/2/10 | selected by screening |
| Material | 3F46 | sourced datasheet |
| Switching frequency | 2.00 MHz | selected |
| Primary turns | 4 | selected |
| Secondary turns per half | 1 | derived from 4:1 ratio |
| Parallel secondary layers | 4 | selected |
| Copper weight | 3 oz (104 um) | selected |
| Interleaved | no | selected |
| Layers used | 12 of 14 | derived |
| Board thickness | 2.65 mm | derived |

### Resonant tank

| Quantity | Value | How it was obtained |
|---|---|---|
| Magnetising inductance | 0.405 uH | set to a fraction of the ZVS charge limit |
| Resonant inductance | 0.0675 uH | from the chosen Lm/Lr ratio; in practice this is transformer leakage |
| Resonant capacitance | 93.85 nF | places resonance at the switching frequency |
| Resonant frequency | 2.000 MHz | derived |
| Capacitor peak voltage | 20 V | from tank current, not from the bus |

## Loss and temperature

| Mechanism | Watts | Share | Confidence |
|---|---|---|---|
| Core | 0.25 | 1% | iGSE over the real triangular waveform, inside the fitted domain |
| Primary copper | 17.59 | 80% | 1D Dowell; the field solver has not corrected it |
| Secondary copper | 3.58 | 16% | 1D Dowell, divided across parallel layers |
| Vias | 0.46 | 2% | barrel resistance only; current crowding not modelled |
| **Total** | **21.88** | 100% | transformer only, 97.17% efficient at 750 W |

Skin depth at this frequency is 56 um against 104 um of copper. Loss is minimised near one skin depth, so copper weight is a real optimum rather than a case of thicker being better.

Worst-case temperature across the swept cooling boundary is 261 C in the winding and 177 C in the core. The airflow and thermal path behind those numbers are assumptions, not specifications, which is why the result is a sweep.

## Insulation and common mode

The consequence of stacking cells in series is easy to understate. Each cell switches only about 100 V locally, but the top cell's primary floats near the entire bus with respect to the shared secondary. The barrier is therefore designed against **844.6 V**, roughly eight times the local figure.

Interwinding capacitance is 20.9 pF static, driving 93 mA rms of common-mode current at 1.0 A peak during each edge. Interleaving lowers copper loss and raises this capacitance, so the two cannot be optimised separately.

## Gates

| Gate | State |  | Detail |
|---|---|---|---|
| Requirements and provenance complete | pass |  | locked at b2a12fe4c5867d6c |
| Analytic energy and loss consistency | pass |  | components sum to 21.8767 W against a reported 21.8767 W |
| Core flux inside the material's fitted domain | pass |  | 2.00 MHz at 40 mT |
| Windings fit the core window | pass |  | no clashes |
| Board passes design rule checks | **unverified** |  | run 'forge geometry' to generate and check a board for this design; the shipped board was checked for the base |
| Mesh-converged 2D field results | **unverified** |  | inductances are analytic; the 2D field study has not been run for this geometry, so leakage and AC resistance  |
| Zero-voltage switching predicted at nominal and corners | pass |  | 309 nC available |
| Cell sharing under component mismatch | pass | safety | cell voltages 89.2 to 109.0 V, spread 19.8% about the mean; worst is cell 1 |
| Fault cases within device derating | **fail** | safety | all cells healthy: 100 V; one cell stops drawing power: 114 V; two cells stop drawing power: 133 V; one cell i |
| Insulation coordination reviewed | **unverified** | safety | creepage, clearance, hipot and partial discharge are conservative placeholders; the governing tables are in li |
| Interwinding capacitance and common-mode current | **fail** | safety | 93 mA rms; capacitance is estimated from facing areas, not solved |
| Temperature within limits across the cooling sweep | **fail** | safety | winding 261 C, core 177 C |
| Component derating and availability | pass |  | prices and stock harvested; EPC2366 stock covers roughly 131 builds |
| Uncertainty budget and benchmark protocol recorded | pass |  | benchmark protocol 3c234bdece3a8552 committed |
| No restricted source material in published output | pass | safety | retrieved documents stay in a gitignored cache; only citations and derived values are published |

An unverified gate blocks release exactly as a failing one does. Not having checked something is a different claim from having checked it and found it acceptable.

## Circuit verification

- cell voltages 89.2 to 109.0 V, spread 19.8% about the mean; worst is cell 1
- all cells healthy: 100 V per surviving cell (within derating)
- one cell stops drawing power: 114 V per surviving cell (within derating)
- two cells stop drawing power: 133 V per surviving cell (OVER derating)
- one cell input shorted: 114 V per surviving cell (within derating)

## Cost

A 6 kW converter comes to **$290.75**, or $48.46 per kW, at 1000 units. 2 of 8 lines are real vendor quotes, covering 54% of component cost. The remaining 6 are best-effort estimates, not quotes.

| Part | Qty | Unit | Extended | Basis |
|---|---|---|---|---|
| EPC2305 | 16 | $3.562 | $57.00 | quoted |
| EPC2366 | 32 | $1.562 | $50.00 | quoted |
| MIE1W0505BGLVH | 8 | $4.400 | $35.20 | estimated |
| LMG1020 | 16 | $1.056 | $16.90 | estimated |
| ELP18/4/10-3F46 | 16 | $0.968 | $15.49 | estimated |
| MP18831 | 8 | $1.850 | $14.80 | estimated |
| ISO7740 | 2 | $2.300 | $4.60 | estimated |
| DSPIC33CK256MP605 | 1 | $3.600 | $3.60 | estimated |

## What is assumed rather than known

- Cooling: airflow, inlet temperature and thermal path are all assumed and swept, because none is published for this class of converter.
- Insulation spacing: conservative placeholders. The governing IEC tables are licensed and may not be reproduced here.
- Interwinding capacitance: estimated from facing areas, not solved electrostatically.
- Leakage inductance: analytic. The 2D field study omits vias, corners and end effects, and has not been run for this geometry.

## What would have to happen next

1. A licensed reviewer replaces the placeholder insulation spacings.
2. The 2D field study runs on this geometry, and targeted 3D studies cover vias and corners.
3. Prototypes are built and measured against `hardware/acceptance.lock.yaml`, whose criteria were frozen before any hardware existed.
4. Only once every criterion in that file is met does its promotion clause apply. Production qualification is not in scope for this project at all, and passing that protocol would not imply it.

## Sources

| Key | Owner | Revision | Status |
|---|---|---|---|
| epc91123_kit_guide | Efficient Power Conversion Corporation | May 2026 | retrieved |
| epc_800v_white_paper | Efficient Power Conversion Corporation | - | retrieved |
| ferroxcube_3f36 | Ferroxcube International Holding B.V. | 2013 Jun 06 | retrieved |
| ferroxcube_3f46 | Ferroxcube International Holding B.V. | 2016 March 03 | retrieved |
| iec_60664_1 | International Electrotechnical Commission | - | licensed_offline |
| iec_62368_1 | International Electrotechnical Commission | - | licensed_offline |
| magnetics_ferrite_catalog | Magnetics (Spang & Company) | 2022 | retrieved |
| navitas_crps_planar | Navitas Semiconductor | - | retrieved |
| ocp_diablo_400_v052 | Open Compute Project Foundation | 0.5.2 (30 May 2025) | blocked |
| ocp_diablo_400_v070 | Open Compute Project Foundation | 0.7.0 (1 March 2026) | blocked |
| proterial_ml95s | Proterial, Ltd. | - | unavailable |
| tdk_elp_18_4_10 | TDK Electronics AG | - | retrieved |
| tdk_elp_22_6_16 | TDK Electronics AG | - | retrieved |
| tdk_elp_32_6_20 | TDK Electronics AG | - | retrieved |
| tdk_elp_38_8_25 | TDK Electronics AG | - | retrieved |
| tdk_elp_43_10_28 | TDK Electronics AG | - | retrieved |
| tdk_elp_58_11_38 | TDK Electronics AG | - | retrieved |
| tdk_ferrite_catalog | TDK Electronics AG | - | blocked |
| ti_ssztd94 | Texas Instruments Incorporated | - | retrieved |

Retrieved documents are held in a local cache that is excluded from version control. Most are all-rights-reserved, and getting past an HTTP 403 is not a redistribution right, so only citations and derived values appear here.
