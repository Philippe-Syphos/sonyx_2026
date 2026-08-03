"""Directional-coupler coupling-length test (R4A).

Directional couplers with a swept parallel coupling length ``L`` map the
bar/cross power split ``cos^2(kappa L)`` / ``sin^2(kappa L)``, so fitting the
measured split vs. L extracts the coupling coefficient / beat length and
calibrates the coupler design. Two tiers are placed: a sweep around the 50/50
point (L = 75.47 um nominal) on top and a sweep around the 5/95-tap point
(L = 94.38 um nominal, its nominal included) below it.

Per DUT the intended wiring connects **three** ports to grating couplers --
``o2`` (input, the upper west port), ``o3`` (bar output, upper east) and ``o4``
(cross output, lower east) -- while ``o1`` (the second, unused input) is
terminated by a beam dump (:func:`dump_two_groups`) so it cannot reflect back up
the input lane. The eight DCs are split into **two groups of four**, each with its own
N-S grating-coupler array (``gratingcoupler_rib_sm_800nm_ext``, three couplers per
DC) + left alignment loop, placed side by side. Each DUT is the PDK DC cell for
its tier's split ratio (``directionalcoupler_rib_sm_800nm_ord_50_50`` / ``_5_95``)
with the surfaced ``coupling_length`` overridden per instance -- the gap stays at
the PDK design point, and the PDK cell carries the blackbox flag.

Every grating coupler in the R4A top band sits on **one continuous
``grating_coupling_pitch_for_tests`` grid** -- inside each array, across each
group's alignment loopback, from group to group, and from this block to the
back-to-back-MZI block east of it (see :func:`group_pitch` /
:func:`block_x_base`), so one fibre array steps the whole row uniformly.

Fully routed, two bundles per group: the four west couplers -> the DUT ``o2``
inputs (:func:`add_group_input_routes`), and the DUT ``o3``/``o4`` outputs -> the
eight remaining couplers (:func:`add_group_output_routes`). A tier is therefore
three passes -- :func:`place_two_groups`, :func:`route_two_groups`,
:func:`dump_two_groups` -- all taking the same ``lengths`` / prefixes.
"""

from __future__ import annotations

from collections.abc import Callable

import picasso as fw
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from luqia_ln200.cells.splitters import (
    directionalcoupler_rib_sm_800nm_ord_5_95,
    directionalcoupler_rib_sm_800nm_ord_50_50,
)
from picasso.component import PortSpec
from picasso.leaves import make_array
from picasso.recipe import recipe

from ..parameters import parameters as _p
from .beam_dumps import add_2x2_input_beam_dumps

# Swept parallel coupling lengths (um). Two sweeps, one per tap ratio, each
# centred on the PDK nominal for that coupler:
#   50/50 -> nominal L = 75.47 um; 5/95 tap -> nominal L = 94.38 um.
# The tap sweep includes its nominal (94.38) and brackets it.
_LENGTHS_5050: tuple[float, ...] = (10.0, 30.0, 55.0, 75.0, 95.0, 120.0, 150.0, 190.0)
_LENGTHS_TAP: tuple[float, ...] = (45.0, 65.0, 80.0, 94.38, 108.0, 125.0, 155.0, 195.0)

# Per DUT: one input coupler (o2) + two output couplers (o3 bar / o4 cross);
# o1 -- the second, unused input -- is left open.
_GC_PER_DC = 3
_INPUT_PORT = "o2"  # DUT port the input bundle lands on (upper west)
_OUTPUT_PORTS = ("o3", "o4")  # bar (upper east) then cross (lower east)
# The 8 DCs split into two side-by-side groups of this many.
_PER_GROUP = 4
# Grating couplers in a group's alignment loopback (a 2-coupler U-turn, itself on
# the grating pitch) -- counted so the group pitch keeps the whole row on grid.
_ALIGN_GC = 2

# Layout (um). Each group: GC array north (left loop + couplers) with its 4 DCs
# stacked below, inputs (o2) aligned on the group's input column.
_LEFT_MARGIN = 1750.0  # first group's left edge off the left inner edge
_TOP_MARGIN = 40.0  # coupler/loop tops below the top inner edge
_GC_TO_DC_GAP = 120.0  # GC array bottom down to the top DC
_DC_ROW_PITCH = 120.0  # vertical centre-to-centre of stacked DCs
_TIER_DROP = 750.0  # vertical drop from the 50/50 tier to the 5/95 tier below it
_NUM_GROUPS = 2  # side-by-side groups per sweep block

