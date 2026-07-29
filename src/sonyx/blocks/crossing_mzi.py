"""Balanced-bridge crossing crosstalk MZIs (R3A) -- geometry-variation sweep.

The "MZI #2" balanced bridge: two crossings act as the couplers of a Mach-
Zehnder, wired with the through/cross **swap** so each arm carries exactly one
through-transit and one cross-transit (``X1.o2 -> X2.o4`` and ``X1.o3 -> X2.o1``,
input ``X1.o1``, outputs ``X2.o2`` balanced and ``X2.o3`` carrier, ``X1.o4``
open). Both arms are symmetric 3-bend Euler routes (matched bend count) with a
deliberate length imbalance ``DL`` -- the through arm rises ``_ARM_UP`` and the
cross arm returns ``_ARM_DN`` (after a short ``_CROSS_DIP`` first leg), so
``DL = 2*(_ARM_UP - _ARM_DN)`` -- and a wavelength sweep traces the fringe. The
crosstalk is read from the balanced-port / carrier-port ratio, immune to common-
mode loss; the small differential arm loss enters only as a fractional error.

Two test-cell blocks on R3A, each with its own GC array + alignment loop:

- **MMI block (top)** -- three bridges sweeping the MMI bar length
  (``length_scale`` in :data:`_MMI_LENGTH_SCALES`, detuning the self-imaging).
- **Tapered block (below)** -- three bridges sweeping the tapered collimation
  factor (``m`` in :data:`_TAPERED_M`, the widened-width sweet spot).

Placement-only at the die level: the device ports are routed to the couplers in a
later step.
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
from picasso.routing import resolve_routes
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

# Geometry-variation sweeps (BOE): MMI imaging-length detuning, tapered m.
_MMI_LENGTH_SCALES: tuple[float, ...] = (0.9, 1.0, 1.1)
_TAPERED_M: tuple[float, ...] = (3.0, 4.0, 5.0)

# Placement on R3A (top-left band): two stacked blocks, each three cells side by
# side with a GC array + alignment loop above.
_BLOCK_LEFT_MARGIN = 200.0  # off the left inner edge (was 100; +100 to clear overlap)
_BLOCK_TOP_MARGIN = 40.0
_BLOCK_CELL_GAP = 140.0  # horizontal gap between cells in a block
_GC_ROW_GAP = 120.0  # gap from a GC array to its cell row
_BLOCK_GAP = 250.0  # vertical gap between the MMI (top) and tapered (bottom) blocks


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
    cell.add_port("out_bal", x2.ports["o2"])
    cell.add_port("out_car", x2.ports["o3"])
    resolve_routes(cell)  # materialise geometry so the placed bbox is correct
    cell.cell_type = "test_mzi"
    cell.calibration_status = "PLACEHOLDER"
    cell.parameters.arm_length_imbalance_um = 2.0 * (_ARM_UP - _ARM_DN)
    return cell


@recipe
def crossing_mzi_mmi(length_scale: float = 1.0) -> fw.Component:
    """Balanced-bridge crosstalk MZI with MMI crossings at ``length_scale``."""
    return _balanced_bridge(pdk.cells["crossing_mmi_rib_sm_800nm"](length_scale=length_scale))


@recipe
def crossing_mzi_tapered(m: float = 4.0) -> fw.Component:
    """Balanced-bridge crosstalk MZI with tapered crossings at collimation ``m``."""
    return _balanced_bridge(pdk.cells["crossing_tapered_rib_sm_800nm"](m=m))


def _place_block(
    cell: fw.Component,
    prefix: str,
    named_cells: list[tuple[str, fw.Component]],
    x_left: float,
    y_top: float,
) -> float:
    """Place a GC array + alignment loop (tops at ``y_top``) over a row of cells.

    Cells are laid left to right from ``x_left``, tops aligned below the GC row.
    Returns the block's bottom y (for stacking the next block beneath it).
    """
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(loop, name=f"{prefix}_gc_align", x=x_left - lb.xmin, y=y_top - lb.ymax)
    arr = make_array(
        template=gratingcoupler_rib_sm_800nm_ext(),
        rows=1,
        cols=3 * len(named_cells),
        dx=pitch,
        dy=0.0,
    )
    ab = arr.bbox
    array_xmin = (x_left + lb.dx) + (pitch - gc_w)
    cell.add_placed(arr, name=f"{prefix}_gc_array", x=array_xmin - ab.xmin, y=y_top - ab.ymax)

    # MZIs start at the GC array's left edge -> to the right of the alignment loop.
    mzi_top = (y_top - max(lb.dy, ab.dy)) - _GC_ROW_GAP
    x_cursor = array_xmin
    max_h = 0.0
    for name, comp in named_cells:
        b = comp.bbox
        cell.add_placed(comp, name=name, x=x_cursor - b.xmin, y=mzi_top - b.ymax)
        x_cursor += b.dx + _BLOCK_CELL_GAP
        max_h = max(max_h, b.dy)
    return mzi_top - max_h


def add_crossing_mzis(cell: fw.Component) -> None:
    """Place the MMI (top) and tapered (bottom) crosstalk-MZI variation blocks on R3A.

    Each block is three balanced bridges (geometry sweep) side by side with its own
    GC array + alignment loop, top-left band. Placement only (device ports not
    routed to the couplers).
    """
    half_w = _p.die_width.value / 2.0
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    x_left = (-half_w + kw) + _BLOCK_LEFT_MARGIN
    y_top = (half_h - kw) - _BLOCK_TOP_MARGIN

    mmi_cells = [
        (f"crossing_mzi_mmi_s{round(s * 100):d}", crossing_mzi_mmi(length_scale=s))
        for s in _MMI_LENGTH_SCALES
    ]
    block_bottom = _place_block(cell, "crossing_mzi_mmi", mmi_cells, x_left, y_top)

    tapered_cells = [
        (f"crossing_mzi_tapered_m{round(m * 10):d}", crossing_mzi_tapered(m=m))
        for m in _TAPERED_M
    ]
    _place_block(cell, "crossing_mzi_tapered", tapered_cells, x_left, block_bottom - _BLOCK_GAP)
