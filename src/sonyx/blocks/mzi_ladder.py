"""Unbalanced-MZI n_eff / n_g calibration ladder for R4B (placement only).

Places the unbalanced-MZI PCM ladder from
``pdk-luqia-ln200/docs/luqia_pdk_unbalanced_mzi_pcm_boe.md`` onto a die: the
three-rung ΔL ladder (A/B/C = 27.5 / 55 / 275 µm) in **both** waveguide
orientations -- ``unbalanced_mzi_rib_sm_800nm_ord`` (E-W) and
``..._ext`` (N-S) -- so six MZIs total, laid west→east as the ``_ord`` trio
then the ``_ext`` trio.

Each orientation is grouped along its own waveguide axis, which is what makes it
routable. The ``_ord`` rungs are E-W, so their ports face west and east: they
**stack vertically** (A top, B middle, C bottom), giving one column of west ports
and one of east ports. The ``_ext`` rungs are N-S, their ports facing south and
north, so stacking them would put both port sets at three different heights with
no common band to bundle in -- they sit in a **single row** west->east instead.
Every ext rung is the same height, so a row lands all three ``o1`` on one line and
all three ``o2`` on another. (A single six-tall column doesn't fit either way:
R4B's usable band is only the strip above the full-width modulators.)

The fibre I/O is **two grating-coupler arrays** at the constant
``grating_coupling_pitch_for_tests`` pitch (one per group), built from
``gratingcoupler_rib_sm_800nm_ext`` (N-S, fibre input from the north) and sitting
on a common horizontal line north of both groups.

Both groups are fully wired to their arrays, one bundle per side -- four in all,
each rung getting a nested coupler pair (``c0<->c5`` / ``c1<->c4`` / ``c2<->c3``
on the ord column; ``A: c0<->c5``, ``B: c1<->c4``, ``C: c2<->c3`` on the ext row).

The whole ladder is one self-contained Component (:func:`mzi_ladder_block`)
built in its own local frame -- origin at the ord column's centre x and the
GC-line centre y. The die (``dies/die_r4b.py``) abuts that single instance
against the paperclip block with ``add_aligned``; nothing here knows die
coordinates.
"""

from __future__ import annotations

from itertools import pairwise

import picasso as fw
from luqia_ln200 import pdk
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from picasso.leaves import make_array
from picasso.recipe import recipe
from picasso.routing import ObstacleSet
from picasso.routing.obstacles import route_element_bboxes_for_child

from ..parameters import parameters as _p

# ΔL ladder (label, imbalance in um) -- the A/B/C rungs from the design note.
_LADDER: tuple[tuple[str, float], ...] = (("A", 27.5), ("B", 55.0), ("C", 275.0))

# Layout knobs (um).
_ORD_STACK_GAP = 20.0  # vertical bbox-to-bbox gap between stacked MZIs (ord column)
_COL_GAP = 500.0  # horizontal bbox-to-bbox gap between the ord column and the ext row
# Ext rungs sit in a single **row**, not a vertical stack. Stacked, their N-S ports
# ended up at three different heights on both sides, which left no common band to
# bundle in; in a row -- since every ext rung is the same height, with o1 at local
# (0, 0) and o2 directly above -- both port sets come out co-linear in y, one clean
# bundle per side. Bbox-to-bbox gap between adjacent rungs; kept modest because the
# o1 lanes leave *south*, under the row, rather than between the devices.
_EXT_ROW_GAP = 60.0
# Vertical gap from the coupler port line down to the ext row's o2 (north) ports.
# This band carries the whole ext group's routing -- the o2 fan-in from the ~470 um
# device spacing to the 127 um coupler pitch, plus the o1 lanes coming back up
# around the row -- so it is deliberately generous. It costs nothing: the row is
# ~880 um shallower than the stack it replaces, and the ord column still sets the
# block's bottom edge.
_EXT_ROW_GC_GAP = 400.0
# y-anchor within the block (local y = 0 is the GC-line centre):
_GC_TO_STACK = 350.0  # top (A) MZI centre below the GC line