# Eastward run (um) each input lane needs between its coupler and its DUT's o2.
# The lane drops out of the coupler and turns east into o2 (see
# :func:`add_group_input_routes`); the tight L-bend's footprint radius is 30 um, but
# the bundle needs more than one bend's worth -- measured on the two back-to-back-MZI
# east groups (the binding case), the planner folds its centreline back on itself
# below 90 um and plans cleanly at 90 and above. 120 um is that floor plus ~1 bend
# radius of margin, and still leaves ~200 um between the widest DUT's east end and
# the last output coupler.
_INPUT_LANE_RUN = 120.0


def _dc_dut(coupling_length: float) -> fw.Component:
    """The PDK 50/50 DC at the given coupling length; ports ``o1``-``o4``."""
    return directionalcoupler_rib_sm_800nm_ord_50_50(coupling_length=coupling_length)


def _tap_dc_dut(coupling_length: float) -> fw.Component:
    """The PDK 5/95-tap DC at the given coupling length; ports ``o1``-``o4``."""
    return directionalcoupler_rib_sm_800nm_ord_5_95(coupling_length=coupling_length)


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


def group_gc_width() -> float:
    """Horizontal extent (um) of a group's GC array (loop + pitch gap + couplers)."""
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    lb = gratingcoupler_alignment_rib_sm_800nm_ext().bbox
    return lb.dx + (pitch - gc_w) + _gc_line(_GC_PER_DC * _PER_GROUP).bbox.dx


def group_pitch() -> float:
    """Group-to-group x pitch (um) -- a whole number of grating pitches.

    A group's couplers form an unbroken pitch chain: ``_ALIGN_GC`` in the alignment
    loopback then ``_GC_PER_DC * _PER_GROUP`` in the array. Stepping the next group
    by exactly that many pitches continues the chain across the group boundary
    instead of leaving an arbitrary gap, so **every** coupler in the row -- both
    groups of both blocks, loopbacks included -- lands on one grid and a fibre array
    steps it uniformly.

    This is ``group_gc_width()`` plus one ``pitch - gc_w`` step: the group's own
    extent stops at its last coupler's east edge, and the step carries the grid over
    to the next group's first coupler centre.
    """
    per_group = _ALIGN_GC + _GC_PER_DC * _PER_GROUP
    return per_group * _p.grating_coupling_pitch_for_tests.value


def block_x_base(block_index: int) -> float:
    """Left edge (um) of sweep block ``block_index``, in the die frame.

    Block ``0`` is the single-DC sweep (:func:`add_dc_length_sweep`), block ``1`` the
    back-to-back-MZI sweep (:func:`~sonyx.blocks.dc_mzi_length_sweep`). Blocks tile
    west to east at ``_NUM_GROUPS`` whole :func:`group_pitch` steps, which is what
    keeps the grating grid continuous *between* blocks as well as within them -- so
    the MZI block's position is derived here rather than carrying its own margin
    (an independent margin silently drifts off the grid).
    """
    half_w = _p.die_width.value / 2.0
    x0 = (-half_w + _p.keepout_width.value) + _LEFT_MARGIN
    return x0 + block_index * _NUM_GROUPS * group_pitch()


def _input_coupler_index(num_duts: int, dut_index: int) -> int:
    """Which coupler feeds DUT ``dut_index`` (0 = top of the stack).

    The reversed pairing that :func:`add_group_input_routes` routes: coupler ``c0``
    (west-most) feeds the bottom DUT and ``c{n-1}`` the top one. Defined once here so
    the placement clearance rule (:func:`_input_lane_shift`) and the router agree.
    """
    return num_duts - 1 - dut_index


