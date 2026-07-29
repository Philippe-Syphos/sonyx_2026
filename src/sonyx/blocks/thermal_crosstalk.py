"""Thermal-crosstalk test cell (R3A) -- first draft, placement-only.

A single Cr heater line with a vertical stack of balanced MZI "thermometers"
below it at increasing distance. Driving the heater raises the local temperature;
each balanced MZI (arms fanned top/bottom, dL = 0) converts the thermal gradient
across its arms into an output shift, and a heater-power sweep traces that shift.
Stacking the MZIs at increasing distance from the heater maps the thermal
crosstalk decay delta-T(distance).

Layout (top-down): GC array + alignment loop (MZI fibre I/O), the heater line,
then ``_NUM_MZI`` balanced MZIs stacked downward. Two TOP_METAL heater-bias bond
pads (``bondpad_for_test_top``, same as the R4B TOPS test) sit on the shared DC
test-pad row. Placement only -- optical ports not routed to the couplers and the
heater terminals not routed to the pads.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.bends import sbend_rib_sm_800nm
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from luqia_ln200.cells.dc import bondpad_for_test_top, heater_cr
from luqia_ln200.cells.splitters import mmi_1x2_rib_sm_800nm_ord
from luqia_ln200.cells.waveguides import straight_rib_sm_800nm
from picasso.component import PortSpec
from picasso.leaves import make_array
from picasso.recipe import recipe

from ..parameters import parameters as _p

_NUM_MZI = 5  # balanced-MZI thermometers stacked under the heater
_MZI_ARM = 150.0  # each MZI arm length (um) -- longer = more phase per delta-T
_MZI_GAP = 0.0  # gap between stacked MZI bboxes (touching); the moat isolates them optically
_HEATER_SECTIONS = 10  # Cr ladder heater (~235 um active, ~100 ohm) -- the source
_HEATER_GAP = 45.0  # gap from the bottom MZI to the heater below it
_GC_ROW_GAP = 250.0  # gap from the GC array to the heater
_MZI_X_OFFSET = 250.0  # MZI left edge right of the alignment loop (routing room)

# Placement on R3A: to the right of the crossing-MZI blocks, top band.
_TC_LEFT_MARGIN = 2050.0  # left edge off the left inner edge (+250 for routing room)
_TC_TOP_MARGIN = 40.0  # GC tops below the top inner edge


@recipe
def _balanced_mzi_plain(arm_length: float) -> fw.Component:
    """Balanced 1x2-MMI MZI (dL = 0), plain arms -- a passive thermal sensor.

    Two ``mmi_1x2_rib_sm_800nm_ord`` splitters back-to-back; each output is fanned
    apart by an S-bend (top up, bottom down) into an ``arm_length`` plain
    straight, then fanned back for the combiner. No heater -- the arms sense an
    external thermal gradient (top arm warmer than bottom when a heater sits
    above). Ports ``o1`` (west) / ``o2`` (east). Built via ``put()``.
    """
    sbw = sbend_rib_sm_800nm()
    arm = straight_rib_sm_800nm(length=arm_length)
    cell = fw.Component()
    mi = cell.add_placed(mmi_1x2_rib_sm_800nm_ord(), name="mmi_in")
    su = cell.put(sbw, (mi.name, "o2"), port_to="o1", name="splay_up")
    sd = cell.put(sbw, (mi.name, "o3"), port_to="o1", name="splay_dn", mirror=True)
    ta = cell.put(arm, (su.name, "o2"), port_to="o1", name="top_arm")
    ba = cell.put(arm, (sd.name, "o2"), port_to="o1", name="bot_arm")
    fu = cell.put(sbw, (ta.name, "o2"), port_to="o1", name="fan_up", mirror=True)
    fd = cell.put(sbw, (ba.name, "o2"), port_to="o1", name="fan_dn")
    mo = cell.put(mmi_1x2_rib_sm_800nm_ord(), (fu.name, "o2"), port_to="o3", name="mmi_out")
    cell.connect((fd.name, "o2"), (mo.name, "o2"))
    cell.add_port("o1", (mi.name, "o1"))
    cell.add_port("o2", (mo.name, "o1"))
    cell.cell_type = "mzi"
    cell.calibration_status = "PLACEHOLDER"
    cell.parameters.band = "800nm"
    cell.parameters.length_imbalance_um = 0.0
    cell.parameters.arm_length_um = arm_length
    return cell


def add_thermal_crosstalk(cell: fw.Component) -> None:
    """Place the thermal-crosstalk cell on R3A, right of the crossing MZIs.

    Top-down: GC array + alignment loop, the heater line (centred over the MZI
    arm region), then ``_NUM_MZI`` balanced MZIs stacked downward at increasing
    distance from the heater. Two heater-bias bond pads sit on the shared DC row.
    Placement only. Instances ``thermal_gc_align`` / ``thermal_gc_array`` /
    ``thermal_heater`` / ``thermal_mzi_{i}`` / ``thermal_dc_pad_{1,2}``.
    """
    half_w = _p.die_width.value / 2.0
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx

    x_left = (-half_w + kw) + _TC_LEFT_MARGIN
    y_top = (half_h - kw) - _TC_TOP_MARGIN

    # GC array (2 per MZI) + alignment loop, tops at y_top.
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(loop, name="thermal_gc_align", x=x_left - lb.xmin, y=y_top - lb.ymax)
    arr = make_array(
        template=gratingcoupler_rib_sm_800nm_ext(), rows=1, cols=2 * _NUM_MZI, dx=pitch, dy=0.0
    )
    ab = arr.bbox
    array_xmin = (x_left + lb.dx) + (pitch - gc_w)
    cell.add_placed(arr, name="thermal_gc_array", x=array_xmin - ab.xmin, y=y_top - ab.ymax)

    # MZI stack directly below the GC row (top MZI closest to the couplers),
    # started _MZI_X_OFFSET right of the alignment loop for routing room.
    mzi0 = _balanced_mzi_plain(_MZI_ARM)
    mb = mzi0.bbox
    mzi_x_left = (x_left + lb.dx) + _MZI_X_OFFSET
    mzi_top_axis = (y_top - max(lb.dy, ab.dy)) - _GC_ROW_GAP - mb.ymax
    for i in range(_NUM_MZI):
        cell.add_placed(
            _balanced_mzi_plain(_MZI_ARM),
            name=f"thermal_mzi_{i}",
            x=mzi_x_left - mb.xmin,
            y=mzi_top_axis - i * (mb.dy + _MZI_GAP),
        )

    # Heater below the bottom MZI -- same side as the bond pads, so its terminals
    # reach the DC row without crossing the MZI stack. Centred over the arm region.
    heater = heater_cr(sections=_HEATER_SECTIONS)
    hb = heater.bbox
    heater_cx = mzi_x_left + mb.dx / 2.0
    bottom_mzi_c = mzi_top_axis - (_NUM_MZI - 1) * (mb.dy + _MZI_GAP)
    y_heater_c = (bottom_mzi_c + mb.ymin) - _HEATER_GAP - hb.dy / 2.0
    cell.add_placed(
        heater,
        name="thermal_heater",
        x=heater_cx - hb.dx / 2.0 - hb.xmin,
        y=y_heater_c - hb.dy / 2.0 - hb.ymin,
    )

    # Two heater-bias bond pads on the shared DC test-pad row (as on R4B TOPS),
    # rotated 90 deg (long side N-S). First pad's left edge at x_left.
    pad = bondpad_for_test_top()
    pad_w_rot = pad.bbox.dy
    pad_pitch = pad_w_rot + _p.dc_test_pad_spacing.value
    x_pad0 = x_left + pad_w_rot / 2.0
    for i in range(2):
        cell.add_placed(
            pad,
            name=f"thermal_dc_pad_{i + 1}",
            x=x_pad0 + i * pad_pitch,
            y=_p.dc_test_pad_row_y.value,
            rotation=90.0,
        )

    # Autoroute the 5 leftmost GCs to the MZI left inputs as a single bundle
    # (tight routing spec, vgraph_rect default). No obstacle set: the routes run
    # down the left channel into the west-facing o1 ports and never cross the MZI
    # bodies (which extend east). A whole-layer WG_RIB obstacle set would be the
    # entire die (~2300 polygons, slow) and would also wall off the target ports.
    gc_ports: list[PortSpec] = [("thermal_gc_array", f"o1_r0_c{i}") for i in range(_NUM_MZI)]
    mzi_ports: list[PortSpec] = [(f"thermal_mzi_{i}", "o1") for i in range(_NUM_MZI)]
    cell.autoroute(
        ports_b=gc_ports,
        ports_a=mzi_ports,
        spec="routing_sm_tight",
        # avoid_port_owners=True,
        name="thermal_routes",
        strategy="grid_astar",
        step=10.0
    )

    # Autoroute the MZI outputs (east-facing o2) to the 5 rightmost GCs as a
    # second bundle. The routes exit east, clear of the MZI stack (bodies extend
    # east but the o2 ports are their eastmost points), then run north up the
    # right channel into the couplers. Same tight spec / no obstacle set as the
    # input bundle.
    gc_out_ports: list[PortSpec] = [
        ("thermal_gc_array", f"o1_r0_c{_NUM_MZI + i}") for i in range(_NUM_MZI)
    ]
    mzi_out_ports: list[PortSpec] = [(f"thermal_mzi_{i}", "o2") for i in range(_NUM_MZI)]
    cell.autoroute(
        ports_b=gc_out_ports,
        ports_a=mzi_out_ports,
        spec="routing_sm_tight",
        name="thermal_routes_out",
        strategy="grid_astar",
        step=10.0,
        fan_out=True
    )