# Forced first leg (um) along each MZI port's own heading, before the pathfinder's
# first vertex, on the ord column's fibre-I/O bundles. Required on both sides: with
# the default the planner lands a ~10 um segment between two corners, which the
# Euler L-bend cannot absorb, and rejects the bundle. The leg gives that first corner
# room. Unlike the heater_cr / paperclip blocks, no bbox_margin bump is needed --
# every coupler this column targets sits within a pitch of its port column, so the
# 50 um default window already covers the turns.
_ORD_GC_START_STRAIGHT = 40.0

# Search-window inflation (um) for the ext o1 bundle -- the one bundle whose path
# leaves its own endpoint bbox, since the o1 ports face south and loop around the
# row's east end to reach the coupler line (see add_mzi_ext_input_routes). The
# excursion is ~450 um east and ~140 um south of the bbox; 800 covers both with
# margin (1200 gives identical geometry).
_EXT_IN_BBOX_MARGIN = 800.0


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


def add_mzi_ext_output_routes(cell: fw.Component) -> None:
    """Bundle-route the ext row's outputs (``o2``, north) to its three westmost couplers.

    **One autoroute call.** The ext rungs are N-S, so ``o2`` already faces north --
    straight at the coupler line, whose ports face south. Source and target headings
    are therefore the *same* (north), which makes this a pure lateral translation
    rather than the two-turn L the ord column and the E-W blocks needed: each lane
    lifts off its ``o2``, shifts sideways inside the ``_EXT_ROW_GC_GAP`` band, and
    drops into its coupler.

    Lane order is consequently a different rule: **order-preserving**, west to west.
    With no turns to ride the outside of, the only way three parallel lanes avoid
    crossing is to keep their left-to-right order, so the row pairs west-to-east
    against ``c0``/``c1``/``c2``: ``A -> c0``, ``B -> c1``, ``C -> c2``. (The
    outward-in nesting the other blocks use would reverse the order and cross every
    lane.) The lanes *converge* doing it -- ``A`` shifts ~141 um east while ``B`` and
    ``C`` shift ~142 and ~536 um west -- because the row spans ~930 um port-to-port
    and the coupler triple only ~254 um.

    ``fan_in`` is what absorbs that convergence. Without it the lanes have to morph
    at the centreline corners, and packing ~756 um of it into the band puts two
    segments broadside to each other ("centreline self-clearance violation"); an
    explicit fan-in component gathers the lanes pre-A* instead, so A* only routes
    the cohesive section.

    It has to be **pinned**, though -- bare ``fan_in=True`` (and ``"centre"``) leaves
    lane 1 a 36.7 um gather move, too short to lower into a bend, and that lane is
    dropped. ``"left"`` pins the fan's cohesive-side landing so the **leftmost** lane
    (``A -> c0``) rides straight through the corridor with no staircase bends, which
    gives the lane closest to the ext alignment loop the cleanest path. ``"right"``
    and floats >= 100 um also resolve it, to identical geometry.

    With the fan doing the gathering, ``grid_astar`` handles the rest -- same planner
    as the ord bundles, no per-strategy departure needed. (``vgraph_euclid`` or
    ``fan_out`` clear the violation too, but the fan-out variants detour west to
    x ~2865 under the ext alignment loop instead of staying in the row's own span.)

    ``routing_sm_tight`` by request -- the band is 400 um and the convergence is
    lateral, so the tight Euler L-bend's smaller radius is what keeps the three
    lanes' turns from stacking up.
    """
    labels = [label for label, _ in _LADDER]  # A (west) .. C (east)
    cell.autoroute(
        ports_a=[(f"mzi_ext_{label}", "o2") for label in labels],  # west -> east
        ports_b=[("mzi_gc_array_ext", f"o1_r0_c{k}") for k in range(len(labels))],
        obstacles=_ladder_gc_obstacles(cell, "mzi_ext_out"),
        spec="routing_sm_tight",
        strategy="grid_astar",
        step=10.0,
        fan_in="left",
        name="mzi_ext_out",
    )


