"""Die holder R3·A — third row, left.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): RF (probe) —
termination · TRL · standalone TW electrode (length sweep). Frame only for now.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk
from luqia_ln200.cells.couplers import gratingcoupler_alignment_rib_sm_800nm_ext

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ._frame import die_scaffold
from ._head_coupler_block import add_head_and_couplers
from .test_cells_die_r1a import (
    imbricated_ull_offset,
    test_waveguide_cutback_sm,
    test_waveguide_cutback_ull,
)

# Gap (um) between the input directional coupler and the modulator heads to its
# right, and the extra head-to-head spacing on this die.
_INPUT_DC_GAP = 230.0
_EXTRA_HEAD_SPACING = 100.0
# Gap (um) from the die right inner edge to the (rightmost) ULL cutback cell.
_CUTBACK_RIGHT_MARGIN = 250.0
# SM cutback interleave vs the ULL cutback: horizontal shift toward the ULL, and
# the vertical spiral offset -- realised as *extra SM coupler-to-spiral spacing*
# (not a placement drop) so the two grating arrays stay on one line while the SM
# spirals sit lower to interleave.
_SM_CUTBACK_INTERLEAVE_X = 1000.0
_SM_CUTBACK_INTERLEAVE_Y = 110.0


def die_r3a() -> fw.Component:
    """Build and return the R3·A die."""
    params = DieParameters()
    cell = die_scaffold("die_R3A", params, num_bondpads=8)
    # Two GSG phase-modulator electrodes (SM on column A) stacked vertically:
    # bottom one gsg_modulator_vertical_shift above the die bottom edge, top one
    # gsg_modulator_spacing (centre-to-centre) above it. Placed directly so their
    # ports (o1-o4 optical, e1/e2 electrode) are reachable for per-die routing.
    half_h = _p.die_height.value / 2.0
    modulator = pdk.cells[params.gsg_modulator_cell.value](
        length=_p.gsg_modulator_electrode_length.value,
    )
    mb = modulator.bbox
    x0 = -mb.center_x  # centre the electrode in x
    bot_y = -half_h + _p.gsg_modulator_vertical_shift.value - mb.ymin
    top_y = bot_y + _p.gsg_modulator_spacing.value
    mod_bot = cell.add_placed(modulator, "gsg_modulator_bot", x=x0, y=bot_y)
    mod_top = cell.add_placed(modulator, "gsg_modulator_top", x=x0, y=top_y)
    # RF launch on both electrode ends: a via lifts each modulator's bottom-metal
    # electrode up to top metal, then a width taper matches the electrode bundle to
    # the GSG pad launch, ending on a GSG bondpad triplet. Input (east, e2) and
    # output (west, e1) chains are mirror images. NOTE: placeholder floorplan --
    # some variations will drop the output pads for a terminator once decided, so
    # the two sides are kept as explicit per-end puts rather than a shared helper.
    # -- input (east, e2): via extends +x, continuation on top_e2, taper/pads on e1
    via_bot_in = cell.put(
        pdk.cells["gsg_via_electrode_top_bot_holes_50ohms"](),
        mod_bot.ports.e2,
        port_to="bot_e1",
        name="rf_via_bot_in",
    )
    via_top_in = cell.put(
        pdk.cells["gsg_via_electrode_top_bot_holes_50ohms"](),
        mod_top.ports.e2,
        port_to="bot_e1",
        name="rf_via_top_in",
    )
    taper_bot_in = cell.put(
        pdk.cells["gsg_taper_electrode_to_pads_top_metal_50ohms"](),
        via_bot_in.ports.top_e2,
        port_to="e1",
        name="rf_taper_bot_in",
    )
    taper_top_in = cell.put(
        pdk.cells["gsg_taper_electrode_to_pads_top_metal_50ohms"](),
        via_top_in.ports.top_e2,
        port_to="e1",
        name="rf_taper_top_in",
    )
    cell.put(
        pdk.cells["gsg_bondpads_top_metal_50ohms"](),
        taper_bot_in.ports.e2,
        port_to="e1",
        name="rf_pads_bot_in",
    )
    cell.put(
        pdk.cells["gsg_bondpads_top_metal_50ohms"](),
        taper_top_in.ports.e2,
        port_to="e1",
        name="rf_pads_top_in",
    )
    # -- output (west, e1): via extends -x, continuation on top_e1. Taper e1
    # (electrode side) mates the via and e2 (pad side) mates the pads -- same
    # electrode->pad sense as the input side, just mirrored in x.
    via_bot_out = cell.put(
        pdk.cells["gsg_via_electrode_top_bot_holes_50ohms"](),
        mod_bot.ports.e1,
        port_to="bot_e2",
        name="rf_via_bot_out",
    )
    via_top_out = cell.put(
        pdk.cells["gsg_via_electrode_top_bot_holes_50ohms"](),
        mod_top.ports.e1,
        port_to="bot_e2",
        name="rf_via_top_out",
    )
    taper_bot_out = cell.put(
        pdk.cells["gsg_taper_electrode_to_pads_top_metal_50ohms"](),
        via_bot_out.ports.top_e1,
        port_to="e1",
        name="rf_taper_bot_out",
    )
    taper_top_out = cell.put(
        pdk.cells["gsg_taper_electrode_to_pads_top_metal_50ohms"](),
        via_top_out.ports.top_e1,
        port_to="e1",
        name="rf_taper_top_out",
    )
    cell.put(
        pdk.cells["gsg_bondpads_top_metal_50ohms"](),
        taper_bot_out.ports.e2,
        port_to="e2",
        name="rf_pads_bot_out",
    )
    cell.put(
        pdk.cells["gsg_bondpads_top_metal_50ohms"](),
        taper_top_out.ports.e2,
        port_to="e2",
        name="rf_pads_top_out",
    )
    # --- R3·A per-die content ---
    # modulator_head + directional couplers test block (shared with R4A/R4B),
    # but with two modulator_heads at the input.
    add_head_and_couplers(cell, second_input_head=True, extra_input_spacing=_EXTRA_HEAD_SPACING)
    # A directional coupler left of the two modulator heads, centred vertically
    # between them (facing their inputs).
    h1 = cell.instances["test_modulator_head"]
    h2 = cell.instances["test_modulator_head_2"]
    in_x = h1.ports.o1.position[0]
    mid1 = (h1.ports.o1.position[1] + h1.ports.o2.position[1]) / 2.0
    mid2 = (h2.ports.o1.position[1] + h2.ports.o2.position[1]) / 2.0
    dc = pdk.cells["directionalcoupler_rib_sm_800nm_ord_50_50"]()
    sb = dc.bbox
    cell.add_placed(
        dc,
        "test_input_dc",
        x=(in_x - _INPUT_DC_GAP) - sb.xmax,
        y=((mid1 + mid2) / 2.0) - sb.center_y,
    )
    # SM + ULL waveguide-loss (cutback) test cells (moved here from R1A): each a
    # horizontal coupler array on top of a vertical stack of four horizontal delay
    # spirals (long/thin at 10-12 loops, so each stack is only ~1.4-1.5 mm tall).
    # The ULL cell (reversed length order -> longest at top) is placed x-flipped
    # (mirror + 180 deg: spirals extend left, alignment loop on the right) and the
    # SM cell (upright) nests to its left so the two triangular spiral profiles
    # imbricate -- shortest-SM facing longest-ULL. The pair sits in the clear top
    # band and is pushed to the **right** of the die (ULL, the rightmost, held
    # _CUTBACK_RIGHT_MARGIN off the right inner edge). The SM is then nudged
    # +1000 um toward the ULL and -110 um down to interleave further (a small
    # residual SM<->ULL overlap is accepted for now).
    left_inner = -_p.die_width.value / 2.0 + _p.keepout_width.value
    right_inner = _p.die_width.value / 2.0 - _p.keepout_width.value
    top_inner = half_h - _p.keepout_width.value
    # Corner alignment-loop height, from the Component bbox (ty-clean; Instance
    # bbox is BBox | None). The scaffold lands the loop's top at top_inner.
    corner_loop_dy = gratingcoupler_alignment_rib_sm_800nm_ext().bbox.dy
    # The SM cell carries extra coupler-to-spiral spacing so its (raised) grating
    # array lands on the same line as the ULL's while its spirals interleave below.
    sm_cut = test_waveguide_cutback_sm(extra_coupler_gap=_SM_CUTBACK_INTERLEAVE_Y)
    ull_cut = test_waveguide_cutback_ull()
    dx, _dy = imbricated_ull_offset(sm_cut, ull_cut)
    # Shared grating-array line (both cells' coupler tops land here).
    y_couplers = top_inner - corner_loop_dy - 30.0 + 100.0
    # Base SM x-anchor (upright, top-left of the band); ULL nests at +dx.
    x_sm = (left_inner + 70.0 + 250.0) - sm_cut.bbox.xmin
    # (1) Shift the whole pair right so the x-flipped ULL's right edge (its
    # rightmost point is -ull.bbox.xmin from its anchor) sits _CUTBACK_RIGHT_MARGIN
    # off the right inner edge.
    ull_right = (x_sm + dx) - ull_cut.bbox.xmin
    block_dx = (right_inner - _CUTBACK_RIGHT_MARGIN) - ull_right
    # SM shifted +_SM_CUTBACK_INTERLEAVE_X toward the ULL; both coupler arrays
    # anchored (bbox top) to the shared y_couplers line.
    cell.add_placed(
        sm_cut,
        "test_waveguide_cutback_sm",
        x=x_sm + block_dx + _SM_CUTBACK_INTERLEAVE_X,
        y=y_couplers - sm_cut.bbox.ymax,
    )
    cell.add_placed(
        ull_cut,
        "test_waveguide_cutback_ull",
        x=x_sm + dx + block_dx,
        y=y_couplers - ull_cut.bbox.ymax,
        mirror=True,
        rotation=180.0,
    )
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    return cell
