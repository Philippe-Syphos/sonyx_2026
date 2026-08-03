"""Thermo-optic phase-shifter test — balanced MZIs with a swept heater length.

A set of **balanced** Mach-Zehnder interferometers (arm imbalance dL = 0), each
carrying a Cr ladder heater (:func:`luqia_ln200.cells.dc.heater_cr`) of a
*different active length* on the top arm and a length-matched plain waveguide on
the bottom. With dL = 0 the only interferometric phase comes from the heater, so
sweeping the heater length across the set and measuring each MZI's transfer vs.
drive power maps the thermo-optic phase shifter: the short-heater P_pi rolloff /
plateau, the thermal time constant (~proportional to length), and -- since the
ladder resistance R scales with the section count -- the V_pi = sqrt(P_pi*R)
drive point (V_pi ~ sqrt(L) at ~fixed thermal efficiency).

Length is swept via the ladder's series-section count ``sections`` (M): active
length ~proportional to M*N_p and R ~proportional to M/N_p, so with N_p fixed,
``M`` walks the active length (and R rises with it). All M are **even** so both
heater terminals land on the north band, away from the bottom arm.

Each device (built purely from PDK cells via ``put()``):

    mmi_1x2 (split) -> wide S-bend splay -> heated arm (top) / matched plain WG
    (bottom) -> wide S-bend splay-back -> mmi_1x2 (combine)

Fibre I/O is a single constant-pitch N-S grating-coupler array
(``gratingcoupler_rib_sm_800nm_ext``, input from the north) + a fibre-alignment
loop, in the die's top-left corner -- same convention as the other test cells.
The MZIs stack vertically below the array. Placement-only: the MZI optical ports
are not routed to the couplers, and the heater terminals are not routed to pads.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.bends import sbend_rib_sm_800nm_wide
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from luqia_ln200.cells.dc import bondpad_for_test_top, heater_cr
from luqia_ln200.cells.splitters import mmi_1x2_rib_sm_800nm_ord
from luqia_ln200.cells.waveguides import straight_rib_sm_800nm
from picasso.leaves import make_array
from picasso.recipe import recipe

from ..parameters import parameters as _p

# Heater length map: ladder series-section counts M (even -> both terminals
# north). Active length ~proportional to M*N_p, R ~proportional to M/N_p; with
# the default N_p=5 these give active ~92..568 um and R ~42..250 ohm.
_HEATER_SECTIONS: tuple[int, ...] = (4, 8, 12, 16, 20, 24)

# One input + one output grating coupler per MZI.
_GC_PER_MZI = 2
_NUM_MZI = len(_HEATER_SECTIONS)

# Gaps (um) from the die inner edges (past the 50 um keepout) to the GC array:
# the alignment loop's left edge sits _LEFT_MARGIN off the left inner edge, and
# the coupler/loop tops sit _TOP_MARGIN below the top inner edge. Both coupler
# groups, both MZI columns and the DC pad row key off _LEFT_MARGIN, so it is the
# single knob that slides the whole block east/west.
_LEFT_MARGIN = 1250.0
_TOP_MARGIN = 40.0

# MZI columns (below the GC array). The couplers + MZIs split into two
# routing groups: a left group (left loop + first coupler half + first MZI half)
# and a right group (mid loop + second coupler half + second MZI half), so each
# MZI half routes locally up to its own coupler half. The right group is pushed
# _RIGHT_BLOCK_GAP beyond the pitch-continuous position to separate the two.
_RIGHT_BLOCK_GAP = 150.0  # extra x-separation of the right group from the left
# Extra eastward offset (um) of the east MZI column only, on top of the pin to its
# group's first real coupler (the couplers and pads do not move).
_EAST_COLUMN_SHIFT = 350.0
# Top MZI axis (both columns) below the top inner edge; deep enough to leave
# routing room between the coupler line and the MZIs.
_MZI_TOP_DROP = 400.0
_MZI_ROW_PITCH = 120.0  # vertical centre-to-centre of stacked MZIs (~76 um tall)

# DC heater-bias test bond pads: a row of _NUM_DC_PADS TOP_METAL-only test pads
# (bondpad_for_test_top, 200 x 200 um per the AEPONYX probe convention -- the
# heater terminals are already on routing_top_metal, so no via at the pad).
# Pitch = pad width + parameters.dc_test_pad_spacing = 250 um (the convention).
# The row centreline is parameters.dc_test_pad_row_y (shared with the other test
# cells). This block's 8 pads and the paperclip block's 4 form ONE continuous
# 12-pad row on the 250 um grid (an AEPONYX probe card lands 9 needles at that
# pitch, so any 9-consecutive window must be gapless metal): this row is slid
# _PAD_ROW_EAST_SHIFT east of _LEFT_MARGIN and the paperclip pads continue the
# grid at indices 8..11 (see :func:`dc_pad_center_x`), meeting roughly midway
# between the two blocks' old row positions.
_NUM_DC_PADS = 8
_PAD_ROW_EAST_SHIFT = 650.0


@recipe
def _heated_arm(sections: int) -> fw.Component:
    """One MZI arm: a rib WG straight with a Cr ladder heater of ``sections`` M over it.

    The heater's active length sets the WG length (so the whole arm is heated),
    matching :func:`luqia_ln200.cells.modulators.tops_rib_sm_800nm` but with the
    ladder ``sections`` exposed for the length sweep. Ports: ``o1``/``o2`` (WG,
    west/east) and ``e1``/``e2`` (heater terminals, north-facing axial).
    """
    heater = heater_cr(sections=sections)
    active = heater.parameters.active_length_um.value
    wg = straight_rib_sm_800nm(length=active)
    arm = fw.Component()
    wg_inst = arm.add_placed(wg, name="wg")
    heater_inst = arm.add_placed(heater, name="heater", x=0.0, y=0.0)
    arm.add_port("o1", (wg_inst.name, "o1"))
    arm.add_port("o2", (wg_inst.name, "o2"))
    arm.add_port("e1", (heater_inst.name, "e1"))
    arm.add_port("e2", (heater_inst.name, "e2"))
    arm.cell_type = "phase_shifter"
    arm.parameters.heater_sections = sections
    arm.parameters.heater_active_length_um = active
    arm.parameters.heater_resistance_ohm = heater.parameters.resistance_ohm.value
    return arm


@recipe
def _balanced_mzi_tops(sections: int) -> fw.Component:
    """Balanced 1x2-MMI MZI with a ``sections``-M ladder heater on the top arm.

    Two ``mmi_1x2_rib_sm_800nm_ord`` splitters back-to-back; the outputs are
    fanned apart by a wide S-bend per arm (top up, bottom down) so the heater
    clears the lower arm, then fanned back for the combiner. The top arm is a
    :func:`_heated_arm` (WG + heater); the bottom arm is a plain WG of the
    **same length**, so the interferometer is balanced (dL = 0) and all phase
    comes from the heater. Ports: ``o1`` (input, west) / ``o2`` (output, east) /
    ``e1``/``e2`` (heater terminals). Built via ``put()`` -- every abutment a Net.
    """
    mmi_in = mmi_1x2_rib_sm_800nm_ord()
    mmi_out = mmi_1x2_rib_sm_800nm_ord()
    sbw = sbend_rib_sm_800nm_wide()
    top = _heated_arm(sections)
    active = top.parameters.heater_active_length_um.value
    bot = straight_rib_sm_800nm(length=active)  # matched -> balanced

    cell = fw.Component()
    mi = cell.add_placed(mmi_in, name="mmi_in")
    # Fan the two MMI outputs apart: top (o2) up, bottom (o3) down (mirrored).
    su = cell.put(sbw, (mi.name, "o2"), port_to="o1", name="splay_up")
    sd = cell.put(sbw, (mi.name, "o3"), port_to="o1", name="splay_dn", mirror=True)
    # Arms (equal optical length).
    ta = cell.put(top, (su.name, "o2"), port_to="o1", name="top_arm")
    ba = cell.put(bot, (sd.name, "o2"), port_to="o1", name="bot_arm")
    # Fan back to the MMI output pitch (mirror flags reversed vs the splay).
    fu = cell.put(sbw, (ta.name, "o2"), port_to="o1", name="fan_up", mirror=True)
    fd = cell.put(sbw, (ba.name, "o2"), port_to="o1", name="fan_dn")
    # Combiner MMI: mate its o3 to the top return; record the bottom join as a Net.
    mo = cell.put(mmi_out, (fu.name, "o2"), port_to="o3", name="mmi_out")
    cell.connect((fd.name, "o2"), (mo.name, "o2"))

    cell.add_port("o1", (mi.name, "o1"))
    cell.add_port("o2", (mo.name, "o1"))
    cell.add_port("e1", (ta.name, "e1"))
    cell.add_port("e2", (ta.name, "e2"))
    cell.cell_type = "mzi"
    cell.description = (
        "Balanced 1x2-MMI Mach-Zehnder on the 800 nm SM rib (ord-axis) with a "
        f"Cr ladder heater (sections M={sections}) on the top arm -- thermo-optic "
        "phase-shifter length-sweep test cell."
    )
    cell.calibration_status = "PLACEHOLDER"
    cell.parameters.band = "800nm"
    cell.parameters.axis = "ord"
    cell.parameters.mechanism = "thermo_optic"
    cell.parameters.length_imbalance_um = 0.0
    cell.parameters.heater_sections = sections
    cell.parameters.heater_active_length_um = active
    cell.parameters.heater_resistance_ohm = top.parameters.heater_resistance_ohm.value
    return cell


@recipe
def _gc_line(num: int) -> fw.Component:
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


def _gc_group_left_edges() -> tuple[float, float]:
    """Left-edge x of the left and right coupler/MZI groups.

    The left group's left edge (the far-left alignment loop) sits ``_LEFT_MARGIN``
    off the left inner edge. The right group (mid loop + second coupler half)
    would continue the constant pitch immediately after the left half; it is
    instead pushed a further ``_RIGHT_BLOCK_GAP`` right to separate the two
    routing groups. Both the couplers and the MZI columns anchor to these.
    """
    half_w = _p.die_width.value / 2.0
    kw = _p.keepout_width.value
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    gap = pitch - gc_w  # keeps adjacent GC centres one pitch apart within a group
    loop_dx = gratingcoupler_alignment_rib_sm_800nm_ext().bbox.dx
    line_l_dx = _gc_line((_GC_PER_MZI * _NUM_MZI) // 2).bbox.dx

    left_x = (-half_w + kw) + _LEFT_MARGIN
    right_x = left_x + (loop_dx + gap) + (line_l_dx + gap) + _RIGHT_BLOCK_GAP
    return left_x, right_x


def _add_gc_array(cell: fw.Component) -> None:
    """Place the sweep's GC array + alignment loops, top-left of the die.

    ``_GC_PER_MZI * _NUM_MZI`` N-S grating couplers split into two equal halves,
    each a constant-pitch group led by a fibre-alignment loop (the loop is two
    couplers wide, so it occupies two pitch slots): a left group (far-left loop +
    first half) and a right group (mid loop + second half). Within each group the
    ``grating_coupling_pitch`` grid is continuous; the right group is offset
    ``_RIGHT_BLOCK_GAP`` further right (see :func:`_gc_group_left_edges`). All
    coupler/loop tops sit ``_TOP_MARGIN`` below the top inner edge.

    Instances: ``heater_mzi_gc_align_l`` / ``heater_mzi_gc_align_mid`` (loops)
    and ``heater_mzi_gc_array_l`` / ``heater_mzi_gc_array_r`` (the two coupler
    halves, ports ``o1_r0_cN``, left open for later routing to the MZIs).
    """
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    gap = pitch - gc_w
    y_top = (half_h - kw) - _TOP_MARGIN

    n_total = _GC_PER_MZI * _NUM_MZI
    n_left = n_total // 2
    line_l = _gc_line(n_left)
    line_r = _gc_line(n_total - n_left)
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    left_x, right_x = _gc_group_left_edges()

    def place(sub: fw.Component, name: str, x_left: float) -> None:
        b = sub.bbox
        cell.add_placed(sub, name=name, x=x_left - b.xmin, y=y_top - b.ymax)

    # Left group: far-left loop, then couplers 1..n_left one pitch onward.
    place(loop, "heater_mzi_gc_align_l", left_x)
    place(line_l, "heater_mzi_gc_array_l", left_x + loop.bbox.dx + gap)
    # Right group: mid loop (offset by _RIGHT_BLOCK_GAP), then couplers n_left+1..n_total.
    place(loop, "heater_mzi_gc_align_mid", right_x)
    place(line_r, "heater_mzi_gc_array_r", right_x + loop.bbox.dx + gap)


def _add_devices(cell: fw.Component) -> None:
    """Place the balanced-MZI heater sweep as two columns below the GC array.

    The MZIs split into two columns matching the coupler halves: the first
    ``_NUM_MZI // 2`` (shorter heaters) form the left column under the left
    coupler group, the rest the right column under the right coupler group. Each
    column stacks downward at ``_MZI_ROW_PITCH`` from the same top axis.

    Each column's **west edge is pinned to its group's first real grating coupler**
    -- the first one that is not the fibre-alignment loop. The loop is two couplers
    wide, so that is the third coupler slot of the group and the ``c0`` port of the
    group's array. The MZI's ``o1`` (its westmost point) lands on that coupler's x,
    so the input drops straight down from it. The east column is then offset a
    further ``_EAST_COLUMN_SHIFT`` east. Instances ``heater_mzi_M{M}``.

    Must run after :func:`_add_gc_array` -- it reads the placed coupler arrays.
    """
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    y_axis0 = (half_h - kw) - _MZI_TOP_DROP

    split = _NUM_MZI // 2
    columns = (
        ("heater_mzi_gc_array_l", _HEATER_SECTIONS[:split], 0.0),
        ("heater_mzi_gc_array_r", _HEATER_SECTIONS[split:], _EAST_COLUMN_SHIFT),
    )
    for array_name, sections, shift in columns:
        # First non-alignment coupler of this group = the array's c0 port.
        x_in = cell.instances[array_name].ports["o1_r0_c0"].position[0] + shift
        for i, m in enumerate(sections):
            mzi = _balanced_mzi_tops(m)
            # o1 (input) sits at local (0, 0); place it directly at (x_in, y_axis).
            cell.add_placed(mzi, name=f"heater_mzi_M{m}", x=x_in, y=y_axis0 - i * _MZI_ROW_PITCH)


def dc_pad_center_x(index: int) -> float:
    """Centre x of pad ``index`` (0-based) on R4B's continuous 12-pad probe row.

    One 250 um grid shared by this block (indices 0..7) and the paperclip
    block (8..11, via its ``_add_dc_pads``), so an AEPONYX 9-needle probe
    card lands on gapless metal anywhere along the row. Pad 0's left edge
    sits ``_LEFT_MARGIN + _PAD_ROW_EAST_SHIFT`` off the left inner edge.
    """
    pad_w = bondpad_for_test_top().bbox.dy  # rotated 90 deg -> E-W width
    pitch = pad_w + _p.dc_test_pad_spacing.value
    half_w = _p.die_width.value / 2.0
    kw = _p.keepout_width.value
    x0 = ((-half_w + kw) + _LEFT_MARGIN + _PAD_ROW_EAST_SHIFT) + pad_w / 2.0
    return x0 + index * pitch


def _add_dc_pads(cell: fw.Component) -> None:
    """Place this block's 8 pads (row indices 0..7) of the shared 12-pad row.

    ``bondpad_for_test_top`` (200 x 200 um, TOP_METAL only) on the AEPONYX
    250 um probe grid (:func:`dc_pad_center_x`), the row centreline at
    ``parameters.dc_test_pad_row_y``. The paperclip block continues the same
    grid with pads 8..11. Instances ``dc_pad_{i}``.
    """
    pad = bondpad_for_test_top()
    y_row_c = _p.dc_test_pad_row_y.value
    for i in range(_NUM_DC_PADS):
        cell.add_placed(
            pad, name=f"dc_pad_{i + 1}", x=dc_pad_center_x(i), y=y_row_c, rotation=90.0
        )


# Pad allocation per MZI column: three signal pads then one shared ground pad, so
# the west column takes dc_pad_1..4 and the east column dc_pad_5..8.
_PADS_PER_COLUMN = 4


def _column_mzis(column: int) -> list[str]:
    """Instance names of ``column``'s MZIs, **top to bottom** (0 = west, 1 = east)."""
    split = _NUM_MZI // 2
    sections = _HEATER_SECTIONS[:split] if column == 0 else _HEATER_SECTIONS[split:]
    return [f"heater_mzi_M{m}" for m in sections]