def _input_column_x(
    arr: fw.Component, array_x: float, array_center_x: float,
    lengths: tuple[float, ...], dut_factory: Callable[[float], fw.Component],
) -> float:
    """Common x for the group's DUT ``_INPUT_PORT`` ports -- the group's **input column**.

    The DUTs of a group differ in length, so centring each one on the GC array (the
    old rule) staircases their input ports over ~95 um of x. Aligning them on one
    column instead is what the group layout intends ("inputs aligned"), and it is
    what makes a bundle fan-in legal on the DUT side: ``autoroute``'s fan requires
    every ``ports_a`` at the same spine coordinate.

    The column is the east-most position the DUTs would take if each were centred, so
    no DUT is pulled west of where centring put it, bumped further east if that would
    leave the east-most input lane less than ``_INPUT_LANE_RUN`` of eastward run.
    With one shared column only that last (east-most) coupler's lane can be short, so
    the single clearance test covers the whole group.
    """
    centred = [
        (array_center_x - dut_factory(length).bbox.center_x)
        + dut_factory(length).ports[_INPUT_PORT].position[0]
        for length in lengths
    ]
    last_coupler_x = array_x + arr.ports[f"o1_r0_c{len(lengths) - 1}"].position[0]
    return max(max(centred), last_coupler_x + _INPUT_LANE_RUN)


def _add_group(
    cell: fw.Component, x_left: float, y_top: float, y0: float,
    lengths: tuple[float, ...], tag: str, *,
    dut_factory: Callable[[float], fw.Component] = _dc_dut,
    gc_prefix: str = "dc_gc", dut_prefix: str = "dc_len",
) -> None:
    """Place one group: GC array + left alignment loop (north) and its DUTs below.

    The alignment loop's left edge sits at ``x_left``; couplers/loop tops at
    ``y_top``. The array's first coupler continues the loopback's pitch chain, so the
    group is one unbroken grating grid. Each DUT (from ``dut_factory``, a
    coupling-length -> Component) is stacked downward from ``y0`` with its
    ``_INPUT_PORT`` on the group's shared input column (:func:`_input_column_x`) --
    the DUTs differ in length, so aligning their inputs is not the same as centring
    their bodies -- and the ``y0`` rows are the *input port* heights, so a row's pitch
    is what the router sees. Instances ``{gc_prefix}_align_{tag}`` /
    ``{gc_prefix}_array_{tag}`` / ``{dut_prefix}_{L}`` -- prefixes keep sibling
    sweeps on one die distinct.
    """
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(loop, name=f"{gc_prefix}_align_{tag}", x=x_left - lb.xmin, y=y_top - lb.ymax)
    arr = _gc_line(_GC_PER_DC * len(lengths))
    ab = arr.bbox
    array_x = (x_left + lb.dx) + (pitch - gc_w) - ab.xmin  # placement offset
    cell.add_placed(arr, name=f"{gc_prefix}_array_{tag}", x=array_x, y=y_top - ab.ymax)
    array_center_x = array_x + ab.center_x  # GC array horizontal centre
    in_x = _input_column_x(arr, array_x, array_center_x, lengths, dut_factory)
    for i, length in enumerate(lengths):
        dut = dut_factory(length)
        in_port = dut.ports[_INPUT_PORT].position
        cell.add_placed(
            dut, name=f"{dut_prefix}_{length:g}",
            x=in_x - in_port[0], y=(y0 - i * _DC_ROW_PITCH) - in_port[1],
        )


def _group_split(lengths: tuple[float, ...]) -> tuple[tuple[tuple[float, ...], str], ...]:
    """Split a tier's sweep into its two groups: ``((first half, "a"), (second half, "b"))``.

    One source of truth for which lengths belong to which group tag, shared by the
    placement pass (:func:`place_two_groups`) and the routing pass
    (:func:`route_two_groups`) so the two can never drift apart.
    """
    return ((lengths[:_PER_GROUP], "a"), (lengths[_PER_GROUP:], "b"))


def place_two_groups(
    cell: fw.Component, *, lengths: tuple[float, ...], x_base: float, y_top: float,
    dut_factory: Callable[[float], fw.Component] = _dc_dut,
    gc_prefix: str = "dc_gc", dut_prefix: str = "dc_len",
) -> None:
    """Place a length sweep as two side-by-side groups anchored at (x_base, y_top).

    Splits ``lengths`` into two groups of ``_PER_GROUP`` (first half / second
    half), each a GC array + left alignment loop with its DUTs below; the second
    group is offset right by exactly one :func:`group_pitch`, which continues the
    grating grid across the group boundary. Shared by the 50/50 and 5/95-tap tiers
    and by the single-DC and back-to-back-MZI blocks.
    """
    lb = gratingcoupler_alignment_rib_sm_800nm_ext().bbox
    y0 = (y_top - lb.dy) - _GC_TO_DC_GAP  # top DUT below the (tallest) alignment loop
    step = group_pitch()
    for g, (lens, tag) in enumerate(_group_split(lengths)):
        x_left = x_base + g * step
        _add_group(
            cell, x_left, y_top, y0, lens, tag,
            dut_factory=dut_factory, gc_prefix=gc_prefix, dut_prefix=dut_prefix,
        )


