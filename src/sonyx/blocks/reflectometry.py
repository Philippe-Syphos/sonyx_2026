"""Reflectometry test cell (R1A) -- fibre-I/O first pass.

A simple OFDR/reflectometry structure (the reflector + delay path land in a later
pass). This first pass places only the fibre I/O: a row of four N-S grating
couplers (``gratingcoupler_rib_sm_800nm_ext``) below the R1A terminators -- a
left fibre-alignment loop (two couplers) followed by two open couplers that will
feed the reflectometry DUT. Placement-only; the open couplers are left unrouted.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.beam_dumps import beam_dump_rib_sm_800nm
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from luqia_ln200.cells.waveguides import straight_rib_sm_800nm
from picasso.leaves import make_array
from picasso.recipe import recipe

from ..parameters import parameters as _p

# Four grating couplers: a left alignment loop (two couplers) + this many open
# couplers, all on one constant-pitch line.
_NUM_OPEN_GC = 2
# Layout (um): left edge off the left inner edge; coupler tops this far below the
# top inner edge -- clear below the terminator row (bottom ~2122).
_LEFT_MARGIN = 250.0
_TOP_DROP = 560.0

# Reflectometry waveguides: two 9 mm horizontal straights below the couplers, one
# unterminated (open end) and one beam-dumped. Axes below the GC line, in the
# clear band above the top-2 modulator head.
_WG_LENGTH = 9000.0
_WG_GAP = 200.0  # first WG axis below the GC-top line
_WG_PITCH = 130.0  # vertical spacing between the two WG axes
_WG_X_SHIFT = 500.0  # shift the waveguide start (west end) right of the coupler left edge


@recipe
def _gc_line(num: int) -> fw.Component:
    """A row of ``num`` N-S grating couplers at ``grating_coupling_pitch_for_tests``."""
    return make_array(
        template=gratingcoupler_rib_sm_800nm_ext(),
        rows=1,
        cols=num,
        dx=_p.grating_coupling_pitch_for_tests.value,
        dy=0.0,
    )


def add_reflectometry_cell(cell: fw.Component) -> None:
    """Place the reflectometry cell's 4-coupler fibre I/O below the R1A terminators.

    A left fibre-alignment loop (two couplers) + ``_NUM_OPEN_GC`` open couplers,
    on one constant-pitch line: the loop's left edge sits ``_LEFT_MARGIN`` off the
    left inner edge and all coupler tops ``_TOP_DROP`` below the top inner edge
    (clear below the terminator row). Instances ``reflecto_gc_align`` (loop) and
    ``reflecto_gc_array`` (open couplers, ports ``o1_r0_cN``). Placement-only.
    """
    half_w = _p.die_width.value / 2.0
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx

    x_left = (-half_w + kw) + _LEFT_MARGIN
    y_top = (half_h - kw) - _TOP_DROP

    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(loop, "reflecto_gc_align", x=x_left - lb.xmin, y=y_top - lb.ymax)

    arr = _gc_line(_NUM_OPEN_GC)
    ab = arr.bbox
    array_xmin = (x_left + lb.dx) + (pitch - gc_w)
    cell.add_placed(arr, "reflecto_gc_array", x=array_xmin - ab.xmin, y=y_top - ab.ymax)

    # Two 9 mm horizontal waveguides below the couplers: one unterminated
    # (bare open end) and one terminated with a beam dump. Left-aligned with the
    # coupler row; each extends east.
    y_wg1 = y_top - _WG_GAP
    y_wg2 = y_wg1 - _WG_PITCH
    x_wg = x_left + _WG_X_SHIFT
    wg_open = straight_rib_sm_800nm(length=_WG_LENGTH)
    cell.add_placed(
        wg_open, "reflecto_wg_open",
        x=x_wg - wg_open.bbox.xmin, y=y_wg1 - wg_open.bbox.center_y,
    )
    wg_dumped = straight_rib_sm_800nm(length=_WG_LENGTH)
    wd = cell.add_placed(
        wg_dumped, "reflecto_wg_dumped",
        x=x_wg - wg_dumped.bbox.xmin, y=y_wg2 - wg_dumped.bbox.center_y,
    )
    # Beam dump on the east (far) end -- absorbs the wave (no back-reflection).
    cell.put(beam_dump_rib_sm_800nm(), wd.ports.o2, port_to="o1", name="reflecto_beamdump")
