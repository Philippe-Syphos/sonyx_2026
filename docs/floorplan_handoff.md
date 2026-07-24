# Sonyx floorplan — handoff (continue in new chat)

Continue building the **sonyx_2026** photonic reticle (2×4 die grid) using the
**luqia_ln200** PDK (800 nm TFLN) + **picasso** framework.

## 1. Repos & boundaries

| Repo | Path | Access |
|---|---|---|
| `sonyx_2026` | `/Users/philippe/Github/sonyx_2026` | **read/write** (the layout) |
| `pdk-luqia-ln200` | `/Users/philippe/Github/pdk-luqia-ln200` | **read/write** (the PDK) |
| `picasso-pdk-dev/picasso` | `/Users/philippe/Github/picasso-pdk-dev/picasso` | **read/write** (framework) |
| bare `picasso`, `pdk-lxt-ltpro-picasso`, `buddha_lxtltpro_202602` | — | **read-only** (patterns only) |

## 2. Workflow & conventions

- **uv-managed, run from the repo root.** cwd sometimes resets between tool
  calls — always `cd /Users/philippe/Github/sonyx_2026` (or the PDK) at the
  start of a shell command.
- Build: `uv run python -m sonyx.artifacts` → GDS-only into
  `layout_artifacts/sonyx.gds`.
- **Verify numerically** (bbox / port positions / overlap scans on the built
  cells), **never** by render. No PNG/SVG.
- **Keep green on sonyx:** `uv run ruff check src/sonyx` and
  `uv run ty check src/sonyx`. Line length 100, ASCII in code.
  - **ty gotcha:** `Component.bbox` is ty-clean, but `Instance.bbox` types as
    `BBox | None`. Anchor placements to **ports**
    (`inst.ports.xN.position`, ty-clean) or to a `Component.bbox` computed
    before placing — never `Instance.bbox`.
  - **sonyx layer strings:** pass layers to `rectangle()`/leaves as strings
    (`"TOP_METAL.drawing"`, `"WG_RIB.field"`), not `_layers.X` objects (those
    type as `object` and fail ty in sonyx). This is the `_frame.py` convention.
  - The **PDK repo is not ruff/ty-clean at baseline**; only add no *new*
    errors. Baseline `rf.py` = 15 ruff errors; `cells/__init__.py` has 2
    pre-existing E501.
  - **Known pre-existing sonyx ruff** (leave them): 3 in `die_r1a.py` (F401
    `test_waveguide_cutback_sm/_ull`, F841 `half_w`) from a commented-out
    cutback block.
- **Uncommitted** — commit only when asked; branch off `main` first.
- Multi-die shared content: make each cell a `@recipe` (cached, shared across
  dies like PDK cells) and place with a plain helper — a plain wrapper
  `Component` reused per die causes `ComponentNameCollisionError` at reticle
  assembly.

## 3. Current state (this session's work)

**Per-die modulators / electrodes:**

- **R1A** — 3 modulators (bottom pair `gsg_modulator_bot/top` + single top-edge
  `gsg_modulator_top_2`), wrapped RF launch. Modulator vertical shift =
  **1250 µm** (row-1). Has head + input-DC + two output-DCs (via
  `add_head_and_couplers(input_anchor=...)`; R1A uses the wrapped launch so it
  passes the launch east edge). Bondpads horizontal (`bondpad_rotation=0.0`).
  Cutback test block still commented out.
- **R1B** — now **SM** (`DieParameters`, was multimode), bondpads **vertical**
  (default rotation), 3 modulators (added `gsg_modulator_top_2` with a full
  explicit via→taper→pads chain), shift 1250, head + couplers (R4A-style
  default anchor).
- **R2A** — 2 mods, output terminated, modulator length = global + freed;
  **both electrodes shifted 220 µm left** (`x0 = -mb.center_x - 220`). Head +
  couplers.
- **R2B** — now **SM** (`DieParameters`, was multimode). 2 mods + explicit RF
  chain.
- **R3A** — 2 mods, two input heads + input DC, 8 bondpads.
- **R3B** — **bespoke widened-gap electrodes** (the "safe" die). Two inline SM
  modulators via local `_bespoke_gap_modulator(length, gap)`: top gap =
  `gsg_gap + 0.5` (6.0 µm), bottom gap = `gsg_gap + 1.0` (6.5 µm), pinned to
  the live PDK `gsg_gap`. Bespoke via via local `_bespoke_via(gap)` =
  `_build_gsg_via(bot_xs=bespoke, top_xs=gsg_electrode_top_metal_50ohms)`. Two
  input heads (no input DC) + output DCs.
