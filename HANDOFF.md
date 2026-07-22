# Sonyx layout — handoff

Context to continue work on the **sonyx_2026** photonic layout (luqia_ln200 PDK +
picasso framework) in a fresh chat.

## 1. Repos & boundaries (critical)

| Repo | Role | Access |
|------|------|--------|
| `sonyx_2026` | the layout (this repo) | **read/write** |
| `pdk-luqia-ln200` | the PDK (800 nm TFLN, single-band) | **read/write** |
| `picasso-pdk-dev/picasso` | the framework | **read/write** |
| `buddha_lxtltpro_202602` | prior layout (lxt-ltpro PDK) — best pattern reference | **read-only** |
| bare `picasso`, `pdk-lxt-ltpro-picasso` | parallel work / source PDK | **read-only** |

Never edit the read-only repos — mine them for patterns only. Any framework
change goes to `picasso-pdk-dev`, never bare `picasso`.

## 2. Workflow & conventions

- **uv-managed.** Run everything from the repo root: `uv run …`.
- **Build the GDS:** `uv run python -m sonyx.artifacts` → GDS-only into
  `layout_artifacts/sonyx.gds` (no netlist/DRC/SVG by default; `gds_only=True`).
- **No PNG/SVG renders.** Verify **numerically** (bbox, port positions, per-layer
  polygons via KLayout `pya`), never by rendered preview.
- **Keep green on every change:** `uv run ruff check src/sonyx` and
  `uv run ty check src/sonyx`. Line length 100; use ASCII in code/docstrings
  (ambiguous `×`/`−` trip ruff RUF00x).
- **Layers as strings** (`"DEEP_ETCH.dark"`, `"DIE.boundary"`, `"KEEPOUT.drawing"`,
  `"WG_RIB.drawing"`) — ty-clean, unlike `_layers.X.purpose` (types as `object`).
- **Uncommitted.** Commit only when asked; branch off `main` first. Co-author +
  PR footer rules apply.

## 3. Architecture

- `blocks/reticle.py::reticle()` → top cell **`sonyx`** (22×22 mm). Places the 8
  dies on the 2-col × 4-row grid and draws the 150 µm `DEEP_ETCH` dicing street
  grid (perimeter + all inter-die lanes incl. between columns). No reticle
  outline frame — the 22 mm extent is the perimeter trench (outer edge ±11000).
  `design.py::build()` is a thin adapter returning `reticle()`.
- **`blocks/dies/_frame.py::die_scaffold(name, die_params)`** — shared placements
  common to every die; returns the **live, mutable cell**:
  - die-defining rectangle on `DIE.boundary` (edges abut the trench inner wall),
  - `keepout_width` perimeter keep-out ring on `KEEPOUT.drawing` (4 rectangle
    tiles = exact ring, no corner gaps),
  - die-ID label (`make_label` glyph polygons) on `WG_RIB.drawing`, top-left,
  - circuit edge-coupler array (`edge_couplers_circuit`) lower-left + leftmost-pair
    loopback (`ec_loopback_circuit`),
  - TOP_METAL bond-pad array (`bondpads`) lower-right.
- **`blocks/dies/die_r{1..4}{a,b}.py`** — each is the **full per-die builder**:
  calls `die_scaffold`, then adds that die's own geometry/wiring on the returned
  cell (reach shared elements via `cell.instances["…"].ports`), returns it.
  Rows R1(top)→R4(bottom); columns A(left)/B(right). `DIE_GRID[row][col]` in
  `blocks/dies/__init__.py` is the placement map.
