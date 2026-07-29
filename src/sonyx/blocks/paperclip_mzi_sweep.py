"""Paperclip-TOPS test — MZIs with a folded thermo-optic phase shifter, arm sweep.

Measures the folded (paperclip) thermo-optic phase shifter and how its efficiency
scales with the number of folded arms. Three MZIs, each carrying a paperclip TOPS
of a different **fold count** (num_arms = 3 / 5 / 7) on one arm; the heater is the
*same* default Cr ladder on all three, so the only variable is how many folded
arm-lengths share that one heater footprint (N=1 would be the straight-TOPS
baseline in the neighbouring heater_cr block).

Each paperclip TOPS is composed from PDK parts: ``make_paperclip`` (num_arms
folded bundle) + a centred ``heater_cr`` (mirrors ``paperclip_tops_rib_sm_800nm``,
which fixes num_arms=3). The paperclip is 150-360 um tall, so the MZI arms are
fanned with **L-bend risers** (a straight of the paperclip's height between two
90 deg bends), not S-bends.

MZI topology (offset-coupler form, by request): from the input MMI's top port,
put()-cascade lbend -> straight(=paperclip height) -> lbend -> paperclip TOPS ->
straight -> output MMI. That single upward jog leaves the output MMI offset ~240
um above the input. The reference arm then runs east **under** the paperclip at
the input level and jogs up **east** of it into the output MMI's lower port
(rising to just below the paperclip arm, so the two never cross). The paperclip
is thus offset between the two couplers. Placement-only, right of the heater_cr
block; not routed to fibre I/O or bias pads.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.bends import lbend_rib_sm_800nm, lbend_rib_sm_800nm_tight
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from luqia_ln200.cells.dc import bondpad_for_test_top, heater_cr
from luqia_ln200.cells.splitters import mmi_1x2_rib_sm_800nm_ord
from picasso.leaves import make_array, make_paperclip, make_straight
from picasso.recipe import recipe

from ..parameters import parameters as _p

# Fold-count sweep: paperclip arm counts (odd, >= 3 -- make_paperclip needs >= 2).
_NUM_ARMS: tuple[int, ...] = (3, 5, 7)

# Paperclip arm overhang past the heater active length, per side (um) -- matches
# the PDK paperclip_tops so the ladder sits clear of the bulging return loops.
_PC_ARM_MARGIN = 10.0
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

# Placement: three MZIs stacked, right of the heater_cr block (its DC pads end
# ~x -2088). Devices are left-aligned by their input port and extend up + east.
_INPUT_X = -1800.0
_ROW_PITCH = 280.0  # vertical centre-to-centre of stacked MZIs

# Grating-coupler array (north of the block) + left alignment loop, and DC bond
# pads (below the block). One in + one out coupler per MZI.
_GC_PER_MZI = 2
_TOP_MARGIN = 40.0  # coupler/loop tops below the top inner edge
_GC_TO_BLOCK_GAP = 60.0  # from the GC array bottom down to the top device's top
_NUM_DC_PADS = 4


def _straight(length: float) -> fw.Component:
    return make_straight(length=length, cross_section="rib_sm_800nm")


@recipe
def _paperclip_tops(num_arms: int) -> fw.Component:
    """Paperclip TOPS with ``num_arms`` folded arms + a centred default Cr heater.

    Composes ``make_paperclip`` (the PDK paperclip_rib fixes num_arms=3) with a
    centred ``heater_cr`` -- the folded sibling of ``tops``. Ports: ``o1``/``o2``
    (WG west/east) and ``e1``/``e2`` (heater terminals, north).
    """
    heater = heater_cr()
    hlen = heater.parameters.active_length_um.value
    arm_len = hlen + 2.0 * _PC_ARM_MARGIN
    pc = make_paperclip(
        "rib_sm_800nm",
        bend=lbend_rib_sm_800nm_tight(),
        arm_length=arm_len,
        arm_spacing=6.0,
        num_arms=num_arms,
    )
    cell = fw.Component()
    pi = cell.add_placed(pc, name="pc")
    bb = pi.bbox
    assert bb is not None
    hi = cell.add_placed(heater, name="heater", x=bb.center_x - hlen / 2.0, y=bb.center_y)
    cell.add_port("o1", (pi.name, "o1"))
    cell.add_port("o2", (pi.name, "o2"))
    cell.add_port("e1", (hi.name, "e1"))
    cell.add_port("e2", (hi.name, "e2"))
    cell.cell_type = "phase_shifter"
    cell.description = (
        f"Paperclip thermo-optic phase shifter ({num_arms}-arm folded WG + Cr "
        "ladder heater) on the 800 nm SM rib."
    )
    cell.calibration_status = "PLACEHOLDER"
    cell.parameters.mechanism = "thermo_optic"
    cell.parameters.topology = "paperclip"
    cell.parameters.num_arms = num_arms
    cell.parameters.heater_resistance_ohm = heater.parameters.resistance_ohm.value
    cell.parameters.heater_active_length_um = hlen
    return cell


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
    mi = cell.add_placed(mmi_1x2_rib_sm_800nm_ord(), name="mmi_in")
    # Top arm: up-riser -> paperclip -> output straight -> output MMI (mate its
    # o3, so the free port o2 is the LOWER combiner input).
    t1 = cell.put(lbend, (mi.name, "o2"), port_to="o1", name="t_lb1")
    pc_drop = pc.ports["o1"].position[1] - pc.ports["o2"].position[1]
    riser_len = max(pc_h - _RISER_SHORTEN, pc_drop + _RISER_MARGIN)
    t2 = cell.put(_straight(riser_len), (t1.name, "o2"), port_to="o1", name="t_str1")
    t3 = cell.put(lbend, (t2.name, "o2"), port_to="o1", name="t_lb2", mirror=True)
    tp = cell.put(pc, (t3.name, "o2"), port_to="o1", name="paperclip")
    ts = cell.put(_straight(_TOP_OUT_STRAIGHT), (tp.name, "o2"), port_to="o1", name="t_str2")
    mo = cell.put(mmi_1x2_rib_sm_800nm_ord(), (ts.name, "o2"), port_to="o3", name="mmi_out")

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
    fibre-alignment loop one pitch to its left, left edge at ``_INPUT_X``, all
    tops at ``y_top``. Instances ``paperclip_gc_align`` / ``paperclip_gc_array``.
    """
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(loop, name="paperclip_gc_align", x=_INPUT_X - lb.xmin, y=y_top - lb.ymax)
    arr = _gc_line(_GC_PER_MZI * len(_NUM_ARMS))
    ab = arr.bbox
    array_xmin = (_INPUT_X + lb.dx) + (pitch - gc_w)
    cell.add_placed(arr, name="paperclip_gc_array", x=array_xmin - ab.xmin, y=y_top - ab.ymax)
    return min(y_top - lb.dy, y_top - ab.dy)


