"""Die holder R3·B — third row, right.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): DC reflectometer
(E3) · N-tree radiating-gap isolation (E1). Frame only for now.

R3B is the **bespoke-electrode** test die: its two SM GSG modulators use a
widened signal-to-ground gap (the "safe" variant — metal pulled back from the
optical line), pinned to the PDK ``gsg_gap`` plus a per-modulator delta. Both
the modulator and its BOT↔TOP via are the stock PDK cells with their surfaced
gap knobs (``straight_gsg_modulator_800nm(gap=...)`` and the split-gap
``gsg_via_electrode_top_bot_holes_50ohms(bot_gap=...)``); the taper → pad
launch stays the stock PDK chain.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk
from luqia_ln200.tech.parameters import parameters as _pdk

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ..crossing_mzi import add_crossing_mzi_gc_routes, add_crossing_mzis
from ..dc_routing import add_dc_pad_routes
from ._frame import die_scaffold
from ._head_coupler_block import (
    add_dc_output_to_ec_routes,
    add_head_and_couplers,
    add_head_input_routes,
    add_mzm_input_routes,
    add_mzm_output_routes,
)
from .test_cells_die_r1a import test_waveguide_cutback_ssm

# SSM cutback: gaps (um) from the die inner edges to the (right-pushed) cell.
_SSM_CUTBACK_RIGHT_MARGIN = 250.0
_SSM_CUTBACK_TOP_MARGIN = 40.0

# Extra head-to-head spacing (um) on this die (mirrors R3A).
_EXTRA_HEAD_SPACING = 100.0
# Signal-to-ground gap increase (um) over the PDK gsg_gap, per modulator: the
# top electrode opens 0.5 um, the bottom 1.0 um. Pinned to the live PDK value so
# they track it (the "safe" wider-gap variant -- metal further from the mode).
_GAP_DELTA_TOP = 0.5
_GAP_DELTA_BOT = 1.0


def _bespoke_gap_modulator(length: float, gap: float) -> fw.Component:
    """The PDK SM GSG modulator at a bespoke signal-to-ground ``gap``.

    ``straight_gsg_modulator_800nm`` with its surfaced gap knob: electrode
    grounds pulled back to ``gap`` and the ribs re-centred in the widened
    gaps. Ports: ``o1``/``o2`` (west), ``o3``/``o4`` (east), ``e1``/``e2``
    (electrode, on the bespoke-gap cross-section).
    """
    return pdk.cells["straight_gsg_modulator_800nm"](length=length, gap=gap)


def _bespoke_via(gap: float) -> fw.Component:
    """Split-gap GSG electrode via: BOT_METAL at the widened ``gap``, TOP at PDK gap.

    The PDK ``gsg_via_electrode_top_bot_holes_50ohms`` with its surfaced
    ``bot_gap``: BOT_METAL grounds at the bespoke gap to match the modulator
    electrode, TOP_METAL grounds at the PDK ``gsg_gap`` to match the
    downstream stock taper, the Via1/Via2 hole array bridging the ground step
    **inside** the via contact. The stock
    ``gsg_taper_electrode_to_pads_top_metal_50ohms`` then abuts the real TOP
    (PDK) geometry on ``top_e1`` / ``top_e2``.
    """
    return pdk.cells["gsg_via_electrode_top_bot_holes_50ohms"](bot_gap=gap)


def die_r3b() -> fw.Component:
    """Build and return the R3·B die."""
    params = DieParameters()
    cell = die_scaffold("die_R3B", params)
    # Two bespoke SM GSG modulators stacked vertically, each with a widened
    # signal-to-ground gap (top +0.5 um, bottom +1.0 um over the PDK gsg_gap).
    # Bottom one gsg_modulator_vertical_shift above the die bottom edge, top one
    # gsg_modulator_spacing (centre-to-centre) above it. Placed directly so their
    # ports (o1-o4 optical, e1/e2 electrode) are reachable for per-die routing.
    half_h = _p.die_height.value / 2.0
    length = _p.gsg_modulator_electrode_length.value
    gap_top = _pdk.gsg_gap.value + _GAP_DELTA_TOP
    gap_bot = _pdk.gsg_gap.value + _GAP_DELTA_BOT
    mod_bot_cell = _bespoke_gap_modulator(length, gap_bot)
    mod_top_cell = _bespoke_gap_modulator(length, gap_top)
    mbb = mod_bot_cell.bbox
    x0 = -mbb.center_x  # centre the electrode in x
    bot_y = -half_h + _p.gsg_modulator_vertical_shift.value - mbb.ymin
    top_y = bot_y + _p.gsg_modulator_spacing.value
    mod_bot = cell.add_placed(mod_bot_cell, name="gsg_modulator_bot", x=x0, y=bot_y)
    mod_top = cell.add_placed(mod_top_cell, name="gsg_modulator_top", x=x0, y=top_y)
    # RF launch on both electrode ends: a bespoke via lifts each modulator's
    # (widened-gap) bottom-metal electrode up to top metal at the PDK gap, then
    # the stock width taper matches the electrode bundle to the GSG pad launch,
    # ending on a GSG bondpad triplet. Input (east, e2) and output (west, e1)
    # chains are mirror images. Per-modulator via (bottom gap 1.0, top gap 0.5).
    # -- input (east, e2): via extends +x, continuation on top_e2, taper/pads on e1
    via_bot_in = cell.put(
        _bespoke_via(gap_bot), mod_bot.ports.e2, port_to="bot_e1", name="rf_via_bot_in"
    )
    via_top_in = cell.put(
        _bespoke_via(gap_top), mod_top.ports.e2, port_to="bot_e1", name="rf_via_top_in"
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
        _bespoke_via(gap_bot), mod_bot.ports.e1, port_to="bot_e2", name="rf_via_bot_out"
    )
    via_top_out = cell.put(
        _bespoke_via(gap_top), mod_top.ports.e1, port_to="bot_e2", name="rf_via_top_out"
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
    # --- R3·B per-die content ---
    # modulator_head + directional couplers test block (shared with R3A/R4A/R4B),
    # with two modulator_heads at the input. Unlike R3A, no input directional
    # coupler next to the heads on this die.
    add_head_and_couplers(cell, second_input_head=True, extra_input_spacing=_EXTRA_HEAD_SPACING)
    # Feed the two input modulator heads (the second is a tunable coupler, in place
    # of the common dies' directional coupler) from the two next-rightmost circuit
    # edge couplers (single bundle, default non-tight SM routing).
    add_head_input_routes(cell, int(params.num_edge_couplers_circuit.value),
                          second_device="test_modulator_head_2")
    # Route the two heads' outputs to the two MZMs (upper head -> top modulator,
    # lower head -> bottom modulator), a single 4-lane bundle to the east ports.
    add_mzm_input_routes(cell, second_device="test_modulator_head_2")
    # Route each MZM's outputs (o1/o2) into its output directional coupler (two calls).
    dc_ec_obs = add_mzm_output_routes(cell)
    # Output DCs -> open circuit edge couplers (bottom drop + top drop via a
    # west-facing U-turn stub). Shared helper.
    add_dc_output_to_ec_routes(cell, int(params.num_edge_couplers_circuit.value), dc_ec_obs)
    # SSM (super-single-mode) waveguide-loss cutback, in the clear top band on the
    # RIGHT of the die (moved here from R3A, whose top band was too narrow). Upright
    # (couplers/alignment loop on the left, spirals extending right), pushed right
    # (its right edge _SSM_CUTBACK_RIGHT_MARGIN off the right inner edge) with its
    # coupler tops _SSM_CUTBACK_TOP_MARGIN below the top inner edge. Inverted in y
    # (built reverse=True: longest spiral at the top, shortest at the bottom).
    right_inner = _p.die_width.value / 2.0 - _p.keepout_width.value
    top_inner = _p.die_height.value / 2.0 - _p.keepout_width.value
    ssm_cut = test_waveguide_cutback_ssm()
    sc = ssm_cut.bbox
    cell.add_placed(
        ssm_cut,
        name="test_waveguide_cutback_ssm",
        x=(right_inner - _SSM_CUTBACK_RIGHT_MARGIN) - sc.xmax,
        y=(top_inner - _SSM_CUTBACK_TOP_MARGIN) - sc.ymax,
    )
    # Balanced-bridge crosstalk MZIs (moved here from R3A): six self-contained
    # blocks in two rows of three along the top band -- the MMI variations on top,
    # the tapered ones below -- each with its own 4-coupler GC array + alignment loop.
    add_crossing_mzis(cell)
    # Each block's west grating coupler -> that bridge's west input port.
    add_crossing_mzi_gc_routes(cell)
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    # DC bias routing on TOP_METAL: modulator-head terminals -> bond pads
    # (pads 0-3 bias, remaining pads strapped as the common ground land).
    add_dc_pad_routes(cell, second_head="test_modulator_head_2")
    return cell