def add_mzi_ext_input_routes(cell: fw.Component) -> None:
    """Bundle-route the ext row's inputs (``o1``, south) to its three eastmost couplers.

    **One autoroute call**, and the hardest of the four: ``o1`` faces **south**,
    directly away from the coupler line, so every lane is a ~360 deg loop --
    south out of the row, east around its east end, north up the clear corridor
    there, then west into ``c5`` / ``c4`` / ``c3`` from below. The other three
    bundles in this block are single L / lateral shifts.

    **Lane order reverses**, which is what a full loop does: the bundle's
    left-right order is fixed once (heading south, the eastmost rung ``C`` is the
    bundle's leftmost lane) and every subsequent leg is another left turn, so
    ``C`` stays leftmost throughout. Arriving north into the coupler line, left is
    **west** -- so ``C`` lands on the westmost target and ``A`` on the eastmost::

        A -> c5        B -> c4        C -> c3

    Equivalently, in the west-bound leg the northmost lane is closest to the
    couplers and must peel off first, i.e. onto the eastmost coupler. The
    order-preserving pairing crosses all three lanes.

    Room for the loop: the excursion stays within the block's own footprint
    (~450 um east of the row's east edge, local x ~1997, and ~140 um south of
    the ``o1`` line), so the die-level bbox abutment accounts for it. The
    west-bound leg threads the band **above** the row: ``mzi_ext_out`` gathers
    along the row top (local y -393..-295, x 896..1846) and then climbs the
    band's **west** edge (x 896..956), leaving y -295..-45 clear from x ~956
    east -- and only x <= 1311 is occupied at y -45..+5, so the ``c3``..``c5``
    approaches (x 1427+) are untouched. Hence ``o2X = 0``: the two ext bundles
    share the band without crossing.

    ``bbox_margin`` is the knob this needs. The endpoint bbox is just
    ``o1``-line-to-coupler-line (local x 905..1681), but the loop has to leave
    it on three sides -- ~450 um east to clear the row and ~140 um south. 800 um
    opens the window with margin; 1200 gives byte-identical geometry, so this is
    headroom, not tuning.

    ``fan_in="left"`` absorbs the convergence, as in
    :func:`add_mzi_ext_output_routes`: sources span 930 um port-to-port and the
    coupler triple only 254 um. It also matters *geometrically* here -- with no
    fan the lanes morph at the centreline corners and cut ~3374 um2 through the
    ext device moats; pinned left, that drops to a 0.5 um-wide moat graze along
    rung ``C``'s east edge (190 um2 on ``WG_RIB.field``, **zero** core-on-core),
    which is ordinary moat union where the lane passes the device.
    """
    labels = [label for label, _ in _LADDER]  # A (west) .. C (east)
    n = len(labels)
    cell.autoroute(
        ports_a=[(f"mzi_ext_{label}", "o1") for label in labels],  # west -> east
        # c5, c4, c3 -- reversed against the row, see the lane-order note above.
        ports_b=[("mzi_gc_array_ext", f"o1_r0_c{k}") for k in range(2 * n - 1, n - 1, -1)],
        obstacles=_ladder_gc_obstacles(cell, "mzi_ext_in", wire_sibling="mzi_ext_out"),
        spec="routing_sm_tight",
        strategy="vgraph_rect",
        bbox_margin=_EXT_IN_BBOX_MARGIN,
        fan_in="left",
        name="mzi_ext_in",
    )