def add_heater_mzi_signal_routes(cell: fw.Component, column: int) -> None:
    """Route one column's west heater terminals to its three signal pads.

    A column's ``e1`` terminals are the driven **signal** side of each Cr ladder
    heater, so each gets its own pad: the first three of that column's four
    (``dc_pad_1..3`` west, ``dc_pad_5..7`` east), landing on their north faces.

    A **single** autoroute: the ``e1`` terminals all sit on one vertical line (x is
    set by the column, not by the swept heater length), which is what a bundle
    needs -- and they end on three distinct pads 400 um apart, so there is a real
    corridor to collapse into. The ``e2`` terminals could not be bundled: the heater
    length is what the sweep varies, so they are not co-linear.

    Lane order: the lines leave west and turn **south** to the pads -- a left turn,
    so the lane on the outside (northmost) stays outside and lands westmost.
    Pairing the sources top-down against the pads west-to-east therefore keeps the
    three lanes from crossing.

    ``grid_astar`` rather than the default ``vgraph_rect``, which finds no path to
    the goal gateway for this bundle.

    The pads' north face is the port named ``"e"``: the pads are placed
    ``rotation=90``, which rotates the port poses but not their names.
    """
    mzis = _column_mzis(column)  # top -> bottom
    first_pad = column * _PADS_PER_COLUMN + 1
    cell.autoroute(
        ports_a=[(name, "e1") for name in mzis],
        ports_b=[(f"dc_pad_{first_pad + k}", "e") for k in range(len(mzis))],  # west->east
        spec="routing_top_metal",
        strategy="grid_astar",
        # step=10 makes the A* grid ~20x more expensive here (the grid scales
        # O(N^2) with the search-area side) for the same resulting path: 25 um
        # plans this bundle in ~90 ms instead of ~1.7 s, bbox unchanged.
        step=25.0,
        # DC metal may run over the cells it wires -- the terminals sit inside the
        # MZI bodies and there is no clear lane out otherwise.
        avoid_port_owners=False,
        name=f"heater_mzi_sig_{'west' if column == 0 else 'east'}",
    )


