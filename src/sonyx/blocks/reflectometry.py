"""Reflectometry test cell (R1A).

A simple OFDR/reflectometry structure: a row of four N-S grating couplers
(``gratingcoupler_rib_sm_800nm_ext``) -- a left fibre-alignment loop (two
couplers) followed by two couplers that launch into the DUT -- plus the two long
reflectometry waveguides below them. The block sits in the clear band **between
R1A's two lower modulators**; it used to live in the top-left band under the
(since relocated) terminator row.

Two passes: :func:`add_reflectometry_cell` places the block,
:func:`add_reflectometry_routes` wires each launch coupler to the west input of
one waveguide. The waveguides' **east** ends are the measurement and stay
unrouted -- ``reflecto_wg_open`` ends in a bare facet (a reflector),
``reflecto_wg_dumped`` in a beam dump (no return) -- so the pair differs only in
its termination. (The reflector + delay path land in a later pass.)
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
from picasso.routing import ObstacleSet

from ..parameters import parameters as _p

# Four grating couplers: a left alignment loop (two couplers) + this many launch
# couplers, all on one constant-pitch line -- one launch coupler per waveguide,
# wired by :func:`add_reflectometry_routes`.
_NUM_LAUNCH_GC = 2
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

    A left fibre-alignment loop (two couplers) + ``_NUM_LAUNCH_GC`` launch couplers on
    one constant-pitch line, with the two reflectometry waveguides below them. The
    loop's left edge sits ``_LEFT_MARGIN`` off the left inner edge; vertically the
    whole block is **centred in the clear band** between ``lower_modulator``'s top
    edge and ``upper_modulator``'s bottom edge, so it tracks the modulators rather
    than the die edge. Instances ``reflecto_gc_align`` (loop) and
    ``reflecto_gc_array`` (launch couplers, ports ``o1_r0_cN``). Placement only --
    :func:`add_reflectometry_routes` wires the couplers to the waveguides.

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
    arr = _gc_line(_NUM_LAUNCH_GC)
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


def add_reflectometry_routes(cell: fw.Component, obstacles: ObstacleSet | None = None) -> None:
    """Route the two launch couplers into the two reflectometry waveguides' west inputs.

    Feeds each 8 mm waveguide from a grating coupler so the pair becomes a real
    measurement: same launch, same length, and the only difference is what
    terminates the far end -- ``reflecto_wg_open``'s bare facet (a reflector) vs
    ``reflecto_wg_dumped``'s beam dump (no return). The waveguides' **east** ports
    stay untouched; they are the device under test, not something to route.

    One bundle, one ``autoroute`` call: both couplers face **south** and both
    targets face **west**, so each lane drops out of the coupler row into the
    corridor above the waveguides and peels off east into its ``o1``. The two lanes
    share that corridor, so planning them together is what keeps them coherent --
    two separate calls plan independently and cross in it.

    **Pairing is reversed** (west coupler ``c0`` -> the *lower* waveguide, east
    coupler ``c1`` -> the *upper* one), the same rule as
    :func:`..dc_length_sweep.add_group_input_routes` and for the same reason: in the
    descending corridor the lanes are ordered in x, and peeling east the lane that
    turns first (the upper target) has to be the inner-most, i.e. the east-most.
    The natural ``c0`` -> upper order would drive ``c1``'s descent straight through
    ``c0``'s eastward run at y = 31.2.

    Tight SM spec (``lbend_rib_sm_800nm_tight``, 30 um footprint radius): ``c1``
    sits only 98.7 um west of the target column, so its peel-off L has to fit in
    less than one default 100 um-radius bend's worth of eastward run.

    Args:
        cell: die cell already carrying the reflectometry block
            (:func:`add_reflectometry_cell`), extended in place.
        obstacles: optional :class:`~picasso.routing.ObstacleSet` to plan against --
            on R1A the DC-output chain from
            :func:`.dies._head_coupler_block.add_mzm_output_routes`, whose
            ``dc_ec_bot`` drop passes ~230 um west of the west-most descent.
    """
    cell.autoroute(
        ports_a=[("reflecto_wg_dumped", "o1"), ("reflecto_wg_open", "o1")],
        ports_b=[
            ("reflecto_gc_array", "o1_r0_c0"),
            ("reflecto_gc_array", "o1_r0_c1"),
        ],
        obstacles=obstacles,
        spec="routing_sm_tight",
        strategy="grid_astar",
        step=10.0,
        name="reflecto_gc_wg",
    )