def _ladder_gc_obstacles(
    cell: fw.Component,
    name: str,
    *,
    sibling: str | None = None,
    wire_sibling: str | None = None,
) -> ObstacleSet:
    """Obstacle set shared by every fibre-I/O bundle in this block.

    All six MZI bodies, both coupler arrays and both alignment loops -- deliberately
    the whole block rather than one group's half, because the two groups' lanes do
    reach into each other's x span (the ord output bundle's eastward leg, the ext
    bundle's lift-off under the ext alignment loop). The ord column's own DC/bias
    metal is not here: nothing in this block carries any.

    Two ways to add an already-placed sibling bundle:

    - ``sibling`` -- its whole-route **bbox**. Right when the new bundle stays
      clear of that bbox anyway (the ord pair: their x ranges are disjoint), and
      it is the cheapest footprint a consumer can get.
    - ``wire_sibling`` -- its per-wire-shape bboxes
      (:func:`~picasso.routing.obstacles.route_element_bboxes_for_child`).
      Required when the new bundle has to *reach into* the sibling's bbox: the ext
      ``o1`` lanes land on couplers whose x sits inside ``mzi_ext_out``'s
      whole-route bbox (which spans the full 400 um band), so the coarse form
      would wall the targets off and leave the goals "enclosed by obstacles".
    """
    obs = ObstacleSet(name=name)
    for label, _ in _LADDER:
        obs.add_instance(cell.instances[f"mzi_ord_{label}"])
        obs.add_instance(cell.instances[f"mzi_ext_{label}"])
    for inst in ("mzi_gc_array_ord", "mzi_gc_align_ord", "mzi_gc_array_ext", "mzi_gc_align_ext"):
        obs.add_instance(cell.instances[inst])
    if sibling is not None:
        obs.add_instance(cell.instances[sibling])
    if wire_sibling is not None:
        obs.add_polygons(route_element_bboxes_for_child(cell, wire_sibling))
    return obs


def add_mzi_ord_input_routes(cell: fw.Component) -> None:
    """Bundle-route the ord column's inputs (``o1``) to its three westmost couplers.

    The ord (E-W, ordinary-axis) rungs are the **west** column, and the only one of
    the two with the west/east port pair this idiom needs -- the ext rungs are N-S,
    their ports facing south and north, so they need their own topology.

    **One autoroute call.** All three ``o1`` ports share an outward heading (west)
    and all three coupler ports share an inward heading (north), which is what lets
    one bundle serve the whole column: west out of the stack, north up a corridor
    left of it, then east into ``c0`` / ``c1`` / ``c2`` from below.

    Lane order is the crossing-free one, and it falls out of the turn geometry:
    west->north->east is two right turns, so the **southmost** ``o1`` (rung ``C``,
    the bottom of the stack) rides the outside of both and ends up the northmost
    lane -- closest to the coupler line, so it peels off first onto the westmost
    coupler. Pairing bottom-to-top against ``c0``/``c1``/``c2`` west-to-east
    therefore keeps the lanes from crossing: ``C -> c0``, ``B -> c1``, ``A -> c2``.

    The ord rungs are stacked at a fixed bbox gap rather than a pitch, so the rows
    are unevenly spaced (~370 / ~480 um apart) and the climb is long -- rung ``C``
    starts ~1.2 mm below the coupler line. That costs nothing here: the corridor
    west of the column is empty for its whole height. ``routing_sm_default``, so
    the lanes pay the large Euler L-bend's low curvature loss rather than the tight
    bend's. See ``_ORD_GC_START_STRAIGHT`` for the one knob this needs.
    """
    labels = [label for label, _ in _LADDER]  # A (top) .. C (bottom)
    cell.autoroute(
        ports_a=[(f"mzi_ord_{label}", "o1") for label in reversed(labels)],  # bottom -> top
        ports_b=[("mzi_gc_array_ord", f"o1_r0_c{k}") for k in range(len(labels))],
        obstacles=_ladder_gc_obstacles(cell, "mzi_ord_in"),
        spec="routing_sm_default",
        strategy="grid_astar",
        step=10.0,
        start_straight=_ORD_GC_START_STRAIGHT,
        name="mzi_ord_in",
    )


