"""Shared modulator_head + directional-coupler test block (R3A, R4A, R4B).

Several dies carry the same modulator_head + directional-coupler combo.
:func:`add_head_and_couplers` adds it to a die cell that already has the
modulator RF launch pads (``rf_pads_bot_in`` / ``rf_pads_bot_out`` /
``rf_pads_top_out``), so each per-die builder calls it after its RF chain.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk

# Input block (modulator_head + one directional coupler below it), anchored to
# the outer (east) edge of the lower input GSG pad group (rf_pads_bot_in.e2).
_HEAD_SHIFT_X = -500.0  # um, block right edge vs the pad's east edge (+x = right)
_HEAD_SHIFT_Y = 300.0  # um, head top below the pad centreline (+ = further down)
_HEAD_DC_SPACING = 60.0  # um, vertical gap between the head and the DC below it

# Output-side directional couplers: one above each modulator, anchored to that
# modulator's output (west) electrode port (gsg_modulator_bot/top.e1) so they
# track the modulator regardless of what terminates the output (pads or an RF
# terminator) or the electrode length. +x = die interior, +y = up.
_OUT_DC_SHIFT_X = -20.0
_OUT_DC_SHIFT_Y = 300.0


def add_head_and_couplers(
    cell: fw.Component,
    second_input_head: bool = False,
    extra_input_spacing: float = 0.0,
    input_anchor: tuple[float, float] | None = None,
) -> None:
    """Add the modulator_head + directional-coupler test block to ``cell``.

    The output DCs anchor to ``gsg_modulator_bot`` / ``gsg_modulator_top``
    (``.e1``). The input block anchors to ``input_anchor`` if given, else to
    the east edge of the lower input GSG pad group ``rf_pads_bot_in`` (``.e2``)
    -- so explicit-chain dies can omit it, while dies using the wrapped RF
    launch (R1A, which has no ``rf_pads_bot_in``) pass the launch east edge in.
    Adds:

    - ``test_modulator_head`` (dual-bias) with, right below it, either a
      ``test_directional_coupler`` (default) or a second dual-bias
      ``test_modulator_head_2`` when ``second_input_head=True`` (e.g. R3A) --
      under the input pads near the bond-pad array;
    - ``test_dc_out_bot`` / ``test_dc_out_top`` -- one directional coupler above
      each modulator, by its output pad.

    Args:
        cell: die cell carrying the modulators (and, unless ``input_anchor`` is
            given, the ``rf_pads_bot_in`` launch pads), extended in place.
        second_input_head: place a second modulator_head below the first
            (instead of a directional coupler) at the input.
        extra_input_spacing: extra vertical gap (um) added below the first head
            before the second head / DC, on top of the default spacing.
        input_anchor: ``(x, y)`` of the input pad's outer (east) edge to anchor
            the head block to. Defaults to ``rf_pads_bot_in.ports.e2.position``.
    """
    # Input: a modulator_head, then below it either a second head or a directional
    # coupler, right-aligned to the input pad's east edge (module constants above).
    if input_anchor is None:
        anchor_x, anchor_y = cell.instances["rf_pads_bot_in"].ports.e2.position
    else:
        anchor_x, anchor_y = input_anchor
    right = anchor_x + _HEAD_SHIFT_X
    head = pdk.cells["modulator_head_rib_sm_800nm_ord"](second_bias_tops=True)
    hb = head.bbox
    head_y = (anchor_y - _HEAD_SHIFT_Y) - hb.ymax
    cell.add_placed(head, "test_modulator_head", x=right - hb.xmax, y=head_y)
    if second_input_head:
        below = pdk.cells["modulator_head_rib_sm_800nm_ord"](second_bias_tops=True)
        below_name = "test_modulator_head_2"
    else:
        below = pdk.cells["directionalcoupler_rib_sm_800nm_ord_50_50"]()
        below_name = "test_directional_coupler"
    bb = below.bbox
    cell.add_placed(
        below,
        below_name,
        x=right - bb.xmax,
        y=((head_y + hb.ymin) - (_HEAD_DC_SPACING + extra_input_spacing)) - bb.ymax,
    )
    # Outputs: one directional coupler above each modulator, by its output
    # (west, e1) electrode port.
    out_dc = pdk.cells["directionalcoupler_rib_sm_800nm_ord_50_50"]()
    odb = out_dc.bbox
    for mod_name, inst_name in (
        ("gsg_modulator_bot", "test_dc_out_bot"),
        ("gsg_modulator_top", "test_dc_out_top"),
    ):
        ax, ay = cell.instances[mod_name].ports.e1.position
        cell.add_placed(
            out_dc,
            inst_name,
            x=(ax + _OUT_DC_SHIFT_X) - odb.xmin,
            y=(ay + _OUT_DC_SHIFT_Y) - odb.center_y,
        )
