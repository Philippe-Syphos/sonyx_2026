"""Die holder R3·A — third row, left.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): RF (probe) —
termination · TRL · standalone TW electrode (length sweep). Frame only for now.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk
from picasso.component import PortSpec

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ..dc_routing import add_dc_pad_routes
from ..thermal_crosstalk import add_thermal_crosstalk
from ._frame import die_scaffold
from ._head_coupler_block import (
    add_dc_output_to_ec_routes,
    add_head_and_couplers,
    add_mzm_input_routes,
    add_mzm_output_routes,
)
from .test_cells_die_r1a import place_cutback_top_right, test_waveguide_cutback_ull

# Gap (um) between the input directional coupler and the modulator heads to its
# right, and the extra head-to-head spacing on this die.
_INPUT_DC_GAP = 230.0
_EXTRA_HEAD_SPACING = 100.0


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
        name="test_input_dc",
        x=(in_x - _INPUT_DC_GAP) - sb.xmax,
        y=((mid1 + mid2) / 2.0) - sb.center_y,
    )
    # Edge-coupled input into the two heads via the input DC, in two single bundles
    # (lanes stay parallel / non-crossing), default (non-tight) SM routing:
    #   (1) the two next-rightmost circuit edge couplers -> the DC's west inputs
    #       (c_{num-4} west -> o2 upper, c_{num-3} east -> o1 lower);
    #   (2) the DC's east outputs -> one west input of each head (o3 upper -> upper
    #       head, o4 lower -> lower head, each to that head's nearer input port).
    num_ec = int(params.num_edge_couplers_circuit.value)
    ec_in: list[PortSpec] = [
        ("edge_couplers_circuit", f"o2_r0_c{num_ec - 4}"),
        ("edge_couplers_circuit", f"o2_r0_c{num_ec - 3}"),
    ]
    dc_in: list[PortSpec] = [("test_input_dc", "o2"), ("test_input_dc", "o1")]
    cell.autoroute(ports_a=ec_in, ports_b=dc_in, spec="routing_sm_default", strategy="vgraph_rect")
    # DC outputs -> heads: two scalar routes, not a bundle. The upper output goes to
    # the upper head and the lower output to the lower head, so the two paths diverge
    # (they cannot cross) -- and their DC-side pitch (~21 um) vs head-side pitch
    # (~248 um) is too divergent over the ~230 um gap for a bundle fan corridor.
    cell.autoroute(
        ("test_input_dc", "o3"),
        ("test_modulator_head", "o1"),
        spec="routing_sm_default",
        strategy="vgraph_rect",
    )
    cell.autoroute(
        ("test_input_dc", "o4"),
        ("test_modulator_head_2", "o2"),
        spec="routing_sm_default",
        strategy="vgraph_rect",
    )
    # Route the two heads' outputs to the two MZMs (upper head -> top modulator,
    # lower head -> bottom modulator), a single 4-lane bundle to the east ports.
    add_mzm_input_routes(cell, second_device="test_modulator_head_2")
    # Route each MZM's outputs (o1/o2) into its output directional coupler (two calls).
    dc_ec_obs = add_mzm_output_routes(cell)
    # Output DCs -> open circuit edge couplers (bottom drop + top drop via a
    # west-facing U-turn stub). Shared helper.
    add_dc_output_to_ec_routes(cell, int(params.num_edge_couplers_circuit.value), dc_ec_obs)
    # ULL waveguide-loss (cutback) test cell: a horizontal coupler array on top of
    # a vertical stack of four horizontal delay spirals. Placed in the standard
    # cutback slot (x-flipped, top-right band). The SM twin now lives on R2B in the
    # same slot -- see place_cutback_top_right.
    place_cutback_top_right(cell, test_waveguide_cutback_ull(), "test_waveguide_cutback_ull")
    # (The balanced-bridge crosstalk MZIs moved to R3B -- see die_r3b.)
    # Thermal-crosstalk cell (heater + stacked balanced-MZI thermometers).
    # First draft, placement only.
    add_thermal_crosstalk(cell)
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    # DC bias routing on TOP_METAL: modulator-head terminals -> bond pads
    # (pads 0-3 bias, remaining pads strapped as the common ground land).
    add_dc_pad_routes(cell, second_head="test_modulator_head_2")
    return cell