def _add_dc_pads(cell: fw.Component) -> None:
    """Place ``_NUM_DC_PADS`` TOP_METAL DC test bond pads, aligned to the left cells.

    ``bondpad_for_test_top`` (400 x 200 um, TOP_METAL only) rotated 90 deg so the
    long side runs N-S (200 um E-W x 400 um N-S) -- the layout convention for DC
    test pads -- in a row, pitch = pad width + ``dc_test_pad_spacing``, left edge
    at ``_INPUT_X``. The row centreline is ``parameters.dc_test_pad_row_y``, shared
    with the heater_cr block's pads so the two align. Instances
    ``paperclip_dc_pad_{i}``.
    """
    pad = bondpad_for_test_top()
    pad_w_rot = pad.bbox.dy  # rotated 90 deg -> E-W width is the pad's original y-extent
    pitch = pad_w_rot + _p.dc_test_pad_spacing.value
    y_c = _p.dc_test_pad_row_y.value
    for i in range(_NUM_DC_PADS):
        cell.add_placed(
            pad, name=f"paperclip_dc_pad_{i + 1}",
            x=(_INPUT_X + pad_w_rot / 2.0) + i * pitch, y=y_c, rotation=90.0,
        )


def add_paperclip_mzi_sweep(cell: fw.Component) -> None:
    """Place the paperclip-TOPS test block, right of the heater_cr block.

    A GC array + left alignment loop (north), the 3 paperclip-TOPS MZIs
    (num_arms 3/5/7) stacked below it, and 4 DC bond pads below those. Devices
    are left-aligned by their input port at ``_INPUT_X``. Placement-only.
    """
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value

    gc_bottom = _add_gc_array(cell, y_top=(half_h - kw) - _TOP_MARGIN)

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
        cell.add_placed(mzi, name=f"paperclip_mzi_N{n}", x=_INPUT_X - o1[0], y=y_input - o1[1])

    # DC pads on the same row as the heater_cr block's pads (left cells).
    _add_dc_pads(cell)
