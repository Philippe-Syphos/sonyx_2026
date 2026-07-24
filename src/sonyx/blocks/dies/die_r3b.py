"""Die holder R3·B — third row, right.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): DC reflectometer
(E3) · N-tree radiating-gap isolation (E1). Frame only for now.

R3B is the **bespoke-electrode** test die: its two SM GSG modulators use a
widened signal-to-ground gap (the "safe" variant — metal pulled back from the
optical line), pinned to the PDK ``gsg_gap`` plus a per-modulator delta. The
electrode + its BOT↔TOP via are hand-built inline here (not registered PDK
cells); the taper → pad launch stays the stock PDK chain.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk
from luqia_ln200.cells.dc import via_top_bot_holes
from luqia_ln200.cells.modulators import _cover_modulator_with_moat  # shared moat draw
from luqia_ln200.cells.rf import _build_gsg_via  # shared GSG via builder (bespoke bot_xs)
from luqia_ln200.tech.cross_sections import cross_sections as _xs
from luqia_ln200.tech.cross_sections import gsg_electrode
from luqia_ln200.tech.layers import layers as _layers
from luqia_ln200.tech.parameters import parameters as _pdk
from picasso.leaves import make_straight

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ._frame import die_scaffold
from ._head_coupler_block import add_head_and_couplers

# Extra head-to-head spacing (um) on this die (mirrors R3A).
_EXTRA_HEAD_SPACING = 100.0
# Signal-to-ground gap increase (um) over the PDK gsg_gap, per modulator: the
# top electrode opens 0.5 um, the bottom 1.0 um. Pinned to the live PDK value so
# they track it (the "safe" wider-gap variant -- metal further from the mode).
_GAP_DELTA_TOP = 0.5
_GAP_DELTA_BOT = 1.0
# Metal-in-moat inclusion (um) on the electrode top/bottom edges -- matches the
# PDK modulator's _MODULATOR_METAL_MOAT_INCLUSION.
_MOD_MOAT_INCLUSION = 5.0


def _bespoke_gap_modulator(length: float, gap: float) -> fw.Component:
    """SM GSG modulator with a bespoke signal-to-ground gap (inline, not a PDK cell).

    A parameter-test copy of the PDK ``straight_gsg_modulator_800nm``: one GSG
    electrode straight (signal / ground at the process defaults, but a widened
    ``gap``) with two ``rib_sm_800nm`` ribs re-centred in the widened gaps, all
    under one ``WG_RIB.field`` moat enclosing the electrode metal. Ports match
    the PDK modulator: ``o1``/``o2`` (west), ``o3``/``o4`` (east), ``e1``/``e2``
    (electrode, on the bespoke cross-section).
    """
    signal = _pdk.gsg_signal_width.value
    ground = _pdk.gsg_ground_width.value
    electrode_xs = gsg_electrode(
        signal=signal, ground=ground, gap=gap, layer=_layers.BOT_METAL,
        name=f"gsg_electrode_bot_metal_gap{gap:g}",
    )
    # Each rib sits at the centre of a signal-to-ground gap: (signal + gap) / 2.
    rib_y = (signal + gap) / 2.0
    m = fw.Component()
    electrode = m.add_placed(make_straight(length=length, cross_section=electrode_xs), "electrode")
    rib_top = m.add_placed(
        make_straight(length=length, cross_section="rib_sm_800nm"), "rib_top", y=+rib_y
    )
    rib_bot = m.add_placed(
        make_straight(length=length, cross_section="rib_sm_800nm"), "rib_bot", y=-rib_y
    )
    # One WG_RIB.field moat over the modulator, enclosing the electrode metal by
    # _MOD_MOAT_INCLUSION um on the top/bottom edges (the PDK modulator's own moat
    # draw; the rib straights' moats union into it).
    _cover_modulator_with_moat(m, inclusion=_MOD_MOAT_INCLUSION)
    m.add_port("o1", rib_top.ports["o1"])
    m.add_port("o2", rib_bot.ports["o1"])
    m.add_port("o3", rib_top.ports["o2"])
    m.add_port("o4", rib_bot.ports["o2"])
    m.add_port("e1", electrode.ports["o1"])
    m.add_port("e2", electrode.ports["o2"])
    m.cell_type = "modulator_straight"
    return m


def _bespoke_via(gap: float) -> fw.Component:
    """Bespoke GSG electrode via: BOT_METAL at the widened ``gap``, TOP at PDK gap.

    Reuses the PDK GSG via builder with a bespoke ``bot_xs`` (the widened-gap
    electrode) and the stock ``gsg_electrode_top_metal_50ohms`` ``top_xs``. The
    <1 um ground-edge step lands at the via's top edge; the hole-array contact
    spans the ~188 um ground overlap, so the transition is electrically
    transparent. Downstream the stock taper mates the TOP (PDK) geometry.
    """
    bot_xs = gsg_electrode(
        signal=_pdk.gsg_signal_width.value, ground=_pdk.gsg_ground_width.value,
        gap=gap, layer=_layers.BOT_METAL, name=f"gsg_electrode_bot_metal_gap{gap:g}",
    )
    return _build_gsg_via(
        bot_xs=bot_xs,
        top_xs=_xs.gsg_electrode_top_metal_50ohms,
        length=_pdk.bondpad_width.value,
        description=f"bespoke GSG electrode via (BOT gap {gap:g} um, TOP PDK gap)",
        stamp=via_top_bot_holes,
    )


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
    mod_bot = cell.add_placed(mod_bot_cell, "gsg_modulator_bot", x=x0, y=bot_y)
    mod_top = cell.add_placed(mod_top_cell, "gsg_modulator_top", x=x0, y=top_y)
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
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    return cell
