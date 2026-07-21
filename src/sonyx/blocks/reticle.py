"""Full-reticle assembly for sonyx — the 22 x 22 mm 2x4 die shuttle (top cell).

Places the eight die holders (:mod:`sonyx.blocks.dies`) on the 2-column x
4-row grid, then draws the 150 µm deep-etch **dicing street grid** — the
reticle perimeter street plus every inter-die lane, INCLUDING the lane between
the two columns. Neighbouring dies share one lane (drawn once), so the streets
form a single grid on the ``DEEP_ETCH`` layer that fills every gap exactly.
The reticle's 22 mm extent is defined by the perimeter trench; the ``DIE``
layer carries the eight die-boundary rectangles (one per die), nothing else.

Geometry is pinned in :mod:`sonyx.parameters`
(``docs/tapeout_plan_reticle_v1.md`` §2); this module only positions it.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.tech.parameters import parameters as _pdk
from picasso.geometry.ops import rectangle

from ..parameters import DIE_COLUMNS, DIE_ROWS
from ..parameters import parameters as _p
from .dies import DIE_GRID

# luqia_ln200 dicing/singulation trench, string form → resolved against the
# active PDK at materialize (DEEP_ETCH.dark = GDS 50/0).
_TRENCH_LAYER = "DEEP_ETCH.dark"


def reticle() -> fw.Component:
    """Assemble and return the full-reticle top cell (named ``sonyx``)."""
    reticle_size = _p.reticle_size.value
    die_w = _p.die_width.value
    die_h = _p.die_height.value
    lane = _p.dicing_lane.value

    # The dicing lane is filled by the deep-etch trench, so its width must be
    # the PDK's deep_trench_width — guard against the two drifting apart.
    trench_w = _pdk.deep_trench_width.value
    if abs(trench_w - lane) > 1e-6:
        raise ValueError(
            f"dicing_lane ({lane} µm) must equal luqia deep_trench_width ({trench_w} µm)"
        )

    top = fw.Component(name="sonyx")

    col_pitch = die_w + lane
    row_pitch = die_h + lane
    # Die centres, symmetric about the origin. Column 0 = left; row 0 = top.
    col_x = [(-(DIE_COLUMNS - 1) / 2.0 + i) * col_pitch for i in range(DIE_COLUMNS)]
    row_y = [((DIE_ROWS - 1) / 2.0 - j) * row_pitch for j in range(DIE_ROWS)]

    # --- Place the eight die holders ----------------------------------------
    for j, row in enumerate(DIE_GRID):
        for i, die_builder in enumerate(row):
            die = die_builder()
            top.add_placed(die, die.name, x=col_x[i], y=row_y[j])

    # --- 150 µm deep-etch dicing street grid (DEEP_ETCH) --------------------
    # Vertical streets: DIE_COLUMNS+1 full-height strips (2 perimeter + inter-
    # column lanes). Horizontal streets: DIE_ROWS+1 full-width strips. They
    # overlap at the crossings (a single unioned grid on the mask).
    for k in range(DIE_COLUMNS + 1):
        x_center = (k - DIE_COLUMNS / 2.0) * col_pitch
        rectangle(
            top,
            width=trench_w,
            height=reticle_size,
            layer=_TRENCH_LAYER,
            center=(x_center, 0.0),
        )
    for k in range(DIE_ROWS + 1):
        y_center = (k - DIE_ROWS / 2.0) * row_pitch
        rectangle(
            top,
            width=reticle_size,
            height=trench_w,
            layer=_TRENCH_LAYER,
            center=(0.0, y_center),
        )

    top.cell_type = "reticle_assembly"
    return top
