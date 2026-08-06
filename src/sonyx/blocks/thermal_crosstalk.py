"""Thermal-crosstalk test cell (R3A) -- first draft, placement-only.

A single Cr heater line with a vertical stack of balanced MZI "thermometers"
below it at increasing distance. Driving the heater raises the local temperature;
each balanced MZI (arms fanned top/bottom, dL = 0) converts the thermal gradient
across its arms into an output shift, and a heater-power sweep traces that shift.
Stacking the MZIs at increasing distance from the heater maps the thermal
crosstalk decay delta-T(distance).

Layout (top-down): GC array + alignment loop (MZI fibre I/O), the heater line,
then ``_NUM_MZI`` balanced MZIs stacked downward. A full 9-pad TOP_METAL probe
row (``bondpad_for_test_top``, same as the R4B TOPS test) sits on the shared DC
test-pad row -- the AEPONYX automated-probe provision (9 pads at the 250 um
pitch, every needle landing on metal, first pad always used) -- with only the
two westmost pads wired to the heater bias.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.bends import sbend_rib_sm_800nm
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from luqia_ln200.cells.dc import bondpad_for_test_top, heater_cr
from luqia_ln200.cells.splitters import mmi_1x2_rib_sm_800nm_ord_6um
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

# Probe pads on the shared DC test-pad row: the AEPONYX automated-probe card
# expects a provision for 9 pads (250 um pitch) with every needle landing on
# metal and the first (westmost) pad always used -- so the heater bias takes
# pads 1-2 and pads 3-9 are unwired landing metal.
_NUM_DC_PADS = 9


@recipe
def _balanced_mzi_plain(arm_length: float) -> fw.Component:
    """Balanced 1x2-MMI MZI (dL = 0), plain arms -- a passive thermal sensor.

    Two ``mmi_1x2_rib_sm_800nm_ord_6um`` splitters back-to-back; each output is fanned
    apart by an S-bend (top up, bottom down) into an ``arm_length`` plain
    straight, then fanned back for the combiner. No heater -- the arms sense an
    external thermal gradient (top arm warmer than bottom when a heater sits
    above). Ports ``o1`` (west) / ``o2`` (east). Built via ``put()``.
    """
    sbw = sbend_rib_sm_800nm()
    arm = straight_rib_sm_800nm(length=arm_length)
    cell = fw.Component()
    mi = cell.add_placed(mmi_1x2_rib_sm_800nm_ord_6um(), name="mmi_in")
    su = cell.put(sbw, (mi.name, "o2"), port_to="o1", name="splay_up")
    sd = cell.put(sbw, (mi.name, "o3"), port_to="o1", name="splay_dn", mirror=True)
    ta = cell.put(arm, (su.name, "o2"), port_to="o1", name="top_arm")
    ba = cell.put(arm, (sd.name, "o2"), port_to="o1", name="bot_arm")
    fu = cell.put(sbw, (ta.name, "o2"), port_to="o1", name="fan_up", mirror=True)
    fd = cell.put(sbw, (ba.name, "o2"), port_to="o1", name="fan_dn")
    mo = cell.put(mmi_1x2_rib_sm_800nm_ord_6um(), (fu.name, "o2"), port_to="o3", name="mmi_out")
    cell.connect((fd.name, "o2"), (mo.name, "o2"))
    cell.add_port("o1", (mi.name, "o1"))
    cell.add_port("o2", (mo.name, "o1"))
    cell.cell_type = "mzi"
    cell.calibration_status = "PLACEHOLDER"
    cell.parameters.band = "800nm"
    cell.parameters.length_imbalance_um = 0.0
    cell.parameters.arm_length_um = arm_length
    return cell


@recipe
def thermal_crosstalk_block() -> fw.Component:
    """The thermal-crosstalk test as one self-contained block.

    Local frame: x = 0 on the alignment loop's west edge, y = 0 on the GC/loop
    tops line (the block's top-left content anchor); the probe row sits
    ``parameters.dc_test_pad_drop`` below the top. The die places this single
    Component with ``add_placed``.

    Top-down: GC array + alignment loop, the heater line (centred over the MZI
    arm region), then ``_NUM_MZI`` balanced MZIs stacked downward at increasing
    distance from the heater. A ``_NUM_DC_PADS``-pad probe row sits on the shared
    DC row drop (the AEPONYX 9-pad provision); the heater bias wires to pads 1-2
    and the rest are unwired landing metal. Instances ``thermal_gc_align`` /
    ``thermal_gc_array`` / ``thermal_heater`` / ``thermal_mzi_{i}`` /
    ``thermal_dc_pad_{1..9}``.
    """
    cell = fw.Component()
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx

    x_left = 0.0
    y_top = 0.0

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
    # centred on the **grating-coupler array** (the alignment loop to its west is
    # excluded), so the in/out routing fans symmetrically off both ends.
    mzi0 = _balanced_mzi_plain(_MZI_ARM)
    mb = mzi0.bbox
    mzi_x_left = array_xmin + (ab.dx - mb.dx) / 2.0
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

    # The 9-pad probe row on the shared DC test-pad row (as on R4B TOPS). The
    # two **wired** pads (1-2) stay centred on the heater above them (which is
    # itself centred on the GC array / MZI stack), so the two bias routes drop
    # symmetrically; the unwired provision pads (3-9) continue the 250 um pitch
    # eastward.
    pad = bondpad_for_test_top()
    pad_w_rot = pad.bbox.dy
    pad_pitch = pad_w_rot + _p.dc_test_pad_spacing.value
    x_pad0 = heater_cx - pad_pitch / 2.0  # centre of pad 1 (westmost, always used)
    for i in range(_NUM_DC_PADS):
        cell.add_placed(
            pad,
            name=f"thermal_dc_pad_{i + 1}",
            x=x_pad0 + i * pad_pitch,
            y=-_p.dc_test_pad_drop.value,
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
        step=10.0,
        # Force a fan-in on the MZI side and pin its landing right, so the
        # rightmost lane rides straight through the corridor (no staircase bends).
        fan_out="right",
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
        # Fan-out pinned left: the leftmost lane lands straight on its coupler.
        fan_out="left",
    )

    # Heater bias: each heater terminal up to its own bond pad. Two separate
    # autoroute calls, not one bundle -- the heater's terminals face opposite ways
    # (e1 west, e2 east) and a bundle needs every lane to share an outward
    # heading. e1 takes the lower-x pad, e2 the higher-x one, so the two lines
    # don't cross. Landing on the pads' north faces (the pads are rotated 90 deg,
    # so that face is the port named "e").
    for term, pad_idx in (("e1", 1), ("e2", 2)):
        cell.autoroute(
            ports_a=[("thermal_heater", term)],
            ports_b=[(f"thermal_dc_pad_{pad_idx}", "e")],
            spec="routing_top_metal",
            name=f"thermal_heater_bias_{term}",
            avoid_port_owners=False,
        )

    cell.cell_type = "test_structure"
    cell.description = (
        "Thermal-crosstalk test block: a Cr ladder heater with 5 balanced-MZI "
        "thermometers stacked below it, GC fibre I/O and a 9-pad DC probe "
        "row, fully wired."
    )
    return cell
