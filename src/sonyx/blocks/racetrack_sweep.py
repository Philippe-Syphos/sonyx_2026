"""Variable-length racetrack resonator sweep (R2A) -- placement-only pass.

Five all-pass racetrack resonators (`racetrack_allpass_rib_sm_800nm`) with a
**fixed bend point coupler** (gap 700 nm, R = 75 um) and a swept straight length
(L_s = 100 / 250 / 500 / 1000 / 1500 um). At fixed coupling, the round-trip loss
grows with L_s, so the sweep walks through coupling regimes (critical at
~500 um, per the coupler sim). Fitting round-trip loss vs L_s: the **slope gives
the propagation loss**, the **intercept the bend + coupler loss**; the shared,
constant point coupler also lets you average the extracted coupling coefficient
across devices as a self-consistency check.

The racetracks stand in a column (buses on one low line, loops extending up),
with a grating-coupler array + alignment loop to their right for fibre I/O (2
couplers per device). :func:`add_racetrack_sweep` places the racetracks + GC
array; :func:`add_racetrack_gc_routes` wires each bus to its coupler pair.
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
from picasso.routing import ObstacleSet

from ..parameters import parameters as _p

# Coupler sim design point (Euler-L-bend geometry): fixed 700 nm gap point coupler
# at the bottom L-bend apex -> kappa^2 = 0.0333; straight-length sweep brackets
# critical coupling at L_s ~ 500 um. (Bend radius is set by the PDK L-bend.)
_L_S: tuple[float, ...] = (100.0, 250.0, 500.0, 1000.0, 1500.0)
_GAP = 0.700

# Layout (um). Each racetrack is rotated 90 deg -> _BUS_LENGTH tall (bus, vertical)
# x (L_s + ~120) wide (loops horizontal). They are stacked vertically and
# LEFT-aligned, so the uncoupled (far) Euler bends line up at a common x while the
# coupling ends (buses) staircase out to the right, _OFFSET apart, for routing.
# A GC array + alignment loop runs along the top, with the stack directly below.
_OFFSET = 100.0  # vertical gap between stacked racetracks (routing lane)
# Racetrack bus length -> rotated device height; trimmed so 5 devices + gaps fit the band.
_BUS_LENGTH = 100.0
_LEFT_MARGIN = 550.0  # stack left edge off the left inner edge (clears test_dc_out_top)
_TOP_MARGIN = 40.0  # coupler tops below the top inner edge
_GC_GAP = 250.0  # vertical gap from the GC row bottom to the racetrack stack top
_GC_PER_RT = 2  # one input + one thru coupler per racetrack


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


def add_racetrack_sweep(cell: fw.Component) -> None:
    """Place the 5-racetrack length sweep (rotated 90 deg) + GC array on R2A.

    Each racetrack is placed ``rotation=90`` (loops horizontal, bus vertical) and
    the five are stacked vertically, **left-aligned** so the uncoupled (far) Euler
    bends line up at ``x0`` while the coupling ends (buses) staircase to the right;
    adjacent devices are ``_OFFSET`` apart (vertical routing lane). Shortest at the
    top. The GC array (``_GC_PER_RT`` per racetrack) + alignment loop runs along the
    top, left-aligned at ``x0``, and the racetrack stack hangs ``_GC_GAP`` directly
    below it. Instances ``racetrack_Ls{L}`` / ``racetrack_gc_array`` /
    ``racetrack_gc_align``. Placement-only (buses not routed to the couplers).
    """
    half_w = _p.die_width.value / 2.0
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx

    x0 = (-half_w + kw) + _LEFT_MARGIN
    y_line = (half_h - kw) - _TOP_MARGIN

    def rt(length: float) -> fw.Component:
        return pdk.cells["racetrack_allpass_rib_sm_800nm"](
            gap=_GAP, straight_length=length, bus_length=_BUS_LENGTH
        )

    device_h = rt(_L_S[0]).bbox.dx  # rotated height = unrotated bus_length

    # GC array + left alignment loop as a horizontal row along the top, left-aligned
    # at x0, coupler tops at y_line.
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(loop, name="racetrack_gc_align", x=x0 - lb.xmin, y=y_line - lb.ymax)
    arr = _gc_line(_GC_PER_RT * len(_L_S))
    ab = arr.bbox
    array_xmin = (x0 + lb.dx) + (pitch - gc_w)
    cell.add_placed(arr, name="racetrack_gc_array", x=array_xmin - ab.xmin, y=y_line - ab.ymax)

    # Racetrack stack directly below the GC row, _GC_GAP beneath the taller element.
    y_stack_top = y_line - max(lb.dy, ab.dy) - _GC_GAP

    # Stack top-down, left-aligned: rotation=90 (CCW) maps rotated bbox.xmin = -b.ymax
    # and rotated bbox.ymin = 0, so placing the origin at (x0 + b.ymax, y_bottom_i)
    # puts every device's left edge (uncoupled bend) at x0.
    for i, length in enumerate(_L_S):
        r = rt(length)
        b = r.bbox
        y_bottom = y_stack_top - device_h - i * (device_h + _OFFSET)
        cell.add_placed(
            r, name=f"racetrack_Ls{length:g}", x=x0 + b.ymax, y=y_bottom, rotation=90.0
        )


def add_racetrack_gc_routes(cell: fw.Component) -> None:
    """Route each racetrack's bus ends to its grating-coupler pair on R2A.

    Racetrack ``i`` (top to bottom, shortest first) takes the GC array's adjacent
    column pair ``c{2i}`` / ``c{2i+1}``. After the 90 deg placement rotation the
    bus is vertical: ``o2`` (thru) sits at the bus **top** facing north, ``o1``
    (input) at the bus **bottom** facing south. The staircase placement puts every
    bus east of all the devices above it, so:

    - ``o2 -> c{2i}``: climbs straight up its bus corridor into the band above the
      stack, then jogs to its coupler.
    - ``o1 -> c{2i+1}``: dips under the bus end, wraps **east** around it, and
      climbs a corridor just east of its own bus (west of the next bus down) into
      the band. Wrapping west instead would trap the line under its own loop
      (the loops extend west, left-aligned, so there is no west corridor).

    Landing order thus matches band-entry order west to east -- the crossing-free
    matching. Ls1000's ``c6`` and Ls1500's ``c8``/``c9`` sit west of their buses,
    so those lines jog back west inside the band; the shared obstacle set nests
    the jogs instead of crossing them.

    **One autoroute call per connection** -- the two bus ports face opposite ways
    (a bundle needs a shared outward heading), and each racetrack's pair lands at
    a different staircase depth. All ten on ``routing_sm_tight`` (the ~100 um
    inter-device lanes and the bus wrap-arounds don't fit the default 100 um bend),
    planned against one shared obstacle set: the five racetrack bodies (a line may
    bend around a device but never through it) plus the ``add_routes`` live rule,
    so later lines bend around earlier ones. Routing order is the nesting order:
    top to bottom, and per racetrack ``o2`` before ``o1`` -- ``o2`` owns the bus
    corridor, and letting ``o1`` go first parks its climb on that corridor, which
    walls ``o2`` in between its own bus and the alignment loop.
    """
    # obs = ObstacleSet(name="racetrack_gc_chain")
    # obs.add_routes(cell)
    # for length in _L_S:
    #     obs.add_instance(cell.instances[f"racetrack_Ls{length:g}"])
    # for i, length in enumerate(_L_S):
    #     rt_name = f"racetrack_Ls{length:g}"
    #     for j, port in enumerate(("o2", "o1")):
    #         cell.autoroute(
    #             ports_a=[(rt_name, port)],
    #             ports_b=[("racetrack_gc_array", f"o1_r0_c{_GC_PER_RT * i + j}")],
    #             obstacles=obs,
    #             spec="routing_sm_tight",
    #             strategy="grid_astar",
    #             step=10.0,
    #             end_straight=60.0,
    #             name=f"{rt_name}_gc_{port}",
    #         )
