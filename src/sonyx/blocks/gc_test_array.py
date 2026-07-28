"""Standalone open grating-coupler test array (N couplers + left alignment loop).

Future fibre I/O for a device that isn't routed yet: a horizontal ext
grating-coupler array (``gratingcoupler_rib_sm_800nm_ext``, N-S, input from the
north) whose ``num`` coupler ports are left **open**, with a grating-coupler
alignment loop (``gratingcoupler_alignment_rib_sm_800nm_ext``) one pitch to its
left, continuing the array's constant pitch. :func:`add_open_gc_array` stamps
the cached recipe cells straight into the die (no wrapper Component to collide at
reticle assembly) in the die's top-right corner.

Used on R1A / R1B as the (unrouted) fibre I/O for the extra top modulator
(``gsg_modulator_top_2``).
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from picasso.leaves import make_array
from picasso.recipe import recipe

from ..parameters import parameters as _p

# Gaps (um) from the die inner edges to the array (its right edge / coupler tops).
_RIGHT_MARGIN = 250.0
_TOP_MARGIN = 40.0


@recipe
def _open_gc_line(num: int) -> fw.Component:
    """A row of ``num`` N-S ext grating couplers at ``grating_coupling_pitch_for_tests``."""
    return make_array(
        template=gratingcoupler_rib_sm_800nm_ext(),
        rows=1,
        cols=num,
        dx=_p.grating_coupling_pitch_for_tests.value,
        dy=0.0,
    )


def add_open_gc_array(cell: fw.Component, num: int, prefix: str) -> None:
    """Place a ``num``-coupler open GC array + left alignment loop, top-right of the die.

    The array's right edge sits ``_RIGHT_MARGIN`` off the right inner edge (clear
    of the top-right corner alignment loop) and its coupler tops ``_TOP_MARGIN``
    below the top inner edge. Instances: ``{prefix}_array`` (ports ``o1_r0_cN``,
    open) and ``{prefix}_align`` (the alignment loop).
    """
    half_w = _p.die_width.value / 2.0
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    x_right = (half_w - kw) - _RIGHT_MARGIN
    y_top = (half_h - kw) - _TOP_MARGIN

    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    arr = _open_gc_line(num)
    ab = arr.bbox
    # Array: right edge at x_right, coupler tops at y_top.
    cell.add_placed(arr, f"{prefix}_array", x=x_right - ab.xmax, y=y_top - ab.ymax)
    # Alignment loop one pitch to the left, GC tops on the same line (continuing
    # the array's constant pitch).
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    target_xmax = (x_right - ab.dx) - (pitch - gc_w)
    cell.add_placed(loop, f"{prefix}_align", x=target_xmax - lb.xmax, y=y_top - lb.ymax)
