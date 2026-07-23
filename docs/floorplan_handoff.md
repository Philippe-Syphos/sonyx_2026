# Sonyx floorplan — handoff

Continue work on the **sonyx_2026** photonic reticle layout (2×4 die grid) using the
**luqia_ln200** PDK + **picasso** framework. This session was floorplanning the 8
dies' test/active content; below is the exact current state.

## 1. Repos & boundaries (read/write = editable; never edit read-only)

| Repo | Path | Access |
|---|---|---|
| `sonyx_2026` | `/Users/philippe/Github/sonyx_2026` | **read/write** (the layout) |
| `pdk-luqia-ln200` | `/Users/philippe/Github/pdk-luqia-ln200` | **read/write** (the PDK, 800 nm TFLN) |
| `picasso-pdk-dev/picasso` | `/Users/philippe/Github/picasso-pdk-dev/picasso` | **read/write** (framework) |
| bare `picasso`, `pdk-lxt-ltpro-picasso`, `buddha_lxtltpro_202602` | — | **read-only** (patterns only) |

## 2. Workflow & conventions

- **uv-managed**, run from repo root. Build: `uv run python -m sonyx.artifacts` → GDS-only
  into `layout_artifacts/sonyx.gds`.
- **Verify numerically** (bbox / port positions via the built cells), **never** by render.
  No PNG/SVG.
- **Keep green on sonyx:** `uv run ruff check src/sonyx` and `uv run ty check src/sonyx`.
  Line length 100, ASCII in code.
  - **ty gotcha:** `Component.bbox` is ty-clean, but `Instance.bbox` types as `BBox | None`
    (errors). Anchor placements to **ports** (`inst.ports.xN.position`) or to a
    `Component.bbox` computed before placing — not `Instance.bbox`.
  - The PDK repo is **not** ruff/ty-clean at baseline (pre-existing unicode / line-length /
    object-typing); only add no *new* errors there.
  - **Known pre-existing** `die_r1a.py` ruff errors (F401 unused `test_waveguide_cutback_*`
    imports, F841 `half_w`) come from a commented-out cutback block — leave them; they clear
    when that block is re-enabled.
- **Uncommitted** — commit only when asked; branch off `main` first.

## 3. Architecture

- `blocks/dies/_frame.py::die_scaffold(name, die_params, bondpad_rotation=90.0, num_bondpads=None)`
  — shared per-die scaffold: DIE boundary, KEEPOUT ring, ID label, circuit edge-coupler array
  (lower-left) + leftmost-pair loopback + one **extra outboard edge coupler**, TOP_METAL
  **bond-pad array** (lower-right), **one N-S GC alignment loop in each of the 4 corners**, and
  a **500×500 µm thermistance `bonding_pad`** 300 µm left of the array + 100 µm down
  (`_THERMISTANCE_GAP=300`, `_THERMISTANCE_DROP=100`). Returns the live cell.
  - `bondpad_rotation`: 90° = vertical column (default); **R1A/R1B pass 0°** (horizontal row).
  - `num_bondpads`: override; **R3A passes 8**, all others 7.
- `blocks/dies/die_r{1..4}{a,b}.py` — per-die builders: call `die_scaffold`, place modulators
  + RF chain, then per-die content.
- **Shared helpers (new this session):**
  - `blocks/dies/_head_coupler_block.py::add_head_and_couplers(cell, second_input_head=False, extra_input_spacing=0.0)`
    — places `test_modulator_head` (dual-bias, `second_bias_tops=True`) + below it either a DC
    (`test_directional_coupler`) or a second head (`test_modulator_head_2` when
    `second_input_head=True`), plus two output DCs (`test_dc_out_bot/top`) anchored to
    `gsg_modulator_bot/top.e1` (so they track termination/length). Constants: `_HEAD_SHIFT_X/Y`,
    `_HEAD_DC_SPACING`, `_OUT_DC_SHIFT_X=-20/_Y=300`.
  - `blocks/dies/test_cells_die_r1a.py::test_waveguide_cutback_sm/_ull()` — GC cutback (outer
    loopback pair + inner GC array + 4 rotated delay spirals 2→10 cm). **Currently commented
    out in `die_r1a.py`.**

## 4. Current per-die state (verified)

- **R1A** — 4 stacked modulators (bottom pair + top pair, `gsg_modulator_{bot,top}` and
  `..._2`), each with a **wrapped RF launch** (`gsg_launch_electrode_to_pads_top_metal_50ohms`)
  on both ends. Bondpads **horizontal**. Cutback test block **commented out**. Modulator shift
  = 750 µm (row-1 exception).
- **R1B** — 2 modulators + RF pads. Bondpads **horizontal**. Shift 750.
- **R2A** — 2 mods; **output (west) terminated** (`gsg_terminator_top_metal_50ohms_parallel`
  replaces output taper+pads); input keeps pads; **modulator length = global + 455 µm** (the
  freed output length, computed from cell sizes); head+DC+output-DCs combo.
- **R2B, R3B** — 2 mods + RF pads only.
- **R3A** — 2 mods; **two input heads** (`extra_input_spacing=100` → 160 µm apart) + **input
  directional coupler** (`test_input_dc`) centred between the heads, 230 µm left
  (`_INPUT_DC_GAP`); output DCs; **8 bondpads**.
- **R4A, R4B** — 2 mods; standard head+DC input + output DCs combo. R4B is column-B (multimode
  modulator).
- Rows 2–4 modulator shift = **2 mm** (`gsg_modulator_vertical_shift=2000`); **row 1 overrides
  to 750** locally.
- `bondpad_vertical_shift=150`, `bondpad_horizontal_shift=50`, `num_bondpads=7`.

## 5. New PDK cells this session (all in `luqia_ln200`, registered in `cells/__init__.py`)

- `couplers.py`: `gratingcoupler_loopback_rib_sm_800nm_ext/_ord` (behind-routed loopback),
  `gratingcoupler_alignment_rib_sm_800nm_ext` (GC + L-bend U-turn, **127 µm pitch**; the `_ord`
  alignment was removed).
- `rf.py`: `gsg_launch_electrode_to_pads_top_metal_50ohms` (wraps via→taper→pads; one input
  port `e1`; `put()` auto-rotates for either electrode end). Via moat now grows on all 4 edges.
- `waveguides.py`: `spiral_rib_sm_800nm_for_length` and
  `spiral_rib_ull_horizontal_800nm_for_length` (target-total-length spirals).
- `dc.py`: `bondpad_for_test_top/_top_bot/_top_heater` (400×200 µm test bond pads).

## 6. Open items / flags

- **R2A modulator is centre-placed**, so growing it by 455 µm shifts the footprint rather than
  pinning the output edge — revisit if the west extent must match the standard dies.
- **R2A output DCs / R3A input DC not yet routed** to the modulator heads (pitch mismatch →
  needs fan-out routing).
- **R4A/R4B (and likely others): output GSG pads extend ~48 µm past the die's left edge** — the
  manual output RF chain is longer than the die can fit on the west; needs a fix (shorter taper
  or rethink).
- **R1A cutback** is commented out; re-enable when ready (restores the `half_w` / import usage).
- Overlaps generally not chased yet (placeholder floorplan).

**First step in the new chat:** run `uv run python -m sonyx.artifacts` + `uv run ruff/ty check
src/sonyx` to confirm green, then continue floorplanning.
