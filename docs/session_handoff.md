# Sonyx 2026 — session handoff

Living handoff for continuing sonyx_2026 work across agents/sessions. Update it as
work progresses (per-die state, open items, first-step check).

## 1. Repos & boundaries
| Repo | Path | Access |
|---|---|---|
| sonyx_2026 (layout) | /Users/philippe/Github/sonyx_2026 | read/write |
| pdk-luqia-ln200 (PDK) | /Users/philippe/Github/pdk-luqia-ln200 | read/write |
| picasso-pdk-dev/picasso | /Users/philippe/Github/picasso-pdk-dev/picasso | read/write (patterns) |
| bare picasso, pdk-lxt-ltpro, buddha | — | read-only |

## 2. Workflow & conventions
- **cwd resets between shell calls** — always `cd /Users/philippe/Github/sonyx_2026` first.
- Build: `uv run python -m sonyx.artifacts` -> `layout_artifacts/sonyx.gds`.
  Add `--blackbox` to also write `sonyx_blackbox.gds` (IP-protected: flagged PDK
  devices become frame+name+port stubs on BLACKBOX 99/0+99/2; routing/pads/topology
  stay real). Sticky: once present it refreshes on every plain run; delete to opt out.
- Keep green: `uv run ruff check src/sonyx` && `uv run ty check src/sonyx` (line length
  100, ASCII). PDK is **not** clean at baseline — only add *no new* ruff/ty errors (type
  new PDK helpers properly; assert `min_spacing is not None`, etc.).
- **Verify numerically** (bbox / ports), never by render. **No PNG/SVG renders.**
- **Placement-only** unless told to route — every test cell so far is placed but unrouted.
- **The user does the overlap check** — just place (build+ruff+ty green) and report
  positions; do **not** run overlap scans.
- **"Do you see a way..." = propose, don't implement** until approved. No unrequested
  follow-on edits.
- **DC test bond pads are always rotated long-side N-S** (200 E-W x 400 N-S); pitch = pad
  width + `parameters.dc_test_pad_spacing`; row centreline = `parameters.dc_test_pad_row_y`.
  TOP_METAL only (heater terminals are already on `routing_top_metal`).
- Multi-die shared content = `@recipe` cells stamped via `add_placed` (avoids
  `ComponentNameCollisionError`); or `put()`-chain sub-cells (every abutment a Net).
- Commit only when asked; branch off main first.

## 3. Per-die state (all placement-only, PLACEHOLDER calibration)
- **R1A** — GSG **termination-resistance sweep** (`gsg_termination_sweep.py`): 7 probeable
  DUTs (25/35/45/50/55/65/75 ohm), single row top-left, each = bondpads -> taper ->
  `gsg_terminator_top_metal_50ohms_parallel`. **Reflectometry cell** (`reflectometry.py`):
  4 GCs (left alignment loop + 2 open) + two 9 mm horizontal waveguides (one open-ended,
  one `beam_dump_rib_sm_800nm`), below the terminators, start shifted +500 um.
- **R2A** — **variable-length racetrack resonator sweep** (`racetrack_sweep.py`): 5 all-pass
  racetracks (`racetrack_allpass_rib_sm_800nm`, gap 700 nm, L_s = 100/250/500/1000/1500 um),
  **rotated 90 deg, vertical stack, left-aligned** (uncoupled Euler bends at x=-4787.5,
  coupling buses staircase right), 150 um vertical gaps + GC array to the right.
- **R3A** — SM + ULL waveguide-loss cutbacks (unchanged).
- **R3B** — **SSM waveguide-loss cutback** (`test_waveguide_cutback_ssm` in
  `test_cells_die_r1a.py`), reverse=True (long spiral at top), top-right (moved from R3A,
  which was too narrow), plus the split-gap GSG via modulator.
- **R4A** — **DC coupling-length sweep** (`dc_length_sweep.py`): single DCs, 2 groups of 4,
  **two tiers** — 50/50 (L 10-190) on top, **5/95 tap** (L centred on 94.38) below.
  **Back-to-back-coupler MZI sweep** (`dc_mzi_length_sweep.py`): zero-arm MZIs (2 DCs each),
  same two-tier layout, right of the single-DC block. 3 ports routed-intent (o1/o3/o4),
  o2 open.
- **R4B** — **heater-length thermo-optic MZI sweep** (`heater_mzi_sweep.py`): 6 balanced
  1x2-MMI MZIs, heater length via ladder `sections` M, two columns + GC arrays + DC pads.
  **Paperclip-TOPS MZI sweep** (`paperclip_mzi_sweep.py`): 3 offset-coupler MZIs, fold count
  num_arms=3/5/7, + GC array + DC pads. Plus the unbalanced-MZI n_eff/n_g ladder.

## 4. Key files
- **Sonyx blocks**: `gsg_termination_sweep, reflectometry, heater_mzi_sweep,
  paperclip_mzi_sweep, dc_length_sweep, dc_mzi_length_sweep, racetrack_sweep`.py; shared
  helpers `dc_length_sweep.place_two_groups/_add_group/group_gc_width`.
- **Sonyx params**: `parameters.py` — `dc_test_pad_spacing`=200, `dc_test_pad_row_y`=1242.
- **PDK cells** (luqia): `waveguides.py` (`straight_rib_ssm_800nm`,
  `spiral_rib_ssm_800nm_for_length`); `resonators.py` (`racetrack_allpass_rib_sm_800nm` —
  Euler-L-bend loop + bend point coupler); `cells/__init__.py` registers the racetrack.

## 5. Physics/design decisions locked
- **Racetrack**: all-pass (thru-only), point coupler in the bend, fixed coupler + swept L_s
  -> slope = propagation loss, intercept = bend + coupler loss; length sweep self-
  disambiguates the coupling regime (critical at L_s~500). Bends are PDK Euler
  `lbend_rib_sm_800nm`.
- **Heater MZI**: P_pi is ~length-independent (thermal efficiency set by the cross-section);
  the length sweep maps the short-heater P_pi knee, tau, and V_pi ~ sqrt(L).
- **Paperclip**: fold-count sweep (num_arms) at fixed heater probes folding efficiency;
  N=1 baseline = the straight heater block.

## 6. Open items / pending
- **Nothing is routed** — all test cells placement-only. Routing TODO per cell (heater->pads,
  MZI/DC/racetrack ports->GCs, reflectometry couplers->waveguides). Racetrack buses were
  deliberately staircased for crossing-free fan-out.
- **Racetrack coupler caveat**: the kappa^2 sim (gap 700 nm -> 0.0333) used L_rt = 2*pi*R with
  R=75, but the built loop uses the PDK lbend (footprint R~50) -> real round-trip length /
  FSR differ; confirm the kappa^2 sim used the actual lbend apex geometry.
- **Calibration**: HEATER sheet resistance (39 ohm/sq) is a suspected-high placeholder ->
  terminators + heaters uncalibrated. All new cells `calibration_status = "PLACEHOLDER"`.
- Broad 8-die overlap sweep not done (user checks per-cell).

## 7. First step in a new chat
```bash
cd /Users/philippe/Github/sonyx_2026 && uv run python -m sonyx.artifacts \
  && uv run ruff check src/sonyx && uv run ty check src/sonyx
```
Confirm green (0 ruff errors, ty passes), then continue.