def add_mzi_ord_output_routes(cell: fw.Component) -> None:
    """Bundle-route the ord column's outputs (``o2``) to its three eastmost couplers.

    **One autoroute call**, the mirror of :func:`add_mzi_ord_input_routes`: east out
    of the stack, north up a corridor right of it, then back **west** into ``c5`` /
    ``c4`` / ``c3`` from below.

    East->north->west is two *left* turns, but the southmost ``o2`` still rides the
    outside of both and still ends up the northmost lane, so it still peels off
    first -- except going west the first coupler reached is ``c5``. So the stack
    pairs bottom-to-top against ``c5``/``c4``/``c3`` east-to-west, which combined
    with the input side gives each rung a **nested** coupler pair::

        C: c0 <-> c5         B: c1 <-> c4         A: c2 <-> c3

    All six sit on one ``grating_coupling_pitch_for_tests`` row, so a 6-fibre array
    still lands the column in a single placement. Adjacent pairing would force the
    lanes to cross.

    The input bundle is added as an obstacle: the two sit in disjoint x ranges
    (input reaches local x ~665, ``c3`` sits at ~781), so listing it makes that
    separation explicit rather than incidental. Watch the **east** end: the forced
    eastward leg runs past this column's own coupler array toward the ext group's
    alignment loop. The loop is in the obstacle set so the lane passes beneath it,
    but that intrusion is worth keeping in mind around the ext column's routing.
    """
    labels = [label for label, _ in _LADDER]
    n = len(labels)
    cell.autoroute(
        ports_a=[(f"mzi_ord_{label}", "o2") for label in reversed(labels)],  # bottom -> top
        ports_b=[("mzi_gc_array_ord", f"o1_r0_c{k}") for k in range(2 * n - 1, n - 1, -1)],
        obstacles=_ladder_gc_obstacles(cell, "mzi_ord_out", sibling="mzi_ord_in"),
        spec="routing_sm_default",
        strategy="grid_astar",
        step=10.0,
        start_straight=_ORD_GC_START_STRAIGHT,
        name="mzi_ord_out",
    )


