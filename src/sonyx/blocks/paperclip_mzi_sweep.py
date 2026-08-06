"""Paperclip-TOPS test — MZIs with a folded thermo-optic phase shifter, arm sweep.

Measures the folded (paperclip) thermo-optic phase shifter and how its efficiency
scales with the number of folded arms. Three MZIs, each carrying a paperclip TOPS
of a different **fold count** (num_arms = 3 / 5 / 7) on one arm; the heater is the
*same* default Cr ladder on all three, so the only variable is how many folded
arm-lengths share that one heater footprint (N=1 would be the straight-TOPS
baseline in the neighbouring heater_cr block).

Each paperclip TOPS is the PDK ``paperclip_tops_rib_sm_800nm`` with the surfaced
``num_arms`` overridden per instance (default heater, default arm length). The
paperclip is 150-360 um tall, so the MZI arms are fanned with **L-bend risers**
(a straight of the paperclip's height between two 90 deg bends), not S-bends.

MZI topology (offset-coupler form, by request): from the input MMI's top port,
put()-cascade lbend -> straight(=paperclip height) -> lbend -> paperclip TOPS ->
straight -> output MMI. That single upward jog leaves the output MMI offset ~240
um above the input. The reference arm then runs east **under** the paperclip at
the input level and jogs up **east** of it into the output MMI's lower port
(rising to just below the paperclip arm, so the two never cross). The paperclip
is thus offset between the two couplers.

The whole test is one self-contained Component
(:func:`paperclip_mzi_sweep_block`) built in its own local frame -- origin at
the optical block's top-left anchor, i.e. x = 0 on the alignment loop's west
edge and y = 0 on the GC/loop tops line (the DC pad row tucks slightly west of
that, so the bbox west edge is the pads'). The die (``dies/die_r4b.py``) abuts
that single instance against the heater block with ``add_aligned``; nothing
here knows die coordinates.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.bends import lbend_rib_sm_800nm
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from luqia_ln200.cells.dc import bondpad_for_test_top
from luqia_ln200.cells.modulators import paperclip_tops_rib_sm_800nm
from luqia_ln200.cells.splitters import mmi_1x2_rib_sm_800nm_ord_6um
from picasso.leaves import make_array, make_straight
from picasso.recipe import recipe
from picasso.routing import ObstacleSet

from ..parameters import parameters as _p

# Fold-count sweep: paperclip arm counts (odd, >= 3).
_NUM_ARMS: tuple[int, ...] = (3, 5, 7)
# Top-arm riser vertical straight = paperclip height minus this (um). The two
# L-bends already add ~100 um of rise, so the arm needn't lift by the full
# paperclip height to clear the reference arm below.
_RISER_SHORTEN = 150.0
# Margin (um) above the riser floor. The reference arm lands sr = riser - pc_drop
# below the paperclip arm, where pc_drop is the paperclip's o1->o2 y-drop (grows
# with num_arms: 12/24/36 um for N=3/5/7). So riser must exceed pc_drop for the
# return arm to close; this margin keeps sr positive.
_RISER_MARGIN = 5.0
# Top-arm straight after the paperclip (um): long enough to open a lane east of
# the paperclip for the reference arm's up-riser.
_TOP_OUT_STRAIGHT = 140.0
# Reference up-riser x-position, this far east of the paperclip's east edge (um).
_REF_RISER_MARGIN = 40.0

# Placement: three MZIs stacked, in the block's own local frame. The optical
# anchor is local x = 0 (the alignment loop's west edge) -- the GC array keys
# off it and the MZIs are centred on the array.
_ROW_PITCH = 280.0  # vertical centre-to-centre of stacked MZIs

# Grating-coupler array (north of the block) + left alignment loop, and DC bond
# pads (below the block). One in + one out coupler per MZI.
_GC_PER_MZI = 2
_GC_TO_BLOCK_GAP = 60.0  # from the GC array bottom down to the top device's top
_NUM_DC_PADS = 4
# Centre x of pad 1, block-local. Negative: the 4-pad row tucks slightly west
# of the optical anchor, preserving the pad<->device geometry the bias-route
# bundles were tuned against. Pad 1's LEFT edge is the block's west bbox edge,
# so its centre sits 100 um (half a pad) inside it -- the heater block pins its
# last pad centre 150 um inside its own east bbox edge, making the two rows one
# gapless 250 um probe grid under the die's corner-on-corner abutment.
_PAD_ROW_X0 = -500.0
# Routing spec for the heater bias / ground metal (see luqia_ln200.tech.routing_specs).
_DC_SPEC = "routing_top_metal"

# Fibre-I/O bundle knobs, both sides (see add_paperclip_input_routes).
# Forced first leg (um) along each MZI port's own heading before the pathfinder's
# first vertex. Required on *both* sides here: every coupler this block targets sits
# on the far side of the ports it feeds (the couplers span local x 274..909 while
# the inputs are all west of 176 and the outputs all east of 1007), so without it
# the planner tries to reverse on leg 0 and rejects the bundle. Kept small -- these
# legs are the block's outermost intrusions.
_GC_START_STRAIGHT = 40.0
# Search-window inflation (um) around each bundle's endpoint bbox. The 50 um default
# leaves no room for that forced leg to turn (the outermost port *is* the bbox edge)
# and neither side finds a path. Identical results from 150 up -- headroom, not tuning.
_GC_BBOX_MARGIN = 150.0


def _straight(length: float) -> fw.Component:
    return make_straight(length=length, cross_section="rib_sm_800nm")


def _paperclip_tops(num_arms: int) -> fw.Component:
    """The PDK paperclip TOPS at ``num_arms`` folds (default heater / arm length).

    Ports: ``o1``/``o2`` (WG west/east) and ``e1``/``e2`` (heater terminals).
    """
    return paperclip_tops_rib_sm_800nm(num_arms=num_arms)


@recipe
def _paperclip_mzi(num_arms: int) -> fw.Component:
    """Offset-coupler MZI with a ``num_arms`` paperclip TOPS on the top arm.

    Top arm (put-cascade from the input MMI's top port): lbend -> straight(=
    paperclip height) -> lbend -> paperclip TOPS -> straight -> output MMI. The
    reference arm runs east under the paperclip and jogs up east of it into the
    output MMI's lower port. Ports: ``o1`` (input, west), ``o2`` (output, east,
    offset up ~240 um), ``e1``/``e2`` (heater terminals). Every abutment a Net.
    """
    pc = _paperclip_tops(num_arms)
    pc_h = pc.bbox.dy
    lbend = lbend_rib_sm_800nm()
    leg = lbend.ports["o2"].position[0]  # 90 deg bend leg (= dx = dy)

    cell = fw.Component()
    mi = cell.add_placed(mmi_1x2_rib_sm_800nm_ord_6um(), name="mmi_in")
    # Top arm: up-riser -> paperclip -> output straight -> output MMI (mate its
    # o3, so the free port o2 is the LOWER combiner input).
    t1 = cell.put(lbend, (mi.name, "o2"), port_to="o1", name="t_lb1")
    pc_drop = pc.ports["o1"].position[1] - pc.ports["o2"].position[1]
    riser_len = max(pc_h - _RISER_SHORTEN, pc_drop + _RISER_MARGIN)
    t2 = cell.put(_straight(riser_len), (t1.name, "o2"), port_to="o1", name="t_str1")
    t3 = cell.put(lbend, (t2.name, "o2"), port_to="o1", name="t_lb2", mirror=True)
    tp = cell.put(pc, (t3.name, "o2"), port_to="o1", name="paperclip")
    ts = cell.put(_straight(_TOP_OUT_STRAIGHT), (tp.name, "o2"), port_to="o1", name="t_str2")
    mo = cell.put(mmi_1x2_rib_sm_800nm_ord_6um(), (ts.name, "o2"), port_to="o3", name="mmi_out")

    pcb = cell.instances["paperclip"].bbox
    assert pcb is not None
    free = mo.ports["o2"].position  # lower free combiner input
    y0 = mi.ports["o3"].position[1]
    x_riser = pcb.xmax + _REF_RISER_MARGIN

    # Reference arm: east under the paperclip, up-riser east of it, into free port.
    le = (x_riser - leg) - mi.ports["o3"].position[0]
    r1 = cell.put(_straight(le), (mi.name, "o3"), port_to="o1", name="r_str0")
    r2 = cell.put(lbend, (r1.name, "o2"), port_to="o1", name="r_lb1")
    sr = free[1] - (y0 + 2.0 * leg)
    r3 = cell.put(_straight(sr), (r2.name, "o2"), port_to="o1", name="r_str1")
    r4 = cell.put(lbend, (r3.name, "o2"), port_to="o1", name="r_lb2", mirror=True)
    lf = free[0] - r4.ports["o2"].position[0]
    r5 = cell.put(_straight(lf), (r4.name, "o2"), port_to="o1", name="r_str2")
    cell.connect((r5.name, "o2"), (mo.name, "o2"))

    cell.add_port("o1", (mi.name, "o1"))
    cell.add_port("o2", (mo.name, "o1"))
    cell.add_port("e1", (tp.name, "e1"))
    cell.add_port("e2", (tp.name, "e2"))
    cell.cell_type = "mzi"
    cell.description = (
        f"Offset-coupler MZI with a {num_arms}-arm paperclip TOPS on the top arm "
        "(L-bend risers) and a reference arm routed under/around it -- 800 nm SM rib."
    )
    cell.calibration_status = "PLACEHOLDER"
    cell.parameters.band = "800nm"
    cell.parameters.mechanism = "thermo_optic"
    cell.parameters.topology = "paperclip"
    cell.parameters.num_arms = num_arms
    cell.parameters.heater_resistance_ohm = pc.parameters.heater_resistance_ohm.value
    return cell


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


def _add_gc_array(cell: fw.Component, y_top: float) -> float:
    """Place the GC array + left alignment loop north of the block; return its bottom y.

    A constant-pitch row of ``_GC_PER_MZI * _NUM_ARMS`` N-S couplers led by a
    fibre-alignment loop one pitch to its left, left edge at local x = 0, all
    tops at ``y_top``. Instances ``paperclip_gc_align`` / ``paperclip_gc_array``.
    """
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(loop, name="paperclip_gc_align", x=0.0 - lb.xmin, y=y_top - lb.ymax)
    arr = _gc_line(_GC_PER_MZI * len(_NUM_ARMS))
    ab = arr.bbox
    array_xmin = lb.dx + (pitch - gc_w)
    cell.add_placed(arr, name="paperclip_gc_array", x=array_xmin - ab.xmin, y=y_top - ab.ymax)
    return min(y_top - lb.dy, y_top - ab.dy)


def _add_dc_pads(cell: fw.Component) -> None:
    """Place this block's 4-pad probe row below the MZI stack.

    ``bondpad_for_test_top`` (200 x 200 um, TOP_METAL only) on the AEPONYX
    250 um probe grid, pad 1 centred at local ``_PAD_ROW_X0``. The row
    centreline sits ``parameters.dc_test_pad_drop`` below the block top -- the
    drop the other test blocks share, so top-aligned blocks land their rows on
    one horizontal. Instances ``paperclip_dc_pad_{i}``.
    """
    pad = bondpad_for_test_top()
    pad_w = pad.bbox.dy  # rotated 90 deg -> E-W width
    pitch = pad_w + _p.dc_test_pad_spacing.value
    y_c = -_p.dc_test_pad_drop.value
    for i in range(_NUM_DC_PADS):
        cell.add_placed(
            pad, name=f"paperclip_dc_pad_{i + 1}",
            x=_PAD_ROW_X0 + i * pitch, y=y_c, rotation=90.0,
        )


@recipe
def paperclip_mzi_sweep_block() -> fw.Component:
    """The paperclip-TOPS fold-count sweep as one self-contained block.

    Local frame: x = 0 on the alignment loop's west edge, y = 0 on the GC/loop
    tops line; the DC pad row tucks slightly west of x = 0 (``_PAD_ROW_X0``).
    The die abuts this single Component against the heater block with
    ``add_aligned``.

    Content: a GC array + left alignment loop (north), the 3 paperclip-TOPS MZIs
    (num_arms 3/5/7) stacked below it, and 4 DC bond pads below those. Each MZI is
    **centred in x on the grating-coupler array** (the alignment loop west of it is
    excluded from that centre), so the three devices -- which differ in width with
    num_arms -- sit symmetrically under their couplers instead of being
    left-aligned.

    Then the wiring: heater bias metal (:func:`add_paperclip_signal_routes` +
    :func:`add_paperclip_ground_routes`) and the fibre I/O, one bundle per side --
    inputs onto the three westmost couplers (:func:`add_paperclip_input_routes`),
    outputs onto the three eastmost (:func:`add_paperclip_output_routes`), giving
    each MZI a nested ``c0<->c5`` / ``c1<->c4`` / ``c2<->c3`` pair. Input before
    output: the output bundle takes the input bundle as an obstacle.
    """
    cell = fw.Component()

    gc_bottom = _add_gc_array(cell, y_top=0.0)
    # Centre of the coupler array alone -- paperclip_gc_align (the alignment loop)
    # sits to its west and is deliberately not part of this centre.
    arr_bb = cell.instances["paperclip_gc_array"].bbox
    assert arr_bb is not None  # placed instances always have geometry
    array_cx = arr_bb.center_x

    # MZIs: top device's top a fixed gap below the GC array; stack downward.
    y_block_top = gc_bottom - _GC_TO_BLOCK_GAP
    y_input0 = None
    for i, n in enumerate(_NUM_ARMS):
        mzi = _paperclip_mzi(n)
        b = mzi.bbox
        o1 = mzi.ports["o1"].position
        if y_input0 is None:  # anchor the top device by its top edge
            y_input0 = y_block_top - (b.ymax - o1[1])
        y_input = y_input0 - i * _ROW_PITCH
        cell.add_placed(
            mzi,
            name=f"paperclip_mzi_N{n}",
            x=array_cx - b.center_x,
            y=y_input - o1[1],
        )

    # DC pads on the shared row drop (co-linear with the heater block's pads
    # once the blocks are top-aligned at die assembly).
    _add_dc_pads(cell)
    # Heater wiring, same configuration as the neighbouring heater_cr block.
    add_paperclip_signal_routes(cell)
    add_paperclip_ground_routes(cell)
    # Fibre I/O: one bundle per side, input first (the output avoids it).
    add_paperclip_input_routes(cell)
    add_paperclip_output_routes(cell)
    cell.cell_type = "test_structure"
    cell.description = (
        "Paperclip-TOPS fold-count sweep test block: 3 offset-coupler MZIs "
        "(num_arms 3/5/7) with GC fibre I/O and a 4-pad DC probe row, fully "
        "wired."
    )
    return cell


def _gc_obstacles(cell: fw.Component, name: str, *, sibling: str | None = None) -> ObstacleSet:
    """Obstacle set shared by the block's two fibre-I/O bundles.

    The three MZI bodies (a lane may bend around a device, never through it), the
    coupler array and the alignment loop. ``sibling`` adds the other bundle where
    one is already placed. The heater bias routes are deliberately **absent**: they
    are TOP_METAL, a different layer from the rib waveguide, so listing them would
    only wall off lanes that are free to cross them.
    """
    obs = ObstacleSet(name=name)
    for n in _NUM_ARMS:
        obs.add_instance(cell.instances[f"paperclip_mzi_N{n}"])
    obs.add_instance(cell.instances["paperclip_gc_array"])
    obs.add_instance(cell.instances["paperclip_gc_align"])
    if sibling is not None:
        obs.add_instance(cell.instances[sibling])
    return obs


def add_paperclip_input_routes(cell: fw.Component) -> None:
    """Bundle-route the MZI inputs (``o1``) to the three westmost couplers.

    **One autoroute call.** All three ``o1`` ports share an outward heading (west)
    and all three coupler ports share an inward heading (north), which is what lets
    a single bundle serve all three devices: west out of the stack, north up a
    corridor left of it, then east into ``c0`` / ``c1`` / ``c2`` from below.

    Lane order is the crossing-free one, and it falls out of the turn geometry:
    west->north->east is two right turns, so the **southmost** ``o1`` (``N7``, the
    bottom device) rides the outside of both and ends up the northmost lane --
    closest to the coupler line, so it peels off first onto the westmost coupler.
    Pairing bottom-to-top against ``c0``/``c1``/``c2`` west-to-east therefore keeps
    the lanes from crossing: ``N7 -> c0``, ``N5 -> c1``, ``N3 -> c2``.

    Two things differ from the heater_cr block's equivalent bundles. The devices
    **widen with** ``num_arms`` and are centred on the coupler array, so neither
    port set is co-linear -- the inputs staircase ~96 um further west per row down
    (``fan_in`` is therefore unusable; the bundle's own staircase absorbs the
    offsets). And every coupler sits *east* of every input, so this side needs the
    same forced first leg as the output side -- see ``_GC_START_STRAIGHT`` and
    ``_GC_BBOX_MARGIN``.

    Runs on ``routing_sm_default``: the large PDK Euler L-bend fits, so there is no
    reason to pay the tight bend's extra curvature loss on a measurement path --
    even though the band between the top device and the coupler line is only ~120 um
    here (``_GC_TO_BLOCK_GAP``), a third of the heater block's. The staircase is
    what buys the room: each lane climbs in its own device's shadow rather than
    nesting three turns into that band.
    """
    cell.autoroute(
        ports_a=[(f"paperclip_mzi_N{n}", "o1") for n in reversed(_NUM_ARMS)],  # bottom -> top
        ports_b=[("paperclip_gc_array", f"o1_r0_c{k}") for k in range(len(_NUM_ARMS))],
        obstacles=_gc_obstacles(cell, "paperclip_in"),
        spec="routing_sm_default",
        strategy="grid_astar",
        step=10.0,
        start_straight=_GC_START_STRAIGHT,
        bbox_margin=_GC_BBOX_MARGIN,
        name="paperclip_in",
    )


def add_paperclip_output_routes(cell: fw.Component) -> None:
    """Bundle-route the MZI outputs (``o2``) to the three eastmost couplers.

    **One autoroute call**, the mirror of :func:`add_paperclip_input_routes`: east
    out of the stack, north up a corridor right of it, then back **west** into
    ``c5`` / ``c4`` / ``c3`` from below.

    East->north->west is two *left* turns, but the southmost ``o2`` still rides the
    outside of both and still ends up the northmost lane, so it still peels off
    first -- except going west the first coupler reached is ``c5``. So the stack
    pairs bottom-to-top against ``c5``/``c4``/``c3`` east-to-west, which combined
    with the input side gives each MZI a **nested** coupler pair::

        N7: c0 <-> c5        N5: c1 <-> c4        N3: c2 <-> c3

    All six sit on one ``grating_coupling_pitch_for_tests`` row, so a 6-fibre array
    still lands the block in a single placement. Adjacent pairing would force the
    lanes to cross.

    The outputs staircase the *opposite* way to the inputs (~96 um further **east**
    per row down, and each ``o2`` also sits ~105 um above its own ``o1`` -- the
    offset-coupler topology lifts the combiner over the paperclip). Same knobs as
    the input side, and the input bundle is added as an obstacle: the two sit in
    disjoint x ranges (input reaches local x ~ 538, ``c3`` sits at ~ 655), so
    listing it makes that separation explicit rather than incidental.

    The eastward leg reaches local x ~ 1330, near the block's east bbox edge --
    and since the unbalanced-MZI ladder is abutted to this block's bbox at die
    assembly, that excursion is part of the footprint the abutment respects.
    """
    n = len(_NUM_ARMS)
    cell.autoroute(
        ports_a=[(f"paperclip_mzi_N{a}", "o2") for a in reversed(_NUM_ARMS)],  # bottom -> top
        ports_b=[("paperclip_gc_array", f"o1_r0_c{k}") for k in range(2 * n - 1, n - 1, -1)],
        obstacles=_gc_obstacles(cell, "paperclip_out", sibling="paperclip_in"),
        spec="routing_sm_default",
        strategy="grid_astar",
        step=10.0,
        start_straight=_GC_START_STRAIGHT,
        bbox_margin=_GC_BBOX_MARGIN,
        name="paperclip_out",
    )


def add_paperclip_signal_routes(cell: fw.Component) -> None:
    """Route the paperclip TOPS west heater terminals to the three west-most pads.

    Each MZI's ``e1`` terminal is the driven **signal** side of its paperclip
    heater, so each gets its own pad: ``paperclip_dc_pad_1..3``, landing on their
    north faces.

    **One bundle, not three individual routes.** These lines must be planned
    together -- routed independently they know nothing about each other and their
    metal overlaps (the union of their footprints looks identical, but the lanes
    themselves short). The bundle holds the lanes apart at the spec's lane pitch.

    Lane order: the lines leave west and turn **south** to the pads -- a left turn,
    so the lane on the outside (northmost) stays outside and lands westmost.
    Pairing the sources top-down against the pads west-to-east therefore keeps the
    three lanes from crossing.

    ``vgraph_euclid`` + ``fan_out``, matching the heater_cr block's equivalent
    bundle; ``fan_out`` absorbs the reversal the planner otherwise rejects.

    The pads' north face is the port named ``"e"``: the pads are placed
    ``rotation=90``, which rotates the port poses but not their names.
    """
    cell.autoroute(
        ports_a=[(f"paperclip_mzi_N{n}", "e1") for n in _NUM_ARMS],  # top -> bottom
        ports_b=[
            (f"paperclip_dc_pad_{i}", "e") for i in range(1, len(_NUM_ARMS) + 1)
        ],  # west -> east
        spec=_DC_SPEC,
        strategy="vgraph_euclid",
        fan_out=True,
        # DC metal may run over the cells it wires -- the terminals sit inside the
        # MZI bodies and there is no clear lane out otherwise.
        avoid_port_owners=False,
        name="paperclip_sig",
        end_straight=50.0
    )


def add_paperclip_ground_routes(cell: fw.Component) -> None:
    """Tie the paperclip TOPS east heater terminals to the last DC pad (ground).

    Each MZI's ``e2`` terminal is the heaters' **common ground**, so all three drop
    onto the *same* pad -- ``paperclip_dc_pad_4``, east of the three signal pads --
    landing on its north face.

    **One autoroute per line, not a bundle**: every line ends on the same port, so
    there is nothing for a bundle to collapse onto.
    """
    gnd_pad = (f"paperclip_dc_pad_{_NUM_DC_PADS}", "e")  # north face
    for n in _NUM_ARMS:
        cell.autoroute(
            ports_a=[(f"paperclip_mzi_N{n}", "e2")],
            ports_b=[gnd_pad],
            spec=_DC_SPEC,
            avoid_port_owners=False,
            name=f"paperclip_gnd_N{n}",
        )
