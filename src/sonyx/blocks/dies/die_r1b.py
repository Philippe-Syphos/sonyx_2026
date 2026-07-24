"""Die holder R1·B — top-right of the reticle.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): unbalanced MZI x3
· DC splitter (direct / MZI / tree). Frame only for now.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ._frame import die_scaffold
from ._head_coupler_block import add_head_and_couplers


def die_r1b() -> fw.Component:
    """Build and return the R1·B die."""
    params = DieParameters()
    cell = die_scaffold("die_R1B", params)
    # Two GSG phase-modulator electrodes (SM, same electrode as R2A) stacked
    # vertically: bottom one gsg_modulator_vertical_shift above the die bottom
    # edge, top one gsg_modulator_spacing (centre-to-centre) above it. Placed
    # directly so their ports (o1-o4 optical, e1/e2 electrode) are reachable.
    half_h = _p.die_height.value / 2.0
    modulator = pdk.cells[params.gsg_modulator_cell.value](
        length=_p.gsg_modulator_electrode_length.value,
    )
    mb = modulator.bbox
    x0 = -mb.center_x  # centre the electrode in x
    # Row 1 uses a 1250 um shift (rows 2-4 use the 2 mm
    # gsg_modulator_vertical_shift default).
    _mod_shift = 1250.0
    bot_y = -half_h + _mod_shift - mb.ymin
    top_y = bot_y + _p.gsg_modulator_spacing.value
    mod_bot = cell.add_placed(modulator, "gsg_modulator_bot", x=x0, y=bot_y)
    mod_top = cell.add_placed(modulator, "gsg_modulator_top", x=x0, y=top_y)
    # One more electrode descending from the top edge -- R1A's former top mirror
    # pair is split one modulator per die, and this is R1B's half. Same top-edge
    # inset as the bottom pair takes from the bottom edge.
    top2_y = half_h - _mod_shift - mb.ymax
    mod_top_2 = cell.add_placed(modulator, "gsg_modulator_top_2", x=x0, y=top2_y)
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
    via_top2_in = cell.put(
        pdk.cells["gsg_via_electrode_top_bot_holes_50ohms"](),
        mod_top_2.ports.e2,
        port_to="bot_e1",
        name="rf_via_top2_in",
    )
    taper_top2_in = cell.put(
        pdk.cells["gsg_taper_electrode_to_pads_top_metal_50ohms"](),
        via_top2_in.ports.top_e2,
        port_to="e1",
        name="rf_taper_top2_in",
    )
    cell.put(
        pdk.cells["gsg_bondpads_top_metal_50ohms"](),
        taper_top2_in.ports.e2,
        port_to="e1",
        name="rf_pads_top2_in",
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
    via_top2_out = cell.put(
        pdk.cells["gsg_via_electrode_top_bot_holes_50ohms"](),
        mod_top_2.ports.e1,
        port_to="bot_e2",
        name="rf_via_top2_out",
    )
    taper_top2_out = cell.put(
        pdk.cells["gsg_taper_electrode_to_pads_top_metal_50ohms"](),
        via_top2_out.ports.top_e1,
        port_to="e1",
        name="rf_taper_top2_out",
    )
    cell.put(
        pdk.cells["gsg_bondpads_top_metal_50ohms"](),
        taper_top2_out.ports.e2,
        port_to="e2",
        name="rf_pads_top2_out",
    )
    # --- R1·B per-die content (see module docstring for planned DUTs) ---
    # Input modulator_head + directional coupler (east) and one output DC above
    # each of the lower two modulators (west) -- the shared head+coupler block,
    # same as R4A (default anchor on rf_pads_bot_in).
    add_head_and_couplers(cell)
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    return cell