def add_heater_mzi_ground_routes(cell: fw.Component, column: int) -> None:
    """Tie one column's east heater terminals to that column's ground pad.

    A column's ``e2`` terminals are the heaters' **common ground**, so all three
    drop onto the *same* pad -- the last of that column's four (``dc_pad_4`` west,
    ``dc_pad_8`` east) -- landing on its north face.

    **One autoroute per line, not a bundle**, for two reasons: every line ends on
    the same port, so there is nothing for a bundle to collapse onto; and the ``e2``
    terminals are not co-linear (the heater length is what the sweep varies, so each
    MZI's east terminal sits at a different x), which a bundle requires.
    """
    mzis = _column_mzis(column)
    gnd_pad = (f"dc_pad_{(column + 1) * _PADS_PER_COLUMN}", "e")  # north face
    side = "west" if column == 0 else "east"
    for mzi_name in mzis:
        cell.autoroute(
            ports_a=[(mzi_name, "e2")],
            ports_b=[gnd_pad],
            spec="routing_top_metal",
            avoid_port_owners=False,
            name=f"heater_mzi_gnd_{side}_{mzi_name.removeprefix('heater_mzi_')}",
        )


def add_heater_mzi_sweep(cell: fw.Component) -> None:
    """Place the thermo-optic phase-shifter length sweep, top-left of the die.

    The top-left GC array + alignment loops, the ``_NUM_MZI`` balanced 1x2-MMI
    MZIs (two columns) with swept heater length, and a row of DC heater-bias test
    bond pads below them, then each column's heater wiring: the three ``e1``
    signals to that column's three signal pads
    (:func:`add_heater_mzi_signal_routes`) and the three ``e2`` terminals tied to
    its shared ground pad (:func:`add_heater_mzi_ground_routes`) -- west column on
    ``dc_pad_1..4``, east column on ``dc_pad_5..8``. The optical I/O is still
    unrouted.
    """
    _add_gc_array(cell)
    _add_devices(cell)
    _add_dc_pads(cell)
    for column in (0, 1):  # 0 = west, 1 = east
        add_heater_mzi_signal_routes(cell, column)
        add_heater_mzi_ground_routes(cell, column)