def add_group_input_routes(
    cell: fw.Component, lengths: tuple[float, ...], *, tag: str,
    gc_prefix: str = "dc_gc", dut_prefix: str = "dc_len", name: str | None = None,
    strategy: str = "grid_astar", step: float = 10.0,
    fan_in: bool | float | str | None = None,
) -> None:
    """Route a group's four **west** grating couplers into its four DUT ``o2`` inputs.

    One bundle, one ``autoroute`` call: the group's GC array dedicates its four
    west-most couplers (``c0..c3``) to the DUT inputs and the remaining eight to the
    bar/cross outputs, so the input lanes share a corridor and can be planned
    together (four separate calls plan independently and cross in that corridor).

    The couplers face **south** and every ``o2`` faces **west**, so the bundle drops
    out of the GC row into the vertical channel between the couplers and the DUT west
    edges, then each lane peels off east into its DUT. The DUT inputs sit on one
    column (:func:`_input_column_x`) at least ``_INPUT_LANE_RUN`` east of ``c3``, so
    the whole channel sits under the coupler row. ``o1`` -- the unused lower west
    input, 21.3 um below ``o2`` -- stays open; the lane arrives collinear with ``o2``
    and never crosses it.

    **Pairing is reversed** (``c0`` -> the *bottom* DUT, ``c3`` -> the *top* one).
    In the vertical channel the lanes are ordered in x; peeling east, the lane that
    turns first (the top DUT) has to be the inner-most, i.e. the east-most lane. So
    east-most coupler -> top DUT is the crossing-free matching, and the natural
    ``c0`` -> top order would cross all three lanes below it. ``lengths`` is in
    placement order (top to bottom), so the pairing just reverses it.

    Tight SM spec (``lbend_rib_sm_800nm_tight``, 30 um footprint radius): the DUT
    row pitch is 120 um, so a peel-off L costs 2 x 30 um of the 120 um budget and the
    default 100 um-radius bend would not fit.

    Args:
        cell: die cell carrying the group (extended in place).
        lengths: the group's own ``_PER_GROUP`` coupling lengths, in placement order
            (top DUT first) -- i.e. one half of a tier's sweep, the same slice
            :func:`place_two_groups` handed to :func:`_add_group`.
        tag: group tag (``"a"`` / ``"b"``) naming its GC array.
        gc_prefix: GC-array instance prefix, matching the placement call.
        dut_prefix: DUT instance prefix, matching the placement call.
        name: route-child name; defaults to ``{dut_prefix}_in_{tag}``.
        strategy: centreline planner. ``grid_astar`` (default) plans all eight
            groups cleanly; kept as a knob because a group whose corridor tightens
            may want ``vgraph_rect`` without touching the other seven.
        step: ``grid_astar`` grid spacing (um); ignored by the other strategies.
        fan_in: ``autoroute``'s side-A (DUT side) fan override. ``None`` (default)
            lets the bundle absorb the per-lane morph at its first corner, which all
            eight groups plan cleanly on. An explicit fan is *legal* here only
            because the DUT inputs share one column (:func:`_input_column_x`) --
            ``autoroute``'s fan rejects a side whose ports differ in spine coord.
    """
    n = len(lengths)
    pairs = [(_input_coupler_index(n, i), length) for i, length in enumerate(lengths)]
    pairs.sort()  # coupler order, west to east
    gc_ports: list[PortSpec] = [
        (f"{gc_prefix}_array_{tag}", f"o1_r0_c{c}") for c, _ in pairs
    ]
    dut_ports: list[PortSpec] = [
        (f"{dut_prefix}_{length:g}", _INPUT_PORT) for _, length in pairs
    ]
    kwargs = {"step": step} if strategy == "grid_astar" else {}
    cell.autoroute(
        ports_a=dut_ports,
        ports_b=gc_ports,
        spec="routing_sm_tight",
        strategy=strategy,
        fan_in=fan_in,
        name=name or f"{dut_prefix}_in_{tag}",
        **kwargs,
    )


