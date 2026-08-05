"""Balanced-bridge crossing crosstalk MZIs (R3B) -- geometry-variation sweep.

The "MZI #2" balanced bridge: two crossings act as the couplers of a Mach-
Zehnder, wired with the through/cross **swap** so each arm carries exactly one
through-transit and one cross-transit (``X1.o2 -> X2.o4`` and ``X1.o3 -> X2.o1``,
inputs ``X1.o1`` / ``X1.o4``, outputs ``X2.o2`` balanced and ``X2.o3``
carrier). Both arms are symmetric 3-bend Euler routes (matched bend count) with a
deliberate length imbalance ``DL`` -- the through arm rises ``_ARM_UP`` and the
cross arm returns ``_ARM_DN`` (after a short ``_CROSS_DIP`` first leg), so
``DL = 2*(_ARM_UP - _ARM_DN)`` -- and a wavelength sweep traces the fringe. The
crosstalk is read from the balanced-port / carrier-port ratio, immune to common-
mode loss; the small differential arm loss enters only as a fractional error.

Four test-cell blocks on R3B in **two rows**, each a single bridge with
**its own** GC array (``_GC_PER_MZI`` couplers) and alignment loop:

- **top row -- MMI variations** -- three bridges sweeping the MMI bar length
  (``length_scale`` in :data:`_MMI_LENGTH_SCALES`, detuning the self-imaging).
- **bottom row -- tapered** -- a single bridge on the vendored Sonyx tapered
  crossing (fixed geometry -- the old collimation-``m`` sweep has no knob left
  to sweep).

One crossing family per row. Both rows share the same left margin and block
pitch, so the tapered block lines up under the first MMI column.

:func:`add_crossing_mzis` is placement; :func:`add_crossing_mzi_gc_routes` wires all
four bridge ports (both X1 inputs and both X2 outputs) to that block's four grating
couplers, one coupler per port.
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
from picasso.routing.spec import RoutingSpec

from ..parameters import parameters as _p

# Bridge arms are manually routed with the PDK Euler L-bend (no default_bend on xs).
_SPEC = RoutingSpec(bend="lbend_rib_sm_800nm")

# Bridge geometry (um). X2 sits _BRIDGE_DX right of X1, its y chosen so the cross
# arm's first leg out of X1.o3 is exactly _CROSS_DIP (keeps the cell compact). Both
# arms are symmetric 3-bend paths (matched bend count): the through arm rises
# _ARM_UP, the cross arm returns _ARM_DN -> imbalance DL = 2*(_ARM_UP - _ARM_DN).
_BRIDGE_DX = 260.0
_ARM_UP = 180.0
_ARM_DN = 110.0
_ARM_EB = 110.0  # cross-arm middle (east) leg
_CROSS_DIP = 75.0  # visible straight out of X1.o3
_BEND_SETBACK = 50.0  # Euler L-bend corner setback consumed per leg (o2 at (50, 50))

# Geometry-variation sweep (BOE): MMI imaging-length detuning. The tapered
# crossing is vendored fixed geometry -- one block, no sweep.
_MMI_LENGTH_SCALES: tuple[float, ...] = (0.9, 1.0, 1.1)

# Instance / cell names, one per variation -- the single source of truth shared by
# the placement pass and the routing pass (which addresses blocks by name only).
_MMI_ROW: tuple[str, ...] = tuple(
    f"crossing_mzi_mmi_s{round(s * 100):d}" for s in _MMI_LENGTH_SCALES
)
_TAPERED_ROW: tuple[str, ...] = ("crossing_mzi_tapered",)

# Placement on R3B (top band): six self-contained blocks in two rows of three (MMI
# on top, tapered below), each one MZI under its own GC array + alignment loop.
_BLOCK_LEFT_MARGIN = 200.0  # off the left inner edge (was 100; +100 to clear overlap)
_BLOCK_TOP_MARGIN = 40.0
_BLOCK_CELL_GAP = 140.0  # horizontal gap between adjacent blocks
_BLOCK_ROW_GAP = 150.0  # vertical gap between the MMI row and the tapered row
_GC_ROW_GAP = 120.0  # gap from a GC array to its MZI
# Couplers per block, one per bridge port: the two inputs on X1 (in / in_2) and the
# two outputs on X2 (balanced / carrier). All four are wired by
# add_crossing_mzi_gc_routes -- no spares.
_GC_PER_MZI = 4


def _balanced_bridge(crossing: fw.Component) -> fw.Component:
    """Balanced-bridge crosstalk MZI using ``crossing`` at both couplers (see module)."""
    w = crossing.bbox.dx
    h = crossing.bbox.dy
    # First cross-arm leg = the desired visible straight + the bend's corner setback,
    # and X2's y is set so that leg lands the cross arm on X2.o1.
    cross_first = _CROSS_DIP + _BEND_SETBACK
    bridge_dy = -h / 2.0 - cross_first + _ARM_DN
    cell = fw.Component()
    x1 = cell.add_placed(crossing, name="x1", x=0.0, y=0.0)
    x2 = cell.add_placed(crossing, name="x2", x=_BRIDGE_DX, y=bridge_dy)
    half = (_BRIDGE_DX - w / 2.0) / 2.0
    # Through arm: X1.o2 (east) up and over into X2.o4 (from the north).
    cell.route(
        (x1.name, "o2"),
        (x2.name, "o4"),
        waypoints=[(half, 0.0), (0.0, _ARM_UP), (half, 0.0)],
        spec=_SPEC,
        name="arm_through",
    )
    # Cross arm: X1.o3 (south) -> _CROSS_DIP visible straight -> east -> up _ARM_DN
    # into X2.o1 (from the west). Matched 3-bend; DL = 2*(_ARM_UP - _ARM_DN).
    cell.route(
        (x1.name, "o3"),
        (x2.name, "o1"),
        waypoints=[(0.0, -cross_first), (_ARM_EB, 0.0), (0.0, _ARM_DN)],
        spec=_SPEC,
        name="arm_cross",
    )
    cell.add_port("in", x1.ports["o1"])
    # X1's second free port (o4, facing north) -- the bridge's other input, fed from
    # its own grating coupler so the bar-state response can be measured too.
    cell.add_port("in_2", x1.ports["o4"])
    cell.add_port("out_bal", x2.ports["o2"])
    cell.add_port("out_car", x2.ports["o3"])
    # No resolve_routes() needed: the two arm routes above are lowered eagerly at
    # their route() call, so the placed bbox is already correct here.
    cell.cell_type = "test_mzi"
    cell.calibration_status = "PLACEHOLDER"
    cell.parameters.arm_length_imbalance_um = 2.0 * (_ARM_UP - _ARM_DN)
    return cell


@recipe
def crossing_mzi_mmi(length_scale: float = 1.0) -> fw.Component:
    """Balanced-bridge crosstalk MZI with MMI crossings at ``length_scale``."""
    return _balanced_bridge(pdk.cells["crossing_mmi_rib_sm_800nm"](length_scale=length_scale))


@recipe
def crossing_mzi_tapered() -> fw.Component:
    """Balanced-bridge crosstalk MZI with the vendored (fixed) tapered crossings."""
    return _balanced_bridge(pdk.cells["crossing_tapered_rib_sm_800nm"]())


def _place_block(
    cell: fw.Component,
    prefix: str,
    name: str,
    comp: fw.Component,
    x_left: float,
    y_top: float,
) -> tuple[float, float]:
    """Place **one** MZI with its own GC array + alignment loop (tops at ``y_top``).

    The block is a ``_GC_PER_MZI``-coupler array (tops at ``y_top``) with an
    alignment loop one pitch to its west, and the MZI ``_GC_ROW_GAP`` below,
    left-aligned to the array. Returns the block's ``(width, height)``, so the caller
    can step ``x_left`` to the next block and ``y_top`` down to the next row.
    """
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(loop, name=f"{prefix}_gc_align", x=x_left - lb.xmin, y=y_top - lb.ymax)
    arr = make_array(
        template=gratingcoupler_rib_sm_800nm_ext(),
        rows=1,
        cols=_GC_PER_MZI,
        dx=pitch,
        dy=0.0,
    )
    ab = arr.bbox
    array_xmin = (x_left + lb.dx) + (pitch - gc_w)
    cell.add_placed(arr, name=f"{prefix}_gc_array", x=array_xmin - ab.xmin, y=y_top - ab.ymax)

    # MZI starts at the GC array's left edge -> to the right of the alignment loop.
    mzi_top = (y_top - max(lb.dy, ab.dy)) - _GC_ROW_GAP
    b = comp.bbox
    cell.add_placed(comp, name=name, x=array_xmin - b.xmin, y=mzi_top - b.ymax)
    width = max((array_xmin + ab.dx) - x_left, (array_xmin + b.dx) - x_left)
    return width, y_top - (mzi_top - b.dy)


def add_crossing_mzis(cell: fw.Component) -> None:
    """Place the four crosstalk-MZI blocks on R3B, in two rows.

    Each variation is its **own** block -- one balanced bridge under its own
    ``_GC_PER_MZI``-coupler GC array plus alignment loop. The three **MMI**
    variations fill the top row (tops ``_BLOCK_TOP_MARGIN`` below the keep-out inner
    north wall) and the single **tapered** block sits the row ``_BLOCK_ROW_GAP``
    below it, each row laid left to right from the same ``_BLOCK_LEFT_MARGIN``.
    Splitting the families into their own rows halves the band's width -- a
    single row ran east under the SSM cutback cell.

    Placement only; :func:`add_crossing_mzi_gc_routes` adds the input routes.
    """
    half_w = _p.die_width.value / 2.0
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    x_left = (-half_w + kw) + _BLOCK_LEFT_MARGIN
    y_top = (half_h - kw) - _BLOCK_TOP_MARGIN

    rows = (
        [
            (name, crossing_mzi_mmi(length_scale=s))
            for name, s in zip(_MMI_ROW, _MMI_LENGTH_SCALES, strict=True)
        ],
        [(name, crossing_mzi_tapered()) for name in _TAPERED_ROW],
    )
    # The cell name doubles as the instance prefix, so each block's couplers and
    # alignment loop get unique instance names.
    for row in rows:
        x_cursor = x_left
        row_height = 0.0
        for name, comp in row:
            width, height = _place_block(cell, name, name, comp, x_cursor, y_top)
            x_cursor += width + _BLOCK_CELL_GAP
            row_height = max(row_height, height)
        y_top -= row_height + _BLOCK_ROW_GAP


def add_crossing_mzi_gc_routes(cell: fw.Component) -> None:
    """Wire every crosstalk-MZI block's four ports to its own four grating couplers.

    One line per port. The two **inputs** take the two west couplers in x order; the
    two **outputs** take the east pair in the *reverse* order, because ``c2`` sits
    directly over the through arm's top leg and so can only be reached from *above*
    the block:

    ==================  ==========  ==============================================
    coupler             port        geometry
    ==================  ==========  ==============================================
    ``o1_r0_c0``        ``in``      ``x1.o1``, facing **west**: the coupler sits
                                    east of it, so the line drops south past the
                                    port's level, hooks west around the block's
                                    left edge and comes back east into it.
    ``o1_r0_c1``        ``in_2``    ``x1.o4``, facing **north**: climbs straight out
                                    of the block, then east and back north.
    ``o1_r0_c2``        ``out_bal`` ``x2.o2``, the balanced output, facing **east**:
                                    east out of the block, north up the **inner**
                                    eastern lane, then back west over the block top
                                    into ``c2``.
    ``o1_r0_c3``        ``out_car`` ``x2.o3``, the carrier output, facing **south**
                                    -- away from the couplers -- so it dips below
                                    the block and climbs the **outer** eastern lane,
                                    outside ``out_bal``, to ``c3``.
    ==================  ==========  ==============================================

    All four on ``routing_sm_tight`` (the small-radius Euler L-bend): the lines turn
    inside the ~85 um channel west of the block and the ~180 um band between the block
    top and the coupler array, neither of which fits the default bend.

    **One autoroute call per connection** -- four per block, sixteen in all. The
    four target ports point four different ways (west / north / south / east) and a
    bundle needs every lane to share an outward heading, so they cannot be grouped; the
    four blocks are separate cells hundreds of um apart with no shared trunk either.
    Every line is planned against one shared obstacle set holding all four bridge cells
    plus the ``add_routes`` live rule, so a line bends around the devices and around
    whatever has already been routed rather than merging with it.

    The table is also the **routing order**, west to east, and it matters:

    - ``in_2`` before ``in``: it is the more boxed-in of the pair -- on the narrow
      tapered crossings ``x1.o4`` sits only ~11 um from ``x1.o1``, against ~36 um on
      the MMI ones -- and routing ``in`` first merges the two input legs on every
      tapered block (~70-180 um² of shared WG_RIB).
    - ``out_bal`` before ``out_car``: ``out_bal`` needs the inner lane up the block's
      east side, leaving ``out_car`` the outer one out to ``c3``. The other way round
      ``out_car`` takes the inner lane and ``out_bal`` is walled in on the narrowest
      tapered block (``no sightline path to the goal gateway``).
    """
    # (coupler, port), in routing order -- see the docstring table.
    lines = (
        ("o1_r0_c1", "in_2"),
        ("o1_r0_c0", "in"),
        ("o1_r0_c2", "out_bal"),
        ("o1_r0_c3", "out_car"),
    )
    # One obstacle set for the whole pass: every bridge cell (a line may bend around a
    # device but never through it) plus the add_routes live rule, which picks up each
    # route as it materialises so later lines avoid earlier ones. The live rule tracks
    # the scene per-child and cached -- re-extracting each finished route's polygons by
    # hand instead costs minutes of build time on this die.
    obs = ObstacleSet(name="crossing_mzi_gc_chain")
    obs.add_routes(cell)
    for name in _MMI_ROW + _TAPERED_ROW:
        obs.add_instance(cell.instances[name])
    for name in _MMI_ROW + _TAPERED_ROW:
        for coupler, port in lines:
            cell.autoroute(
                ports_a=[(f"{name}_gc_array", coupler)],
                ports_b=[(name, port)],
                obstacles=obs,
                spec="routing_sm_tight",
                strategy="vgraph_euclid",
                name=f"{name}_gc_{port}",
            )
