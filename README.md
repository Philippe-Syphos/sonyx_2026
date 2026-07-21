# sonyx

A Picasso layout targeting the **luqia_ln200** PDK, scaffolded by
`picasso.layout_dump()`.

## Build

This is a [uv](https://docs.astral.sh/uv/)-managed project. Set up the
environment once — resolves dependencies, writes the committed `uv.lock`,
and provisions `.venv`:

```bash
uv sync
```

Build / validate / write GDS (run Python under the project env with
`uv run`):

```python
from sonyx import layout

layout.materialize()              # build the top cell
layout.validate()                 # framework checks
layout.write_gds("sonyx.gds")  # emit GDS
```

```bash
uv run pytest        # smoke tests (build / validate / write-GDS)
```

## Designing

Edit `src/sonyx/design.py`:

- **`knobs`** — tunable `fw.Variable`s. They render as GUI controls
  (sliders for bounded numerics, dropdowns for `allowed=` choices) and are
  sweepable via `layout.materialize(overrides={...})`.
- **`floorplan`** — optional die frame (`fw.Floorplan(width=, height=, label=)`).
  When set, `materialize()` stamps the die boundary + label automatically.
- **`build(layout)`** — composes the top cell. Call `layout.stamp_knobs(top)`
  before adding any `fw.ref(...)`-referencing children.

Reusable design sub-circuits go in `src/sonyx/blocks/` as `@fw.recipe`
factories.

## Artifacts

Rebuild the GDS (building a chip is expensive, so this is on-demand, not
on-import):

```bash
uv run python -m sonyx.artifacts
# equivalently: uv run python -m picasso.layout_artifacts sonyx --gds-only
```

The GDS is the deliverable; verify it numerically. Netlist / DRC / design
report / floorplan SVGs are available by dropping `gds_only=True` in
`artifacts.py` (they land under `layout_artifacts/` + `docs/generated/`).