- **Shared sub-circuit modules** (reusable, like buddha's blocks):
  `blocks/edge_couplers.py` (`circuit_edge_coupler_array`),
  `blocks/bondpads.py` (`bondpad_array`). Both use the `make_array` leaf + `@recipe`.
  (There is intentionally **no** `modulators.py` — modulators are placed directly
  in each die body.)

## 4. What each die currently contains

Named sub-instances on every die cell:

- `die_id` — ID label (WG_RIB.drawing 10/0), top-left.
- `edge_couplers_circuit` — row of `num_edge_couplers_circuit` couplers
  (`edgecoupler_rib_sm_800nm_ext` + `ec_tip_800nm` facet lead), facets south,
  lower-left; ports `o2_r0_cN` (circuit, north). `ec_loopback_circuit` = tight
  127 µm C-bend U-turn joining `o2_r0_c0`↔`o2_r0_c1`.
- `bondpads` — row of `num_bondpads` `bondpad_top_metal` pads, lower-right.
- `gsg_modulator_bot`, `gsg_modulator_top` — two GSG phase-modulator electrodes
  (no couplers) stacked vertically, centred in x. SM (`straight_gsg_modulator_800nm`)
  on column A, multimode (`straight_gsg_modulator_mm_800nm`) on column B — chosen
  via `DieParameters.gsg_modulator_cell`. Ports `o1-o4` (optical), `e1/e2` (electrode).
- `rf_via_bot`, `rf_via_top` — `gsg_via_electrode_top_bot_holes_50ohms` (hole-array
  via) put() on each modulator's east electrode port `e2`, lifting BOT_METAL → TOP
  metal. Continuation port for the rest of the RF chain: the via's `top_e2`
  (east, top metal).

## 5. Parameters (`src/sonyx/parameters.py`)

`DIE_COLUMNS=2`, `DIE_ROWS=4` (module-level ints).

**Layout-wide `Parameters`** (all PLACEHOLDER values):
`reticle_size=22000`, `dicing_lane=150`, `die_width=10775`, `die_height=5312.5`,
`keepout_width=50`, `edge_coupling_pitch_for_circuits=127`,
`edge_coupling_pitch_for_tests=127`, `grating_coupling_pitch_for_circuits=254`,
`grating_coupling_pitch_for_tests=254`, `edge_coupler_extension_length=10`,
`edge_coupler_protrusion=5`, `edge_coupler_horizontal_shift=300`,
`bondpad_horizontal_shift=300`, `bondpad_vertical_shift=50`,
`gsg_modulator_spacing=1000` (centre-to-centre of the 2 stacked mods),
`gsg_modulator_vertical_shift=750` (bottom mod's bottom edge above die bottom edge),
`gsg_modulator_electrode_length=8500`.

`_check_tiling()` asserts at import that dies + lanes exactly fill 22 mm.

**Per-die `DieParameters(ParametersBase)`**: `num_edge_couplers_circuit=8`,
`num_bondpads=9`, `gsg_modulator_cell="straight_gsg_modulator_800nm"`.
`DieParametersMultimode(DieParameters)` overrides `gsg_modulator_cell` →
`"straight_gsg_modulator_mm_800nm"` (column-B dies use it).

> **Gotcha:** `ParameterField` is **read-only and class-shared** (`__get__` returns
> one class-level Parameter; `__set__` raises). `DieParameters()` instances can't
> carry different values — per-die variation needs a **subclass** that redeclares
> the field (that's why column B is `DieParametersMultimode`).

## 6. Key gotchas learned

- **Pass a BUILT Component to `add_placed`, not a name string**, when you need
  ports during build — a string-placed instance has no backing child until
  materialize, so its ports aren't resolvable in the die body. Use
  `pdk.cells[name](...)` (a built Component). The same built Component can be
  `add_placed` twice (two instances).
- **`put()` for abutment/wiring** (port-to-port), not `add_placed` + manual xy.
- **Modulator electrode is `gsg_electrode_bot_metal`** (un-suffixed, BOTTOM metal);
  the whole RF launch chain uses the `_50ohms` variants — a **via** (electrode
  top-bot) is what bridges BOT→TOP metal, not a taper. Same BOT_METAL layer, so
  `put()` abuts fine despite the `_50ohms` name difference.
- Edge couplers / modulators need the PDK active — they build during
  `materialize()` → `build()` (which runs `with layout.pdk`).
- Dies are plain rectangles — **no drawn MZM/test band split** inside the die
  (rejected earlier; the plan's 2.5/2.81 mm split is a floorplanning concept, not
  drawn geometry). Do not re-add a band line.

## 7. Next steps / TODO

- **Finish the RF launch chain** from each `rf_via_{bot,top}.top_e2` (top metal),
  same for SM/MM, using `put()`:
  `gsg_taper_electrode_to_routing_top_metal_50ohms` (or `…_to_pads_…`) →
  `gsg_bondpads_top_metal_50ohms` launch; add the `gsg_terminator_top_metal_50ohms_parallel`
  on the modulator's **left** (`e1`) end (traveling-wave termination).
  All these cells are in `pdk-luqia-ln200/src/luqia_ln200/cells/rf.py`.
  → The RF wiring is currently duplicated inline in all 8 die bodies; once the
  chain grows, consider factoring it into a shared routine (each die calls it with
  its modulator instances), like `edge_couplers`/`bondpads`.
- **Optical routing**: connect edge-coupler `o2_r0_cN` ports to the modulator
  optical ports (`o1-o4`) per die.
- **Per-die DUTs**: fill each die's test content per `docs/tapeout_plan_reticle_v1.md`
  §4.0 (recorded in each `die_r*.py` module docstring). AEPONYX labels: optical on
  `WG_RIB.label` (10/11), electrical on `VIA2.label` (31/11).
- **Tune placeholders**: nearly every parameter is a PLACEHOLDER; revisit
  `gsg_modulator_vertical_shift` etc. against real clearances.

## 8. Reference docs

- Tape-out plan: `pdk-luqia-ln200/docs/tapeout_plan_reticle_v1.md` (2×4 reticle,
  MZM DOE + test-cell catalog, AEPONYX label conventions).
- PDK cells: `pdk-luqia-ln200/src/luqia_ln200/cells/` (couplers, modulators, rf,
  dc, bends, …); layers in `tech/layers.py`, cross-sections in
  `tech/cross_sections.py`, params in `tech/parameters.py`.
