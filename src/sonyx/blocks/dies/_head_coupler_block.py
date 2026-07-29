"""Shared modulator_head + directional-coupler test block (R3A, R4A, R4B).

Several dies carry the same modulator_head + directional-coupler combo.
:func:`add_head_and_couplers` adds it to a die cell that already has the
modulator RF launch pads (``rf_pads_bot_in`` / ``rf_pads_bot_out`` /
``rf_pads_top_out``), so each per-die builder calls it after its RF chain.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk
from picasso.component import PortSpec
from picasso.routing import ObstacleSet

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

# Vertical gap (um) above an extra top modulator for its rotated head + DC block.
_TOP2_GAP = 60.0


def add_top_head_and_coupler(cell: fw.Component, mod_name: str = "gsg_modulator_top_2") -> None:
    """Add a modulator_head + output directional coupler for an extra top modulator.

    The standard :func:`add_head_and_couplers` puts the modulator_head near the
    (east) input pads and the output DC at the modulator's (west) output. This is
    the **180 deg-rotated** version for a top-edge modulator (``mod_name``): the
    ``modulator_head`` (rotated 180) lands on the **left**, in the clear band
    ``_TOP2_GAP`` **above** the modulator; the output ``directional coupler``
    (rotated 180) lands on the **right**, ``_TOP2_GAP`` **below** the modulator
    (the opposite side from the head). Placement only -- not routed to the
    modulator's optical ports. Instances: ``test_modulator_head_top2`` and
    ``test_dc_out_top2``.
    """
    m = cell.instances[mod_name]
    mb = m.bbox
    assert mb is not None  # placed modulator always has geometry
    west_x = m.ports.o1.position[0]  # modulator west end
    east_x = m.ports.o3.position[0]  # modulator east end
    # Head (rotated 180) on the left, its bottom _TOP2_GAP above the modulator top.
    # rotation=180 maps local (x, y) -> (X - x, Y - y).
    head = pdk.cells["modulator_head_rib_sm_800nm_ord"](second_bias_tops=True)
    hb = head.bbox
    head_bottom = mb.ymax + _TOP2_GAP
    cell.add_placed(
        head, name="test_modulator_head_top2",
        x=west_x + hb.xmax, y=head_bottom + hb.ymax, rotation=180.0,
    )
    # Output directional coupler (rotated 180) on the right, its top _TOP2_GAP
    # below the modulator bottom (the opposite side from the head).
    dc = pdk.cells["directionalcoupler_rib_sm_800nm_ord_50_50"]()
    db = dc.bbox
    dc_top = mb.ymin - _TOP2_GAP
    cell.add_placed(
        dc, name="test_dc_out_top2",
        x=east_x + db.xmin, y=dc_top + db.ymin, rotation=180.0,
    )


def add_head_input_routes(
    cell: fw.Component,
    num_edge_couplers: int,
    second_device: str = "test_directional_coupler",
) -> None:
    """Feed the input block (``test_modulator_head`` + a second input device).

    Routes one circuit edge coupler into a west input of each input device, so the
    edge facet is the block's optical input. Edge-coupler allocation (see
    :func:`._frame.die_scaffold`): ``c0`` / ``c1`` are the alignment loopback and
    the two rightmost couplers (``c_{num-1}`` / ``c_{num-2}``) feed the SM delay
    spiral, so the next two rightmost-available couplers feed this block.

    Both routes run in a **single bundle** ``autoroute`` so the two lanes share a
    coherent ordering and stay parallel (two separate calls plan independently and
    cross). The pairing sends the more-western source (``c_{num-4}``) to the first
    head and the more-eastern source (``c_{num-3}``) to ``second_device`` -- the
    planar (non-crossing) matching for both layouts this serves:

    - common dies: ``second_device="test_directional_coupler"`` -- the two targets
      differ in x (head ~ 3.6 mm, DC ~ 4.6 mm), so west-source -> west-target;
    - R3B: ``second_device="test_modulator_head_2"`` -- both heads share x and
      differ in y (first head upper, second head lower), so the west source feeds
      the upper head and the east source the lower head (verified crossing-free).

    Both targets are ``o1`` (a west optical input). Default (non-tight) SM routing.
    Requires ``num_edge_couplers >= 4``.
    """
    head_ec = num_edge_couplers - 3  # more-eastern source
    dc_ec = num_edge_couplers - 4  # more-western source
    ec_ports: list[PortSpec] = [
        ("edge_couplers_circuit", f"o2_r0_c{dc_ec}"),
        ("edge_couplers_circuit", f"o2_r0_c{head_ec}"),
    ]
    input_ports: list[PortSpec] = [
        ("test_modulator_head", "o1"),
        (second_device, "o1"),
    ]
    cell.autoroute(
        ports_a=ec_ports,
        ports_b=input_ports,
        spec="routing_sm_default",
        strategy="vgraph_rect",
    )


def add_mzm_input_routes(
    cell: fw.Component, second_device: str = "test_directional_coupler"
) -> None:
    """Route the input stage's two 2x2 couplers to the two MZMs (modulators).

    The head's two outputs feed the top modulator's two arms and ``second_device``'s
    two outputs feed the bottom modulator's two arms, in a **single 4-lane bundle**.
    Targets are the modulators' **east** ports (``o3`` / ``o4``) -- the same side as
    the input stage -- so every target shares one outward heading (a bundle
    requires that) and the lanes stay on the east side rather than crossing the die
    to the west inputs. The pairing is y-monotonic (upper source -> upper target:
    head -> top modulator, ``second_device`` -> bottom modulator), so the lanes
    don't cross. Default (non-tight) SM routing.

    ``second_device`` is the input stage's lower device: ``test_directional_coupler``
    on the common head+DC dies, or ``test_modulator_head_2`` on the two-head dies
    (R3A / R3B). Both expose east outputs ``o3`` / ``o4``.
    """
    src: list[PortSpec] = [
        ("test_modulator_head", "o3"),
        ("test_modulator_head", "o4"),
        (second_device, "o3"),
        (second_device, "o4"),
    ]
    tgt: list[PortSpec] = [
        ("gsg_modulator_top", "o3"),
        ("gsg_modulator_top", "o4"),
        ("gsg_modulator_bot", "o3"),
        ("gsg_modulator_bot", "o4"),
    ]
    cell.autoroute(ports_a=src, ports_b=tgt, spec="routing_sm_default", strategy="vgraph_rect")


def add_mzm_output_routes(cell: fw.Component) -> ObstacleSet:
    """Route each MZM's outputs (o1/o2, west) into its output directional coupler.

    Two calls -- one per modulator -- each a 2-lane bundle from a modulator's two
    west output arms into the two **west** ports of the output DC that sits just
    above that modulator's west end (``test_dc_out_bot`` / ``test_dc_out_top``,
    placed by :func:`add_head_and_couplers`). The DC's west ports are ~20 um west
    of the modulator outputs, so each bundle is a tight local loop; the DC's east
    ports would instead force a full-die-width wrap. The pairing is y-monotonic
    (upper arm -> upper DC port: ``o1`` -> ``o2``, ``o2`` -> ``o1``) so the two
    lanes don't cross. Default (non-tight) SM routing.

    This is the first step of the DC-output routing chain, so it also builds and
    returns the chain's shared :class:`~picasso.routing.ObstacleSet`, seeded with
    the two modulator electrode bboxes. Each MZM->DC route is planned against the
    set, materialised eagerly, then registered back into it (routes tier, actual
    wire polygons) -- so the second route avoids the first, and the caller can keep
    reusing the returned set for the downstream DC->EC routes, which then detour
    around both the electrodes and every route already placed (they share the west
    corridor). ``autoroute`` excludes each route's own endpoint-owner modulator, so
    routing off a modulator port is unaffected by the electrode obstacles.
    """
    obs = ObstacleSet(name="dc_output_chain")
    obs.add_instance(cell.instances["gsg_modulator_bot"])
    obs.add_instance(cell.instances["gsg_modulator_top"])
    pairs = (
        ("gsg_modulator_bot", "test_dc_out_bot", "mzm_dc_bot"),
        ("gsg_modulator_top", "test_dc_out_top", "mzm_dc_top"),
    )
    for mod, dc, name in pairs:
        cell.autoroute(
            ports_a=[(mod, "o1"), (mod, "o2")],
            ports_b=[(dc, "o2"), (dc, "o1")],
            obstacles=obs,
            materialize=True,
            spec="routing_sm_default",
            strategy="vgraph_rect",
            name=name,
            start_straight=120.0
        )
        # Register the just-materialised route as an obstacle for later routes in
        # the chain. Use the route's *bbox* (add_instance) rather than its full wire
        # polygons (add_polygons(route_polygons_for_child(...))): grid_astar's
        # exclude_rings / contains then process one rectangle instead of ~20-50
        # polygons -- ~8x faster on the downstream grid_astar DC->EC drop. Safe here
        # because these MZM->DC loops are compact (bbox ~= the route); for a long
        # L/U route whose bbox is mostly empty, prefer the polygon form.
        # Registers into the default USER_TIER (autoroute only reads a passed set's
        # USER/CONTAINMENT tiers; ROUTES_TIER is for resolve_routes(route_obstacles=True)).
        obs.add_instance(cell.instances[name])
    return obs


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
    cell.add_placed(head, name="test_modulator_head", x=right - hb.xmax, y=head_y)
    if second_input_head:
        below = pdk.cells["modulator_head_rib_sm_800nm_ord"](second_bias_tops=True)
        below_name = "test_modulator_head_2"
    else:
        below = pdk.cells["directionalcoupler_rib_sm_800nm_ord_50_50"]()
        below_name = "test_directional_coupler"
    bb = below.bbox
    cell.add_placed(
        below,
        name=below_name,
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
            name=inst_name,
            x=(ax + _OUT_DC_SHIFT_X) - odb.xmin,
            y=(ay + _OUT_DC_SHIFT_Y) - odb.center_y,
        )
