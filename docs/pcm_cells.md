# Per-Die PCM & Calibration Cells — Layout Instructions

Scope: a compact block of process-control-monitor (PCM) and calibration cells
**replicated on every die**. Devices are low-speed RF **EO (Pockels) modulators**
with **GSG traveling-wave** electrodes, some **DC bond pads**, and heavy optics.
There is **no PN junction** — do not add diode/junction structures here.

Larger characterization structures (cutback spirals, golden reference MZM,
full-length TW electrode line, passive cascades) live once per **reticle**, not here.

## Conventions (apply to all cells)

- **GSG pads**: match the production modulator GSG pitch and pad size exactly, so
  one RF probe setup measures both PCM and product devices.
- **DC bond pads**: match the production DC pad size/pitch.
- **Optical I/O**: use the same grating/edge coupler and fiber-array pitch/angle
  convention as the product circuits, so one optical probe setup serves both.
- **Labels**: add a small text ID next to every cell (structure name + target value
  where applicable) for probe-station identification.
- Group the cells into one contiguous, reusable block that stamps into each die.

## Cells

### 1. Open GSG pads
- GSG pad set with **no connection** between signal and grounds (open termination).
- Purpose: RF de-embed reference — parasitic pad/ground capacitance.
- Same pad geometry as the production TW electrode landing.

### 2. Shorted GSG pads (target resistance)
- GSG pad set with signal shorted to ground through a **defined target resistance**.
- Purpose: RF de-embed (series R/L) and metal/short-path resistance monitor.
- Annotate the target resistance value in the label.

### 3. Open DC bond pads
- A pair of DC bond pads, **not connected** to each other.
- Purpose: DC de-embed / leakage reference.

### 4. Shorted DC bond pads (target resistance)
- A pair of DC bond pads joined by a **defined target resistance**.
- Purpose: DC resistance monitor; annotate target value in the label.

### 5. Heater resistor across DC bond pads
- A pair of DC bond pads connected by a **heater resistor** (same heater layer/type
  used for thermal phase shifters in production).
- Purpose: measure resistance and resistance-vs-power (thermal behavior).
- Annotate nominal resistance in the label.

### 6. Ring resonator (loss + n_g)
- One ring resonator with bus waveguide and optical I/O couplers.
- Purpose: propagation-loss estimate (from Q) and **group index n_g** (from FSR).
- Use the production waveguide type; document radius and coupling gap in the label.

### 7. Coupler loopback reference
- Back-to-back coupler loop (GC-to-GC or EC-to-EC) with a short defined-length
  waveguide between them.
- Purpose: **fiber-to-fiber reference** to de-embed coupler insertion loss; sets the
  baseline for every absolute optical measurement on the die. Treat as mandatory.

## Notes

- Keep the whole block small — it repeats on every die. Do not pull in reticle-level
  structures.
- If a per-die EO process-health monitor is wanted later, the EO-appropriate addition
  is a small **electrode capacitor / leakage-breakdown** cell (C, leakage, breakdown,
  DC-drift canary) — not a diode.
