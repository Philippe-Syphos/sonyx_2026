"""Unbalanced-MZI n_eff / n_g calibration ladder for R4B (placement only).

Places the unbalanced-MZI PCM ladder from
``pdk-luqia-ln200/docs/luqia_pdk_unbalanced_mzi_pcm_boe.md`` onto a die: the
three-rung ΔL ladder (A/B/C = 27.5 / 55 / 275 µm) in **both** waveguide
orientations -- ``unbalanced_mzi_rib_sm_800nm_ord`` (E-W) and
``..._ext`` (N-S) -- so six MZIs total, laid west→east as the ``_ord`` trio
then the ``_ext`` trio.

The six MZIs sit in **two vertical columns** -- an ``_ord`` column and an
``_ext`` column, side by side -- each stacking its three ΔL rungs (A top, B
middle, C bottom). (A single six-tall column doesn't fit: R4B's usable band is
only the strip above the full-width modulators.)

The fibre I/O is **two grating-coupler arrays** at the constant
``grating_coupling_pitch_for_tests`` pitch (one array per column), built from
``gratingcoupler_rib_sm_800nm_ext`` (N-S, fibre input from the north) and
sitting on a common horizontal line north of the two columns.

This is a **placement-only** pass -- the MZI optical ports are *not* routed to
the grating-coupler arrays yet; the cells are only positioned so the R4B
floorplan can be reviewed. Like :func:`sonyx.blocks.pcm.add_pcm_block`, it
stamps cached ``@recipe`` cells straight into the die (no wrapper Component to
collide at reticle assembly).
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from picasso.leaves import make_array
from picasso.recipe import recipe

from ..parameters import parameters as _p

# ΔL ladder (label, imbalance in um) -- the A/B/C rungs from the design note.
_LADDER: tuple[tuple[str, float], ...] = (("A", 27.5), ("B", 55.0), ("C", 275.0))

# Layout knobs (um).
_ROW_PITCH = 440.0  # vertical centre-to-centre of the stacked MZIs (ext column)
_ORD_STACK_GAP = 20.0  # vertical bbox-to-bbox gap between stacked MZIs (ord column)
_COL_GAP = 500.0  # horizontal bbox-to-bbox gap between the ord and ext columns
_EXT_STAGGER = 50.0  # per-rung horizontal offset of the ext column (staircase)
_BLOCK_RIGHT_MARGIN = 250.0  # gap from die right inner edge to the block right edge
# y-anchors relative to the die top inner edge (half_h - keepout):
_GC_LINE_DROP = 80.0  # GC-array line centre below the top inner edge
_GC_TO_STACK = 350.0  # top (A) MZI centre below the GC line


def _place_centered(
    cell: fw.Component, sub: fw.Component, name: str, cx: float, cy: float
) -> None:
    """Place ``sub`` into ``cell`` so its bbox centre lands at ``(cx, cy)``."""
    b = sub.bbox
    cell.add_placed(sub, name=name, x=cx - b.center_x, y=cy - b.center_y)


@recipe
def _gc_test_line(num: int) -> fw.Component:
    """A row of ``num`` N-S grating couplers at ``grating_coupling_pitch_for_tests``.

    ``gratingcoupler_rib_sm_800nm_ext`` (fibre input from the north), tiled with
    :func:`picasso.leaves.make_array`. Array ports: ``o1_r0_cN``.
    """
    return make_array(
        template=gratingcoupler_rib_sm_800nm_ext(),
        rows=1,
        cols=num,
        dx=_p.grating_coupling_pitch_for_tests.value,
        dy=0.0,
    )


def _add_gc_array_with_alignment(
    cell: fw.Component, axis: str, center_x: float, y_line: float, array_dx: float, array_dy: float
) -> None:
    """Place one GC array centred at ``center_x`` on line ``y_line`` + its align loop.

    The fibre-alignment loop sits one pitch to the array's left, GC tops on the
    same line (align bbox tops) so it continues the array's constant pitch.
    ``array_dx`` / ``array_dy`` are the GC-array bbox extents.
    """
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    _place_centered(cell, _gc_test_line(2 * len(_LADDER)), f"mzi_gc_array_{axis}", center_x, y_line)
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    target_xmax = (center_x - array_dx / 2.0) - (pitch - gc_w)
    target_ymax = y_line + array_dy / 2.0
    cell.add_placed(
        loop, name=f"mzi_gc_align_{axis}", x=target_xmax - lb.xmax, y=target_ymax - lb.ymax
    )


def add_mzi_ladder(cell: fw.Component) -> None:
    """Place the 6-MZI ladder (ord + ext) as two close vertical columns, top-right.

    Positions the cells in the clear top band of the die; does **not** route the
    MZI ports to the grating couplers (placement-only, by request).

    The ``_ord`` and ``_ext`` columns each stack their three ΔL rungs vertically
    (A top, B middle, C bottom). Ord rungs pack to a fixed ``_ORD_STACK_GAP``
    bbox-to-bbox gap; ext rungs use the ``_ROW_PITCH`` centre pitch and are
    **staggered** ``_EXT_STAGGER`` in x per rung (a staircase). The two columns
    sit ``_COL_GAP`` apart (bbox-to-bbox), and the whole block is pushed to the
    **right** of the die (``_BLOCK_RIGHT_MARGIN`` from the right inner edge).

    Both constant-pitch grating-coupler arrays sit on **one** common line north
    of the columns; ``_COL_GAP`` is wide enough that they do not overlap
    horizontally. Each is centred over its column with a fibre-alignment loop one
    pitch to its left (``mzi_gc_align_ord`` / ``_ext``).
    """
    half_h = _p.die_height.value / 2.0
    half_w = _p.die_width.value / 2.0
    top_inner = half_h - _p.keepout_width.value
    right_inner = half_w - _p.keepout_width.value

    ord_cells = [(lbl, pdk.cells["unbalanced_mzi_rib_sm_800nm_ord"](length_imbalance=dl))
                 for lbl, dl in _LADDER]
    ext_cells = [(lbl, pdk.cells["unbalanced_mzi_rib_sm_800nm_ext"](length_imbalance=dl))
                 for lbl, dl in _LADDER]
    ab = _gc_test_line(2 * len(_LADDER)).bbox

    # --- horizontal layout, relative to the ord column centre x_ord ---
    ord_hw = max(m.bbox.dx for _, m in ord_cells) / 2.0
    ext_stag = [k * _EXT_STAGGER for k in range(len(ext_cells))]
    ext_left_rel = min(s - m.bbox.dx / 2.0 for s, (_, m) in zip(ext_stag, ext_cells, strict=True))
    ext_right_rel = max(s + m.bbox.dx / 2.0 for s, (_, m) in zip(ext_stag, ext_cells, strict=True))
    dx_col = ord_hw + _COL_GAP - ext_left_rel  # x_ext - x_ord (_COL_GAP bbox gap)
    ext_center_rel = dx_col + (ext_left_rel + ext_right_rel) / 2.0  # ext bbox centre - x_ord
    # Block right edge (rel to x_ord) = max of the ext column and ext GC array.
    block_right_rel = max(dx_col + ext_right_rel, ext_center_rel + ab.dx / 2.0)
    x_ord = (right_inner - _BLOCK_RIGHT_MARGIN) - block_right_rel
    x_ext = x_ord + dx_col
    ext_center_x = x_ord + ext_center_rel

    # --- vertical layout: one GC line, MZI columns below ---
    y_gc = top_inner - _GC_LINE_DROP
    y_stack_top = y_gc - _GC_TO_STACK  # top (A) rung centre, both columns

    # Ord column: fixed bbox-to-bbox gap, A top-anchored.
    prev_bottom = 0.0
    for k, (label, m) in enumerate(ord_cells):
        half = m.bbox.dy / 2.0
        cy = y_stack_top if k == 0 else prev_bottom - _ORD_STACK_GAP - half
        _place_centered(cell, m, f"mzi_ord_{label}", x_ord, cy)
        prev_bottom = cy - half
    # Ext column: centre pitch, staggered in x per rung.
    for k, (label, m) in enumerate(ext_cells):
        cy = y_stack_top - k * _ROW_PITCH
        _place_centered(cell, m, f"mzi_ext_{label}", x_ext + ext_stag[k], cy)

    # Two GC arrays on one common line, each with its left alignment loop.
    _add_gc_array_with_alignment(cell, "ord", x_ord, y_gc, ab.dx, ab.dy)
    _add_gc_array_with_alignment(cell, "ext", ext_center_x, y_gc, ab.dx, ab.dy)