@recipe
def mzi_ladder_block() -> fw.Component:
    """The 6-MZI ladder as one self-contained block: ord column then ext row.

    Local frame: x = 0 on the ord column's centre, y = 0 on the GC-line centre;
    the ext group extends east, the rungs south. The die abuts this single
    Component against the paperclip block with ``add_aligned``.

    Positions the cells, then wires each group to its own coupler half in two
    bundles.

    The **ord** (west, E-W) column: inputs onto its three westmost couplers
    (:func:`add_mzi_ord_input_routes`) and outputs onto its three eastmost
    (:func:`add_mzi_ord_output_routes`), giving each rung a nested
    ``c0<->c5`` / ``c1<->c4`` / ``c2<->c3`` pair. Input before output: the output
    bundle takes the input bundle as an obstacle.

    The **ext** (east, N-S) row needs its own topology, its ports facing south and
    north rather than west and east: the ``o2`` outputs shift laterally north into
    the three westmost couplers (:func:`add_mzi_ext_output_routes`) while the
    ``o1`` inputs, facing away from the coupler line, loop around the row's east
    end up to the three eastmost (:func:`add_mzi_ext_input_routes`) -- so its rungs
    get the same nested pairing read the other way (``A: c0<->c5``). Outputs
    before inputs: the input bundle threads the band above the row and takes the
    output bundle's wire footprint as an obstacle.

    The ``_ord`` rungs stack vertically (A top, B middle, C bottom) at a fixed
    ``_ORD_STACK_GAP`` bbox-to-bbox gap. The ``_ext`` rungs sit in a single row
    west->east (A/B/C) at ``_EXT_ROW_GAP``, on one line, with their ``o2`` (north)
    ports ``_EXT_ROW_GC_GAP`` below the coupler port line -- see ``_EXT_ROW_GAP``
    for why a row and not a stack. The two groups sit ``_COL_GAP`` apart
    (bbox-to-bbox).

    Both constant-pitch grating-coupler arrays sit on **one** common line north of
    both groups. Each is centred over its own group -- the ext array (675 um) is
    narrower than the ext row it sits over -- with a fibre-alignment loop one pitch
    to its left (``mzi_gc_align_ord`` / ``_ext``).
    """
    cell = fw.Component()

    ord_cells = [(lbl, pdk.cells["unbalanced_mzi_rib_sm_800nm_ord"](length_imbalance=dl))
                 for lbl, dl in _LADDER]
    ext_cells = [(lbl, pdk.cells["unbalanced_mzi_rib_sm_800nm_ext"](length_imbalance=dl))
                 for lbl, dl in _LADDER]
    ab = _gc_test_line(2 * len(_LADDER)).bbox

    # --- horizontal layout, relative to the ord column centre x_ord = 0 ---
    # Ext rungs run west->east in one row at a fixed _EXT_ROW_GAP bbox-to-bbox gap.
    # Offsets are relative to the row's first port anchor (each ext cell carries o1
    # at local (0, 0), o2 directly above it, and its ΔL extends *west*, so xmin
    # varies per rung while xmax does not).
    ord_hw = max(m.bbox.dx for _, m in ord_cells) / 2.0
    ext_off: list[float] = [0.0]
    for (_, prev), (_, nxt) in pairwise(ext_cells):
        ext_off.append(ext_off[-1] + prev.bbox.xmax + _EXT_ROW_GAP - nxt.bbox.xmin)
    ext_left_rel = min(o + m.bbox.xmin for o, (_, m) in zip(ext_off, ext_cells, strict=True))
    ext_right_rel = max(o + m.bbox.xmax for o, (_, m) in zip(ext_off, ext_cells, strict=True))
    dx_col = ord_hw + _COL_GAP - ext_left_rel  # x_ext - x_ord (_COL_GAP bbox gap)
    x_ord = 0.0
    x_ext = x_ord + dx_col
    ext_center_x = x_ord + dx_col + (ext_left_rel + ext_right_rel) / 2.0

    # --- vertical layout: one GC line (centre = local y 0), the ord column and
    # the ext row below ---
    y_gc = 0.0
    y_gc_ports = y_gc - ab.dy / 2.0  # coupler port line (array bottom edge)
    y_stack_top = y_gc - _GC_TO_STACK  # top (A) rung centre, ord column

    # Ord column: fixed bbox-to-bbox gap, A top-anchored.
    prev_bottom = 0.0
    for k, (label, m) in enumerate(ord_cells):
        half = m.bbox.dy / 2.0
        cy = y_stack_top if k == 0 else prev_bottom - _ORD_STACK_GAP - half
        _place_centered(cell, m, f"mzi_ord_{label}", x_ord, cy)
        prev_bottom = cy - half
    # Ext row: all three on one line, o2 (north) _EXT_ROW_GC_GAP below the coupler
    # ports. Placing at the port anchor puts o1 exactly at (x, y_ext_o1) -- every
    # rung is the same height, so both port sets come out co-linear in y.
    ext_h = max(m.bbox.dy for _, m in ext_cells)
    y_ext_o1 = (y_gc_ports - _EXT_ROW_GC_GAP) - ext_h
    for off, (label, m) in zip(ext_off, ext_cells, strict=True):
        cell.add_placed(m, name=f"mzi_ext_{label}", x=x_ext + off, y=y_ext_o1)

    # Two GC arrays on one common line, each with its left alignment loop.
    _add_gc_array_with_alignment(cell, "ord", x_ord, y_gc, ab.dx, ab.dy)
    _add_gc_array_with_alignment(cell, "ext", ext_center_x, y_gc, ab.dx, ab.dy)

    # Ord (west, E-W) column fibre I/O: one bundle per side, input first (the
    # output avoids it).
    add_mzi_ord_input_routes(cell)
    add_mzi_ord_output_routes(cell)
    # Ext (east, N-S) row: north outputs -> the 3 westmost ext couplers, then the
    # south inputs looping around the row's east end up to c5..c3. Outputs first:
    # the input bundle threads the band above the row and takes the output
    # bundle's own wire footprint as an obstacle.
    add_mzi_ext_output_routes(cell)
    add_mzi_ext_input_routes(cell)

    cell.cell_type = "test_structure"
    cell.description = (
        "Unbalanced-MZI n_eff/n_g calibration ladder test block: the A/B/C dL "
        "rungs in both waveguide orientations (ord column + ext row), each "
        "group wired to its own GC array."
    )
    return cell
