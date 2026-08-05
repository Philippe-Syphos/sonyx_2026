"""Waveguide-crossing insertion-loss cutback cells (R2A) -- placement-only.

Cascade-length cutback for waveguide crossings: three chains of ``N`` crossings
abutted in series (``N`` in :data:`_COUNTS`), so a log-linear fit of transmission
vs ``N`` gives the **per-crossing insertion loss** (slope) with the coupler +
lead loss absorbed in the intercept (``N = 0``). Two topologies, using the
nominal FEM-calibrated PDK crossing cells:

- ``crossing_cutback_mmi`` -- the MMI ("+") crossing (``crossing_mmi_rib_sm_800nm``).
- ``crossing_cutback_tapered`` -- the direct tapered crossing
  (``crossing_tapered_rib_sm_800nm``).

Each cell mirrors the waveguide-cutback idiom (``test_cells_die_r1a._build_cutback``):
chains laid horizontally, stacked vertically and left-aligned; a horizontal GC
array (two couplers per chain) on top; and a GC alignment loop one pitch to the
**left** of the array. The through path (o1->o2) is chained; the transverse arms
(o3/o4) are open stubs. The chain **west** ends are wired to the three westmost
couplers (see :func:`_route_west_couplers`); the east ends are not routed yet.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from picasso.leaves import make_array, make_straight
from picasso.recipe import recipe
from picasso.routing import ObstacleSet

from ..parameters import parameters as _p

# Cascade lengths (number of crossings in series) -- the cutback lever arm.
_COUNTS: tuple[int, ...] = (10, 30, 60)
_CHAIN_STACK_GAP = 120.0  # um, vertical gap between adjacent stacked chains
_COUPLER_ROW_GAP = 200.0  # um, gap from the GC array bottom to the chain stack top
_CHAIN_DROP = 40.0  # um, extra downward shift of the chain stack (widens the gap)

# Placement on R2A: both blocks sit to the right of the racetrack sweep, MMI on
# top and tapered below. The left margin clears the widest racetrack (which ends
# ~2.2 mm right of the left inner edge); the top line matches the racetracks'.
_BLOCK_LEFT_MARGIN = 2550.0  # stack left edge off the left inner edge
_BLOCK_TOP_MARGIN = 140.0  # GC tops below the top inner edge
_BLOCK_GAP = 150.0  # vertical gap between the MMI (top) and tapered (bottom) blocks


def _route_couplers(cell: fw.Component) -> None:
    """Wire every chain end to a grating coupler -- **one autoroute call per side**.

    Each side is a single bundle: the three ports share an outward heading (west
    ``o1`` / east ``o2``) and the three couplers share an inward heading (north),
    which is what lets one call serve all three chains. Both bundles converge on
    the band between the chain stack and the GC row and peel off into their
    couplers from below:

    - **west** (``o1`` -> ``c0``/``c1``/``c2``): west out of the stack, north up
      a corridor left of ``x = 0``, then east along the band.
    - **east** (``o2`` -> ``c5``/``c4``/``c3``): east out of the stack, north up
      a corridor right of the chain ends, then a long west haul along the band.

    Lane order is the crossing-free one on both sides, and it falls out of the
    turn geometry. West->north->east is two right turns and east->north->west is
    two left turns; either way the **southmost** port (the longest chain,
    ``_COUNTS[-1]``) rides the outside of both turns and ends up the northmost
    lane -- closest to the GC row, so it peels off first. Going east the first
    coupler reached is ``c0``; going west it is ``c5``. So bottom-to-top chains
    map outward-in on both sides, and each chain gets a **nested** coupler pair::

        chain_n60: c0 <-> c5      chain_n30: c1 <-> c4      chain_n10: c2 <-> c3

    (Not adjacent pairs -- adjacent pairing would force the lanes to cross. All
    six sit on one ``grating_coupling_pitch_for_tests`` row, so a 6-fibre array
    still lands the whole block in one placement.)

    Lanes run on ``routing_sm_tight``: three nested turns of the default 100 um
    bend don't fit the band. The east targets (``x >= 401``) all sit east of the
    west bundle's reach (``x <= 285``), so the two bundles share the band without
    contending for it -- ``add_routes`` on the shared obstacle set keeps the east
    lanes off the west ones regardless. Other obstacles: the three chain bodies
    (a lane may bend around a chain, never through it), the coupler array, and
    the alignment loop, which walls off the far-west corridor above its bottom
    edge and forces the west bundle's eastward runs into the band beneath it.
    """
    obs = ObstacleSet(name="crossing_cutback_gc")
    obs.add_routes(cell)  # live rule: the east bundle bends around the west one
    for n in _COUNTS:
        obs.add_instance(cell.instances[f"chain_n{n}"])
    obs.add_instance(cell.instances["couplers"])
    obs.add_instance(cell.instances["gc_align"])
    # Chains bottom-to-top on both sides; couplers outward-in (west 0,1,2 /
    # east 5,4,3) so the bundles nest instead of crossing. West first -- it owns
    # the inner band, and the east haul has the whole band width to nest under.
    ncnt = len(_COUNTS)
    for side, port, cols in (
        ("west", "o1", range(ncnt)),
        ("east", "o2", range(2 * ncnt - 1, ncnt - 1, -1)),
    ):
        cell.autoroute(
            ports_a=[(f"chain_n{n}", port) for n in reversed(_COUNTS)],
            ports_b=[("couplers", f"o1_r0_c{i}") for i in cols],
            obstacles=obs,
            spec="routing_sm_tight",
            strategy="vgraph_rect",
            name=f"{side}_gc_bundle",
        )


@recipe
def _crossing_chain(crossing_name: str, n: int, total_len: float) -> fw.Component:
    """``n`` ``crossing_name`` crossings abutted (o2->o1) + an output straight pad.

    The pad (``rib_sm_800nm`` straight) lengthens the east end so the device spans
    exactly ``total_len`` (um) regardless of ``n`` -- every chain then presents
    ``o1`` (west) and ``o2`` (east) at the **same x**, so the routing to the
    couplers is identical for every count and the SM propagation loss is common-
    mode. The transverse arms (o3/o4) are open stubs. Ports ``o1`` / ``o2`` on
    ``rib_sm_800nm``.
    """
    cell = fw.Component()
    first = cell.add_placed(pdk.cells[crossing_name](), name="x0")
    prev = first
    for i in range(1, n):
        prev = cell.put(
            pdk.cells[crossing_name](), (prev.name, "o2"), port_to="o1", name=f"x{i}"
        )
    pad_len = total_len - n * pdk.cells[crossing_name]().bbox.dx
    east = prev
    if pad_len > 1e-6:
        east = cell.put(
            make_straight(length=pad_len, cross_section="rib_sm_800nm"),
            (prev.name, "o2"),
            port_to="o1",
            name="pad",
        )
    cell.add_port("o1", first.ports["o1"])
    cell.add_port("o2", east.ports["o2"])
    return cell


def _build_crossing_cutback(crossing_name: str) -> fw.Component:
    """Assemble a crossing cutback cell for ``crossing_name`` (see module docstring)."""
    pitch = _p.grating_coupling_pitch_for_tests.value
    cell = fw.Component()

    # Common device length = the longest chain's crossing run, so every chain is
    # padded (output straight) to the same span -> identical routing + common-mode
    # SM propagation loss across counts.
    w = pdk.cells[crossing_name]().bbox.dx
    total_len = max(_COUNTS) * w

    # Chains: horizontal, stacked vertically, left edges aligned at x=0. The top
    # chain's top edge starts _CHAIN_DROP below y=0 (couplers sit above y=0); the
    # stack grows downward. Shortest chain at the top.
    y_cursor = -_CHAIN_DROP  # top edge of the next chain
    for n in _COUNTS:
        chain = _crossing_chain(crossing_name, n, total_len)
        b = chain.bbox
        cell.add_placed(chain, name=f"chain_n{n}", x=-b.xmin, y=y_cursor - b.ymax)
        y_cursor -= b.dy + _CHAIN_STACK_GAP

    # Grating-coupler array (horizontal row, facet south), two couplers per chain,
    # left edge at x=0, _COUPLER_ROW_GAP above y=0.
    arr = make_array(
        template=gratingcoupler_rib_sm_800nm_ext(),
        rows=1,
        cols=2 * len(_COUNTS),
        dx=pitch,
        dy=0.0,
    )
    ab = arr.bbox
    cell.add_placed(arr, name="couplers", x=-ab.xmin, y=_COUPLER_ROW_GAP - ab.ymin)

    # Alignment loop one pitch to the left of the array, GC tops on the same line.
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(
        loop,
        name="gc_align",
        x=-(pitch - gc_w) - lb.xmax,
        y=(_COUPLER_ROW_GAP + ab.dy) - lb.ymax,
    )

    # Fibre I/O: chain o1 -> the 3 west couplers, o2 -> the 3 east ones (1 call each).
    _route_couplers(cell)
    return cell


@recipe
def crossing_cutback_mmi() -> fw.Component:
    """MMI-crossing insertion-loss cutback (3 chains, N in ``_COUNTS``). See module docstring."""
    return _build_crossing_cutback("crossing_mmi_rib_sm_800nm")


@recipe
def crossing_cutback_tapered() -> fw.Component:
    """Tapered-crossing insertion-loss cutback (3 chains, N in ``_COUNTS``). See module."""
    return _build_crossing_cutback("crossing_tapered_rib_sm_800nm")


def add_crossing_cutbacks(cell: fw.Component) -> None:
    """Place the MMI (top) and tapered (bottom) crossing cutback blocks on R2A.

    Both blocks are left-aligned ``_BLOCK_LEFT_MARGIN`` off the left inner edge
    (clearing the racetrack sweep), the MMI block's GC tops ``_BLOCK_TOP_MARGIN``
    below the top inner edge and the tapered block ``_BLOCK_GAP`` beneath it.
    Instances ``cutback_mmi`` / ``cutback_tapered``. Each block carries its own
    west-half fibre routing (see :func:`_route_west_couplers`); the chain east
    ends are still unrouted.
    """
    half_w = _p.die_width.value / 2.0
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    x_left = (-half_w + kw) + _BLOCK_LEFT_MARGIN
    y_top = (half_h - kw) - _BLOCK_TOP_MARGIN

    mmi = crossing_cutback_mmi()
    mb = mmi.bbox
    cell.add_placed(mmi, name="cutback_mmi", x=x_left - mb.xmin, y=y_top - mb.ymax)

    tap = crossing_cutback_tapered()
    tb = tap.bbox
    y_top_tap = (y_top - mb.dy) - _BLOCK_GAP
    cell.add_placed(tap, name="cutback_tapered", x=x_left - tb.xmin, y=y_top_tap - tb.ymax)