def add_group_output_routes(
    cell: fw.Component, lengths: tuple[float, ...], *, tag: str,
    gc_prefix: str = "dc_gc", dut_prefix: str = "dc_len", name: str | None = None,
    strategy: str = "grid_astar", step: float = 10.0,
    fan_out: bool | float | str | None = "left",
) -> None:
    """Route a group's eight DUT outputs into its eight remaining grating couplers.

    One bundle, one ``autoroute`` call, mirroring :func:`add_group_input_routes`: the
    inputs take ``c0..c{n-1}``, so the outputs take everything left -- ``c{n}..c{3n-1}``,
    two couplers per DUT (``o3`` bar, upper east; ``o4`` cross, lower east).

    Both output ports face **east** and the couplers face **south**, so each lane
    exits east of the DUT stack, turns north up the corridor there, and lands on its
    coupler. **Several of the eight couplers sit west of the DUT east edge** --
    directly above the DUT bodies -- because the input-lane clearance
    (:func:`_input_column_x`) pushes the stack east: ``c4``-``c6`` on the single-DC
    groups (~300 um of westward reach), ``c4``-``c8`` on the back-to-back-MZI groups,
    whose DUTs are ~2x longer (up to ~610 um). Those lanes cannot go straight up: they
    run east, north into the ~170 um band between the DUT tops and the coupler row,
    then back west to their coupler. That reversal is fine as long as the whole bundle
    reverses together, which is why this is one bundle and not eight calls.

    **Pairing is y-descending -> coupler west-to-east**: the top DUT's ``o3`` takes
    ``c{n}`` and the bottom DUT's ``o4`` takes the last coupler. Turning from
    east-heading to north-heading puts the north-most lane on the inside of the turn,
    i.e. west-most in the corridor, so source-y order (north to south) *is* corridor
    x order (west to east) -- and landing that order onto the couplers west to east
    keeps the fan crossing-free.

    Args:
        cell: die cell carrying the group (extended in place).
        lengths: the group's own coupling lengths, in placement order (top DUT first).
        tag: group tag (``"a"`` / ``"b"``) naming its GC array.
        gc_prefix: GC-array instance prefix, matching the placement call.
        dut_prefix: DUT instance prefix, matching the placement call.
        name: route-child name; defaults to ``{dut_prefix}_out_{tag}``.
        strategy: centreline planner, as in :func:`add_group_input_routes`.
        step: ``grid_astar`` grid spacing (um); ignored by the other strategies.
        fan_out: ``autoroute``'s side-B (coupler side) fan override, ``"left"`` here
            and **required** -- unlike the input bundles this one cannot ride on
            fan-at-turn. Without an explicit fan the bundle keeps its endpoints' full
            spread (444.5 um half-width on the coupler side, 190.7 um on the DUT
            side), and the westward leg then needs 635 um of self-clearance where the
            band between the DUT tops and the coupler row offers 291 um -- the
            planner rejects it. The fan collapses the coupler side to the cohesive
            lane pitch, which fits. ``"left"`` pins the west-most lane so it lands
            straight on ``c{n}``; ``True`` and ``"centre"`` do not plan (their fan
            geometry cannot be lowered at this corner). A fan is legal on this side
            because the couplers share one y.
    """
    n = len(lengths)
    dut_ports: list[PortSpec] = [
        (f"{dut_prefix}_{length:g}", port)
        for length in lengths  # placement order: top DUT first
        for port in _OUTPUT_PORTS  # o3 (upper) before o4 (lower)
    ]
    gc_ports: list[PortSpec] = [
        (f"{gc_prefix}_array_{tag}", f"o1_r0_c{n + i}") for i in range(len(dut_ports))
    ]
    kwargs = {"step": step} if strategy == "grid_astar" else {}
    cell.autoroute(
        ports_a=dut_ports,
        ports_b=gc_ports,
        spec="routing_sm_tight",
        strategy=strategy,
        fan_out=fan_out,
        name=name or f"{dut_prefix}_out_{tag}",
        **kwargs,
    )


