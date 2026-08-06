"""Standalone open grating-coupler test array (N couplers + left alignment loop).

Future fibre I/O for a device that isn't routed yet: a horizontal ext
grating-coupler array (``gratingcoupler_rib_sm_800nm_ext``, N-S, input from the
north) whose ``num`` coupler ports are left **open**, with a grating-coupler
alignment loop (``gratingcoupler_alignment_rib_sm_800nm_ext``) one pitch to its
left, continuing the array's constant pitch.

:func:`open_gc_array_block` is one self-contained Component in its own local
frame (origin at the loop's west edge / GC tops line), exposing the array's
open coupler ports; the dies (R1A / R1B) place it with ``add_placed`` in the
top-right corner as the (unrouted) fibre I/O for the extra top modulator
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


@recipe
def open_gc_array_block(num: int) -> fw.Component:
    """A ``num``-coupler open GC array + left alignment loop as one block.

    Local frame: x = 0 on the alignment loop's west edge, y = 0 on the GC/loop
    tops line. Instances ``align`` (the loop) and ``array``; the array's open
    coupler ports are exposed on the block as ``o1_r0_cN``. The die places this
    single Component with ``add_placed``.
    """
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    cell = fw.Component()
    # Alignment loop at the block's west edge, tops on the y = 0 line.
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(loop, name="align", x=0.0 - lb.xmin, y=0.0 - lb.ymax)
    # Array one pitch onward, GC tops on the same line (continuing the pitch).
    arr = _open_gc_line(num)
    ab = arr.bbox
    array_xmin = lb.dx + (pitch - gc_w)
    arr_inst = cell.add_placed(arr, name="array", x=array_xmin - ab.xmin, y=0.0 - ab.ymax)
    for i in range(num):
        cell.add_port(f"o1_r0_c{i}", (arr_inst.name, f"o1_r0_c{i}"))
    cell.cell_type = "test_structure"
    cell.description = (
        f"Open {num}-coupler grating test array + left alignment loop -- "
        "future fibre I/O, coupler ports exposed and unrouted."
    )
    return cell
