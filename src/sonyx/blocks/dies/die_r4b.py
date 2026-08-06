"""Die holder R4·B — bottom-right of the reticle.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): edge-coupled SM+ULL
spirals · OFDR reflectometry (E4). Frame only for now.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk

from ...parameters import DieParametersMultimode
from ...parameters import parameters as _p
from ..dc_routing import add_dc_pad_routes
from ..heater_mzi_sweep import heater_mzi_sweep_block
from ..labels import add_rf_pad_labels, add_thermistance_pad_label
from ..mzi_ladder import mzi_ladder_block
from ..paperclip_mzi_sweep import paperclip_mzi_sweep_block
from ._frame import die_scaffold
from ._head_coupler_block import (
    add_dc_output_to_ec_routes,
    add_head_and_couplers,
    add_head_input_routes,
    add_input_beam_dumps,
    add_mzm_input_routes,
    add_mzm_output_routes,
)

# Die-level anchor of the test-block band: the first (heater) block's local
# origin -- its alignment loop's west edge / GC tops line -- goes this far east
# of the left inner edge and below the top inner edge. The other test blocks
# chain off it by bbox abutment, so these two knobs slide the whole band.
_TEST_BLOCK_LEFT_MARGIN = 1250.0
_TEST_BLOCK_TOP_MARGIN = 40.0


def die_r4b() -> fw.Component:
    """Build and return the R4·B die."""
    params = DieParametersMultimode()
    cell = die_scaffold("die_R4B", params)
    # Two GSG phase-modulator electrodes (multimode on column B) stacked
    # vertically: bottom one gsg_modulator_vertical_shift above the die bottom
    # edge, top one gsg_modulator_spacing (centre-to-centre) above it. Placed
    # directly so their ports (o1-o4 optical, e1/e2 electrode) are reachable.
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
    # --- R4·B per-die content ---
    # modulator_head + directional couplers test block (shared with R4A).
    add_head_and_couplers(cell, second_input_adiabatic=True)
    # Feed the input block's head + directional coupler from the two next-rightmost
    # circuit edge couplers (default, non-tight SM routing).
    add_head_input_routes(
        cell, int(params.num_edge_couplers_circuit.value),
        second_device="test_modulator_head_2",
    )
    # Terminate the input stage's spare (unfed) west inputs -- one per input
    # device -- with a PDK beam dump, mirrored away from the fed neighbour.
    add_input_beam_dumps(cell)
    # Route the input-block outputs to the two MZMs (head -> top, coupler -> bottom).
    add_mzm_input_routes(cell, second_device="test_modulator_head_2")
    # Route each MZM's outputs (o1/o2) into its output directional coupler (two calls).
    dc_ec_obs = add_mzm_output_routes(cell)
    # Output DCs -> open circuit edge couplers (bottom drop + top drop via a
    # west-facing U-turn stub). Shared helper.
    add_dc_output_to_ec_routes(cell, int(params.num_edge_couplers_circuit.value), dc_ec_obs)
    # --- test-block band (clear top strip of the die) ---
    # Three self-contained, fully wired test blocks, packed west->east by bbox
    # abutment: each block's top-left corner lands on its west neighbour's
    # top-right corner. Only the heater block is placed at die coordinates;
    # the rest chain off it, so the band re-packs itself when a block's
    # footprint changes.
    half_w = _p.die_width.value / 2.0
    kw = _p.keepout_width.value
    # Thermo-optic phase-shifter test: 6 balanced 1x2-MMI MZIs with a swept
    # heater active length (GC arrays + alignment loops on top, MZIs stacked
    # below, 8-pad DC probe row).
    heater_block = cell.add_placed(
        heater_mzi_sweep_block(),
        name="heater_mzi_sweep",
        x=(-half_w + kw) + _TEST_BLOCK_LEFT_MARGIN,
        y=(half_h - kw) - _TEST_BLOCK_TOP_MARGIN,
    )
    # Paperclip-TOPS test: 3 MZIs (num_arms 3/5/7) with a folded thermo-optic
    # phase shifter on one arm, L-bend risers, 4-pad DC probe row. The two
    # blocks' pad rows meet on one gapless 250 um probe grid: each cell pins
    # its row to its own bbox edge (heater: last pad 150 um inside its east
    # edge; paperclip: first pad 100 um inside its west edge), so plain
    # corner-on-corner abutment continues the grid.
    paperclip_block = cell.add_aligned(
        paperclip_mzi_sweep_block(),
        heater_block,
        anchor="top_left",
        to="top_right",
        name="paperclip_mzi_sweep",
    )
    # Unbalanced-MZI n_eff / n_g calibration ladder (ord + ext, 6 MZIs) with
    # two constant-pitch N-S grating-coupler arrays (one per orientation group).
    cell.add_aligned(
        mzi_ladder_block(),
        paperclip_block,
        anchor="top_left",
        to="top_right",
        name="mzi_ladder",
    )
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    # DC bias routing on TOP_METAL: modulator-head terminals -> bond pads
    # (pads 0-3 bias, remaining pads strapped as the common ground land).
    add_dc_pad_routes(cell, second_head="test_modulator_head_2")
    # Visible names on the RF GSG launch pads (north of each triplet) and on the
    # thermistance bonding pad (west of it) -- last, so both read the pads' final
    # placed positions.
    add_rf_pad_labels(cell)
    add_thermistance_pad_label(cell)
    return cell
