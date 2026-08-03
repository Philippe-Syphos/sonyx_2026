"""Die holder R4·A — bottom row, left.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): parallel-propagation
isolation (E2) · spare optical replicas. Frame only for now.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ..dc_length_sweep import add_dc_length_sweep
from ..dc_mzi_length_sweep import add_dc_mzi_length_sweep
from ..dc_routing import add_dc_pad_routes
from ..labels import add_rf_pad_labels, add_thermistance_pad_label
from ._frame import die_scaffold
from ._head_coupler_block import (
    add_dc_output_to_ec_routes,
    add_head_and_couplers,
    add_head_input_routes,
    add_input_beam_dumps,
    add_mzm_input_routes,
    add_mzm_output_routes,
)


def die_r4a() -> fw.Component:
    """Build and return the R4·A die."""
    params = DieParameters()
    cell = die_scaffold("die_R4A", params)
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
    mod_bot = cell.add_placed(modulator, name="gsg_modulator_bot", x=x0, y=bot_y)
    mod_top = cell.add_placed(modulator, name="gsg_modulator_top", x=x0, y=top_y)
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
    # --- R4·A per-die content ---
    # modulator_head + directional couplers test block (shared with R4B).
    add_head_and_couplers(cell)
    # Feed the input block's head + directional coupler from the two next-rightmost
    # circuit edge couplers (default, non-tight SM routing).
    add_head_input_routes(cell, int(params.num_edge_couplers_circuit.value))
    # Terminate the input stage's spare (unfed) west inputs -- one per input
    # device -- with a PDK beam dump, mirrored away from the fed neighbour.
    add_input_beam_dumps(cell)
    # Route the input-block outputs to the two MZMs (head -> top, coupler -> bottom),
    # a single 4-lane bundle to the modulators' east ports.
    add_mzm_input_routes(cell)
    # Route each MZM's outputs into its output directional coupler. This also builds
    # the DC-output chain's shared obstacle set (modulator electrode bboxes + the two
    # MZM->DC routes) which the DC->EC routes below reuse.
    dc_ec_obs = add_mzm_output_routes(cell)
    # Output DCs -> the open circuit edge couplers (bottom DC -> two rightmost open,
    # top DC -> next two, via a west-facing U-turn stub). Shared helper.
    add_dc_output_to_ec_routes(cell, int(params.num_edge_couplers_circuit.value), dc_ec_obs)
    # # Directional-coupler coupling-length test: 8 DCs (L sweep) + GC array,
    # top-left. Placed, plus the top-left group's four inputs bundled to its four
    # west couplers (tight SM spec); o3/o4 and the other groups routed later, o2 open.
    add_dc_length_sweep(cell)
    # Back-to-back-coupler MZI (zero-arm) coupling-length test: same sweep/layout,
    # placed to the right of the single-DC sweep. Placement-only.
    add_dc_mzi_length_sweep(cell)
    # DC bias routing on TOP_METAL (first test of the routing_top_metal spec):
    # the modulator head's tunable-coupler west terminal -> DC bond pad 0.
    add_dc_pad_routes(cell)
    # Visible names on the RF GSG launch pads (north of each triplet) and on the
    # thermistance bonding pad (west of it) -- last, so both read the pads' final
    # placed positions.
    add_rf_pad_labels(cell)
    add_thermistance_pad_label(cell)
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    return cell
