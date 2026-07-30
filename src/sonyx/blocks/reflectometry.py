"""Reflectometry test cell (R1A) -- fibre-I/O first pass.

A simple OFDR/reflectometry structure (the reflector + delay path land in a later
pass). This first pass places only the fibre I/O: a row of four N-S grating
couplers (``gratingcoupler_rib_sm_800nm_ext``) -- a left fibre-alignment loop
(two couplers) followed by two open couplers that will feed the reflectometry
DUT -- plus the two long reflectometry waveguides below them. The block sits in
the clear band **between R1A's two lower modulators**; it used to live in the
top-left band under the (since relocated) terminator row.
Placement-only; the open couplers are left unrouted.
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
# Layout (um): left edge off the left inner edge. Vertically the block is centred
# in the clear band between the two lower modulators (see
# :func:`add_reflectometry_cell`), so there is no top-edge drop any more.
_LEFT_MARGIN = 1000.0

# Reflectometry waveguides: two 8 mm horizontal straights below the couplers, one
# unterminated (open end) and one beam-dumped. Axes below the GC line.
_WG_LENGTH = 8000.0
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


def add_reflectometry_cell(
    cell: fw.Component,
    lower_modulator: str = "gsg_modulator_bot",
    upper_modulator: str = "gsg_modulator_top",
) -> None:
    """Place the reflectometry cell in the band **between** two stacked modulators.

    A left fibre-alignment loop (two couplers) + ``_NUM_OPEN_GC`` open couplers on
    one constant-pitch line, with the two reflectometry waveguides below them. The
    loop's left edge sits ``_LEFT_MARGIN`` off the left inner edge; vertically the
    whole block is **centred in the clear band** between ``lower_modulator``'s top
    edge and ``upper_modulator``'s bottom edge, so it tracks the modulators rather
    than the die edge. Instances ``reflecto_gc_align`` (loop) and
    ``reflecto_gc_array`` (open couplers, ports ``o1_r0_cN``). Placement-only.

    Args:
        cell: die cell that already carries the two modulators.
        lower_modulator: instance name bounding the band from below.
        upper_modulator: instance name bounding the band from above.
    """
    half_w = _p.die_width.value / 2.0
    kw = _p.keepout_width.value
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx

    x_left = (-half_w + kw) + _LEFT_MARGIN

    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    arr = _gc_line(_NUM_OPEN_GC)
    ab = arr.bbox
    wg_dy = straight_rib_sm_800nm(length=_WG_LENGTH).bbox.dy

    # Block height, measured down from the coupler-top line (y_top): the couplers
    # hang below it, and the lower waveguide axis sits _WG_GAP + _WG_PITCH below
    # with its own half-height beyond that. Independent of y_top, so it can be
    # solved for before choosing where the block sits.
    depth = max(lb.dy, ab.dy, _WG_GAP + _WG_PITCH + wg_dy / 2.0)
    lo_bb = cell.instances[lower_modulator].bbox
    hi_bb = cell.instances[upper_modulator].bbox
    assert lo_bb is not None and hi_bb is not None  # placed instances have geometry
    band_lo, band_hi = lo_bb.ymax, hi_bb.ymin
    y_top = (band_lo + band_hi) / 2.0 + depth / 2.0  # centre the block in the band

    cell.add_placed(loop, name="reflecto_gc_align", x=x_left - lb.xmin, y=y_top - lb.ymax)

    array_xmin = (x_left + lb.dx) + (pitch - gc_w)
    cell.add_placed(arr, name="reflecto_gc_array", x=array_xmin - ab.xmin, y=y_top - ab.ymax)

    # Two horizontal waveguides below the couplers: one unterminated (bare open
    # end) and one terminated with a beam dump. Left-aligned with the coupler row;
    # each extends east.
    y_wg1 = y_top - _WG_GAP
    y_wg2 = y_wg1 - _WG_PITCH
    x_wg = x_left + _WG_X_SHIFT
    wg_open = straight_rib_sm_800nm(length=_WG_LENGTH)
    cell.add_placed(
        wg_open, name="reflecto_wg_open",
        x=x_wg - wg_open.bbox.xmin, y=y_wg1 - wg_open.bbox.center_y,
    )
    wg_dumped = straight_rib_sm_800nm(length=_WG_LENGTH)
    wd = cell.add_placed(
        wg_dumped, name="reflecto_wg_dumped",
        x=x_wg - wg_dumped.bbox.xmin, y=y_wg2 - wg_dumped.bbox.center_y,
    )
    # Beam dump on the east (far) end -- absorbs the wave (no back-reflection).
    cell.put(beam_dump_rib_sm_800nm(), wd.ports.o2, port_to="o1", name="reflecto_beamdump")
