"""Die holder R1·B — top-right of the reticle.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): unbalanced MZI x3
· DC splitter (direct / MZI / tree). Frame only for now.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ..dc_routing import add_dc_pad_routes
from ..gc_test_array import open_gc_array_block
from ..labels import add_rf_pad_labels, add_thermistance_pad_label
from ._frame import die_scaffold, place_thermistance_pad_west_of
from ._head_coupler_block import (
    add_dc_output_to_ec_routes,
    add_head_and_couplers,
    add_head_input_routes,
    add_input_beam_dumps,
    add_mzm_input_routes,
    add_mzm_output_routes,
    add_top2_dc_pad_routes,
    add_top2_dc_pads,
    add_top2_gc_routes,
    add_top2_routes,
    add_top_head_and_coupler,
)

# Top-edge inset (um) of row 1's third electrode, the one descending from the
# top edge. Row-1 specific -- the other dies carry only the bottom pair. Moved
# 150 um north (1250 -> 1100) to open up the band below it.
_TOP2_EDGE_INSET = 1100.0

# Die-level anchor of the open GC-array block (its local origin is the loop's
# west edge / GC tops line), top-right corner: margins off the right / top
# inner edges (clear of the top-right corner alignment loop).
_OPEN_GC_RIGHT_MARGIN = 250.0
_OPEN_GC_TOP_MARGIN = 40.0


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
    # The bottom pair sits on the shared gsg_modulator_vertical_shift (2 mm), the
    # same as rows 2-4, so row 1's two lower modulators line up with every other
    # die. (They previously used a local 1250 um shift.)
    bot_y = -half_h + _p.gsg_modulator_vertical_shift.value - mb.ymin
    top_y = bot_y + _p.gsg_modulator_spacing.value
    mod_bot = cell.add_placed(modulator, name="gsg_modulator_bot", x=x0, y=bot_y)
    mod_top = cell.add_placed(modulator, name="gsg_modulator_top", x=x0, y=top_y)
    # One more electrode descending from the top edge -- R1A's former top mirror
    # pair is split one modulator per die, and this is R1B's half. Row 1's own
    # 1250 um top-edge inset.
    top2_y = half_h - _TOP2_EDGE_INSET - mb.ymax
    mod_top_2 = cell.add_placed(modulator, name="gsg_modulator_top_2", x=x0, y=top2_y)
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
    # Feed the input block's head + directional coupler from the two next-rightmost
    # circuit edge couplers (default, non-tight SM routing).
    add_head_input_routes(cell, int(params.num_edge_couplers_circuit.value))
    # Terminate the input stage's spare (unfed) west inputs -- one per input
    # device -- with a PDK beam dump, mirrored away from the fed neighbour.
    add_input_beam_dumps(cell)
    # Route the input-block outputs to the two MZMs (head -> top, coupler -> bottom).
    # The third modulator (gsg_modulator_top_2) has its own head and is not fed here.
    add_mzm_input_routes(cell)
    # Route each MZM's outputs (o1/o2) into its output directional coupler (two calls).
    dc_ec_obs = add_mzm_output_routes(cell)
    # Output DCs -> open circuit edge couplers (bottom drop + top drop via a
    # west-facing U-turn stub). Shared helper.
    add_dc_output_to_ec_routes(cell, int(params.num_edge_couplers_circuit.value), dc_ec_obs)
    # Open grating-coupler array block (4 couplers + left alignment loop),
    # top-right (right edge / GC tops at the standard margins) -- fibre I/O for
    # the extra top modulator (gsg_modulator_top_2), coupler ports exposed.
    half_w = _p.die_width.value / 2.0
    kw = _p.keepout_width.value
    gc_top2 = open_gc_array_block(4)
    cell.add_placed(
        gc_top2,
        name="mod_top2_gc",
        x=((half_w - kw) - _OPEN_GC_RIGHT_MARGIN) - gc_top2.bbox.xmax,
        y=(half_h - kw) - _OPEN_GC_TOP_MARGIN,
    )
    # R1A/R1B only: park the thermistance bonding pad just west of that array
    # instead of on the reticle-wide _THERMISTANCE_CENTER the other six dies use.
    # Must follow the array -- the pad is re-placed relative to it.
    place_thermistance_pad_west_of(cell, ("mod_top2_gc",))
    # modulator_head (left) + output directional coupler (right) for the extra top
    # modulator, rotated 180 deg vs the standard block, in the band above it.
    add_top_head_and_coupler(cell, "gsg_modulator_top_2")
    # Four DC bias pads for that head's heaters, north-west corner (placement only).
    add_top2_dc_pads(cell)
    # head -> MZM and MZM -> output DC for that modulator (the rotated twin of the
    # add_mzm_input_routes / add_mzm_output_routes pair above).
    top2_obs = add_top2_routes(cell, "gsg_modulator_top_2")
    # The 4 open grating couplers -> that head's inputs / that DC's open outputs.
    add_top2_gc_routes(cell, top2_obs)
    # That head's heater terminals -> the four north-west DC pads.
    add_top2_dc_pad_routes(cell)
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    # DC bias routing on TOP_METAL: modulator-head terminals -> bond pads
    # (pads 0-3 bias, remaining pads strapped as the common ground land).
    add_dc_pad_routes(cell)
    # Visible names on the RF GSG launch pads (north of each triplet) and on the
    # thermistance bonding pad (west of it). Last, so both read the pads' final
    # placed positions -- the thermistance pad is moved twice on this die.
    add_rf_pad_labels(cell)
    add_thermistance_pad_label(cell)
    return cell