- **R4A / R4B** — 2 mods, head + couplers. R4B is the **only multimode** die
  now (`DieParametersMultimode`).
- Rows 2–4 modulator shift = 2 mm default; row 1 = 1250 µm local.

**PCM & calibration block** (`src/sonyx/blocks/pcm.py`, `docs/pcm_cells.md`):
stamped on every die by `die_scaffold` via `add_pcm_block(cell, x_right,
y_top)`, placed **next to the thermistance bonding pad** (right edge 200 µm
west of it, tops aligned). Cells (each a `@recipe`, packed L→R by bbox with
per-cell leading gaps):

- `pcm_open_gsg` — open GSG pads.
- `pcm_shorted_gsg` — GSG pads + low-R short bar (`gsg_short_top_metal_50ohms`).
- `pcm_ring_stack` — two all-pass rings (gaps 0.8 & 0.4 µm) stacked vertically
  25 µm apart; each is the buddha ring-test pattern (2-up 127 µm GC column,
  ring on a folded bus, rotated 90°, **no GC→bend lead-in** — the fold returns
  exactly to the bottom GC). Uses PDK `ringresonator_allpass_rib_sm_800nm`.
- `pcm_bondpad_1x2` — two `bondpad_for_test_top` pads (long side N-S) with
  `heater_cr` centered below, raised 75 µm, **no routing** (heater not yet
  wired to pads).
- Removed earlier: open-DC pair, dc-short, grating loopback, all labels.

**Per-die loss spiral:** `test_spiral_sm` in `die_scaffold` — a single SM
`spiral_rib_sm_800nm_for_length(target_length=50000, n_loops=8)` (5 cm, 8
loops, long side E-W, footprint ~2725×290 µm), placed 100 µm east of the
rightmost circuit edge coupler, inside the bottom keepout.

## 4. New PDK cells this session (`luqia_ln200`, registered in `cells/__init__.py`)

- `tech/cross_sections.py`: **`rib_ssm_800nm`** super-single-mode rib (400 nm
  core, `rib_super_singlemode_width` in `parameters.py`) — "safer" SM, more
  margin below the multimode cutoff. Not yet used by any cell.
- `cells/resonators.py` (**new file**):
  **`ringresonator_allpass_rib_sm_800nm(radius, gap, bus_length)`** — wraps
  `make_ring_allpass` on `rib_sm_800nm` at `ring_points=512` (smooth circle).
- `cells/rf.py`: **`gsg_short_top_metal_50ohms(length=40)`** — solid low-R
  TOP_METAL bar shorting signal↔grounds; port `e1` on
  `gsg_pads_top_metal_50ohms`.

## 5. Open items / pending

- **R3B bespoke via — top-metal fix (HIGHEST PRIORITY, promised but not
  done).** The user wants bottom metal at the bespoke (widened) gap and **top
  metal physically at the PDK gap**, with the via hole-array bridging the
  sub-µm ground offset (a "true split-gap via"). The current
  `_build_gsg_via(bot=bespoke, top=PDK)` draws top & bottom metal
  **congruently at the bespoke pitch** (the PDK via stamp is congruent) and
  only advertises PDK geometry on the top port — so the ≤1 µm ground step lands
  at the via↔taper junction rather than inside the via. Fix = a hand-rolled
  via: BOT_METAL grounds at bespoke pitch, TOP_METAL grounds at PDK pitch,
  Via1/Via2 hole array in the ~188 µm overlap. Explicitly requested and
  repeatedly deferred.
- **PCM heater** (`pcm_bondpad_1x2`) is a standalone `heater_cr` under the pad
  pair — **not electrically wired** to the pads yet.
- **Spiral** (`test_spiral_sm`) is standalone — not routed to the edge coupler.
- **DC de-embed cells**: user cut the open-DC pair (EO devices, no junction →
  little value); revisit only if an electrode-capacitor / leakage cell is
  wanted.
- **R4A / R4B output GSG pads** reportedly spill ~48 µm past the die west edge
  (from the original handoff) — verify / fix.
- Overlaps chased only for the PCM block + spiral (all zero); broader overlap
  sweep not done.

## 6. First step in the new chat

```
cd /Users/philippe/Github/sonyx_2026 \
  && uv run python -m sonyx.artifacts \
  && uv run ruff check src/sonyx \
  && uv run ty check src/sonyx
```

Confirm green (expect only the 3 known `die_r1a.py` ruff errors), then continue
— likely starting with the **R3B split-gap via**.
