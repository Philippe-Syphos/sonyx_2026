"""Die holder R2·A — second row, left.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): GC DOE — 51
variants (fills the test region). Frame only for now.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ._frame import die_scaffold
from ._head_coupler_block import add_head_and_couplers


def die_r2a() -> fw.Component:
    """Build and return the R2·A die."""
    params = DieParameters()
    cell = die_scaffold("die_R2A", params)
    # Two GSG phase-modulator electrodes (SM on column A) stacked vertically:
    # bottom one gsg_modulator_vertical_shift above the die bottom edge, top one
    # gsg_modulator_spacing (centre-to-centre) above it. Placed directly so their
    # ports (o1-o4 optical, e1/e2 electrode) are reachable for per-die routing.
    half_h = _p.die_height.value / 2.0
    # R2A terminates the output instead of taper + GSG pads; lengthen the
    # electrode by exactly the output length that removal frees, so the device
    # spans the same as the standard (taper + pad) dies.
    freed = (
        pdk.cells["gsg_taper_electrode_to_pads_top_metal_50ohms"]().bbox.dx
        + pdk.cells["gsg_bondpads_top_metal_50ohms"]().bbox.dx
        - pdk.cells["gsg_terminator_top_metal_50ohms_parallel"]().bbox.dx
    )
    modulator = pdk.cells[params.gsg_modulator_cell.value](
        length=_p.gsg_modulator_electrode_length.value + freed,
    )
    mb = modulator.bbox
    # Centre the electrode in x, then shift both electrodes 220 um to the left.
    x0 = -mb.center_x - 220.0
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
    # -- output (west, e1): via lifts to top metal, then a 50 ohm RF terminator
    # absorbs the wave (this die replaces the output taper + pads with a load).
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
    cell.put(
        pdk.cells["gsg_terminator_top_metal_50ohms_parallel"](),
        via_bot_out.ports.top_e1,
        port_to="e1",
        name="rf_term_bot_out",
    )
    cell.put(
        pdk.cells["gsg_terminator_top_metal_50ohms_parallel"](),
        via_top_out.ports.top_e1,
        port_to="e1",
        name="rf_term_top_out",
    )
    # --- R2·A per-die content ---
    # modulator_head + directional couplers test block (shared with R3A/R4A/R4B).
    add_head_and_couplers(cell)
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    return cell