def route_two_groups(
    cell: fw.Component, *, lengths: tuple[float, ...],
    gc_prefix: str = "dc_gc", dut_prefix: str = "dc_len",
) -> None:
    """Route both groups of a tier: an input bundle and an output bundle per group.

    The routing counterpart of :func:`place_two_groups` -- same ``lengths`` /
    ``gc_prefix`` / ``dut_prefix`` arguments and the same ``_group_split``, so a tier
    is placed and routed with a matching pair of calls. Four ``autoroute`` calls in
    all: per group, :func:`add_group_input_routes` (4 lanes, west couplers) then
    :func:`add_group_output_routes` (8 lanes, the rest).

    One bundle per group per direction, not fewer and not more. The two groups are
    ~1.8 mm apart in x and share no corridor, so bundling them together would only
    force lanes across the gap; and within a group the inputs run west of the DUT
    stack while the outputs run east of it, so a combined 12-lane bundle would have
    no common corridor either.
    """
    for lens, tag in _group_split(lengths):
        add_group_input_routes(
            cell, lens, tag=tag, gc_prefix=gc_prefix, dut_prefix=dut_prefix
        )
        add_group_output_routes(
            cell, lens, tag=tag, gc_prefix=gc_prefix, dut_prefix=dut_prefix
        )


def dump_two_groups(
    cell: fw.Component, *, lengths: tuple[float, ...], dut_prefix: str = "dc_len"
) -> list[str]:
    """Terminate both groups' unused DUT inputs (``o1``) with PDK beam dumps.

    The third pass of a tier, after :func:`place_two_groups` and
    :func:`route_two_groups` and taking the same ``lengths`` / ``dut_prefix``. Only
    ``_INPUT_PORT`` (``o2``) is fed, so every DUT's ``o1`` would otherwise end in a
    bare facet reflecting back up the input lane and into the measurement -- exactly
    what corrupts a split-ratio fit. :func:`..beam_dumps.add_2x2_input_beam_dumps`
    reads the open port off the nets (so this must run *after* the routing pass) and
    mirrors each dump away from the fed ``o2`` above it -- which here also points the
    body down-and-west, into the empty band between the DUT and the next row, rather
    than up across ``o2``'s own lane.
    """
    return add_2x2_input_beam_dumps(
        cell,
        [f"{dut_prefix}_{length:g}" for length in lengths],
    )


def add_dc_length_sweep(cell: fw.Component) -> None:
    """Place the single-DC coupling-length sweep on R4A -- 50/50 tier + 5/95 tier.

    Two stacked tiers, each two side-by-side groups of four: the 50/50 sweep
    (``_LENGTHS_5050``) at the top, and the 5/95-tap sweep (``_LENGTHS_TAP``,
    centred on the 94.38 um nominal) ``_TIER_DROP`` below it. Instances
    ``dc_*`` (50/50) and ``tap_dc_*`` (5/95). Every DUT's unused ``o1`` is beam-dumped.

    This is sweep block ``0`` (:func:`block_x_base`), the west-most of the two. Both
    groups of both tiers are fully routed by :func:`route_two_groups` -- inputs to the
    four west couplers, outputs to the eight remaining ones -- then terminated by
    :func:`dump_two_groups`.
    """
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    x_base = block_x_base(0)
    y1 = (half_h - kw) - _TOP_MARGIN
    place_two_groups(cell, lengths=_LENGTHS_5050, x_base=x_base, y_top=y1)
    place_two_groups(
        cell, lengths=_LENGTHS_TAP, x_base=x_base, y_top=y1 - _TIER_DROP,
        dut_factory=_tap_dc_dut, gc_prefix="tap_dc_gc", dut_prefix="tap_dc_len",
    )
    # Routing pass, one bundle per group per direction: the four west couplers -> the
    # DUT inputs, then the DUT outputs -> the eight remaining couplers.
    route_two_groups(cell, lengths=_LENGTHS_5050)
    route_two_groups(cell, lengths=_LENGTHS_TAP, gc_prefix="tap_dc_gc", dut_prefix="tap_dc_len")
    # Termination pass (after routing, which is what marks o2 as fed): a beam dump on
    # every DUT's unused o1, mirrored away from the fed o2.
    dump_two_groups(cell, lengths=_LENGTHS_5050)
    dump_two_groups(cell, lengths=_LENGTHS_TAP, dut_prefix="tap_dc_len")
