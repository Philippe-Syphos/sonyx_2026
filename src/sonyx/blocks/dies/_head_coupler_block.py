"""Shared modulator_head + directional-coupler test block (R3A, R4A, R4B).

Several dies carry the same modulator_head + directional-coupler combo.
:func:`add_head_and_couplers` adds it to a die cell that already has the
modulator RF launch pads (``rf_pads_bot_in`` / ``rf_pads_bot_out`` /
``rf_pads_top_out``), so each per-die builder calls it after its RF chain.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk
from luqia_ln200.tech.parameters import parameters as _pdk
from picasso.component import PortSpec
from picasso.routing import ObstacleSet
from picasso.routing.obstacles import route_element_bboxes_for_child

from ...parameters import parameters as _p
from ..beam_dumps import add_2x2_input_beam_dumps
from ..labels import DC_PAD_LABEL_HEIGHT, add_vertical_label
from ._frame import place_thermistance_pad

# Input block (modulator_head + one directional coupler below it), anchored to
# the outer (east) edge of the lower input GSG pad group (rf_pads_bot_in.e2).
_HEAD_SHIFT_X = -500.0  # um, block right edge vs the pad's east edge (+x = right)
_HEAD_SHIFT_Y = 550.0  # um, head top below the pad centreline (+ = further down)
_HEAD_DC_SPACING = 60.0  # um, vertical gap between the head and the DC below it

# Output-side directional couplers: one above each modulator, anchored to that
# modulator's output (west) electrode port (gsg_modulator_bot/top.e1) so they
# track the modulator regardless of what terminates the output (pads or an RF
# terminator) or the electrode length. +x = die interior, +y = up.
_OUT_DC_SHIFT_X = -20.0
_OUT_DC_SHIFT_Y = 300.0

# Vertical gap (um) between an extra top modulator and its rotated head / DC block.
# The DC keeps the tight default gap; the head sits 150 um further out, to leave a
# routing channel between the modulator's optical ports and the head.
_TOP2_GAP = 60.0
_TOP2_HEAD_GAP = _TOP2_GAP + 150.0

# DC bias pads for an extra top modulator's head, in the die's north-west corner:
# five small (120 um square) TOP_METAL bond pads -- one signal per heater (coupler /
# phase / phase2) plus a ground at each end -- tiled west-to-east at the PDK
# bondpad_pitch, tops flush with the keep-out inner north wall and starting
# _TOP2_PAD_CORNER_GAP east of the corner alignment grating coupler.
#
# The gap was opened up by 300 um (150 -> 450) to slide the whole row east: it puts
# the three centre (signal) pads east of the head's two east-facing TOPS bias
# terminals, so those lines run east-then-north into the row instead of doubling
# back west across each other.
_TOP2_NUM_DC_PADS = 5
_TOP2_PAD_CORNER_GAP = 450.0

# Label per north-west DC pad (1 = west-most), matching the wiring in
# :func:`add_top2_dc_pad_routes`: grounds on the two end pads, the three centre
# pads one signal each. ``T2-`` marks the row apart from the main array's pads,
# which on R1B carry the same functions for the other modulator head.
_TOP2_PAD_LABEL_TEXTS = {
    1: "T2-BIAS-GND",
    2: "T2-BIAS-SIG-1",
    3: "T2-BIAS-SIG-2",
    4: "T2-TC-SIG",
    5: "T2-TC-GND",
}
# Gap (um) below a pad before its label starts, and the margin the labels are
# grown by when registered as routing obstacles (the top-metal spec's own
# clearance is 9.6 um, so 10 keeps a lane a full clearance off the glyphs).
#
# The gap is 50, not the ~10 the pads themselves would allow, because obstacles
# only steer a route's *path*: the last jog into a pad's south face is the
# planner's landing approach and runs regardless. That jog occupies roughly the
# 40 um directly under the row, so the labels start below it and let the lines
# come in over their heads.
_TOP2_LABEL_PAD_GAP = 50.0
_TOP2_LABEL_KEEPOUT = 10.0

# Margin (um) grown around each edge-coupler fiducial when it is registered as a
# routing obstacle. Routes are planned on the rib core, but their WG_RIB.field
# moat runs slab_width (6 um) beyond it, so the core alone clearing the mark is
# not enough. 10 um covers the moat and matches the nominal gap PDK rule 10.3
# wants between field fill and functional structures.
_FIDUCIAL_KEEPOUT = 10.0

# Input-stage 2x2 devices whose spare west input is terminated by
# :func:`add_input_beam_dumps`. Only one of the two west inputs of each is fed
# from an edge coupler; the other is a bare open facet unless it is dumped. These
# are the instance names :func:`add_head_and_couplers` creates (plus R3A/R3B's
# second head), so the tuple doubles as the roster of input devices on any die --
# names absent from a given die are skipped.
_INPUT_STAGE_DEVICES = (
    "test_modulator_head",
    "test_modulator_head_2",
    "test_directional_coupler",
)


def add_top_head_and_coupler(cell: fw.Component, mod_name: str = "gsg_modulator_top_2") -> None:
    """Add a modulator_head + output directional coupler for an extra top modulator.

    The standard :func:`add_head_and_couplers` puts the modulator_head near the
    (east) input pads and the output DC at the modulator's (west) output. This is
    the **180 deg-rotated** version for a top-edge modulator (``mod_name``): the
    ``modulator_head`` (rotated 180) lands on the **left**, in the clear band
    ``_TOP2_HEAD_GAP`` **above** the modulator; the output ``directional coupler``
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
    # Head (rotated 180) on the left, its bottom _TOP2_HEAD_GAP above the modulator top.
    # rotation=180 maps local (x, y) -> (X - x, Y - y).
    head = pdk.cells["modulator_head_rib_sm_800nm_ord"](second_bias_tops=True)
    hb = head.bbox
    head_bottom = mb.ymax + _TOP2_HEAD_GAP
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


def add_top2_dc_pads(cell: fw.Component, prefix: str = "top2_dc_pad") -> None:
    """Place ``_TOP2_NUM_DC_PADS`` DC bias pads in the die's north-west corner.

    Bias pads for the extra top modulator's head (:func:`add_top_head_and_coupler`),
    which carries three heaters (coupler / phase / phase2, six terminals) -- so the
    five pads are one signal each plus a ground pad at either end of the row. The
    small square ``bondpad_top_metal`` (120 um, the PDK DC probe / wirebond pad) tiled
    west to east at the PDK ``bondpad_pitch``, as in the die's own wirebond array --
    not the 200 x 200 um ``bondpad_for_test_top``.

    The row sits in the top-left corner **beside** the north-west alignment grating
    coupler (``gc_align_tl``, always placed by :func:`._frame.die_scaffold`): tops
    flush with the keep-out inner north wall, the first pad's left edge
    ``_TOP2_PAD_CORNER_GAP`` east of the coupler. Instances ``{prefix}_{i}``, wired
    to the head by :func:`add_top2_dc_pad_routes`.
    """
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    gcb = cell.instances["gc_align_tl"].bbox
    assert gcb is not None  # placed by die_scaffold on every die
    pad = pdk.cells["bondpad_top_metal"]()
    pb = pad.bbox
    pitch = _pdk.bondpad_pitch.value
    x_center0 = (gcb.xmax + _TOP2_PAD_CORNER_GAP) + pb.dx / 2.0
    y_center = (half_h - kw) - pb.dy / 2.0
    for i in range(_TOP2_NUM_DC_PADS):
        cell.add_placed(pad, name=f"{prefix}_{i + 1}", x=x_center0 + i * pitch, y=y_center)
    add_top2_dc_pad_labels(cell, prefix)


def add_top2_dc_pad_labels(cell: fw.Component, prefix: str = "top2_dc_pad") -> None:
    """Name each north-west DC pad, hanging south off its west edge.

    The row's tops are flush with the keep-out ring and its south side is the
    routing fan-in, so there is no free side to stand these labels on the way the
    main array's east strip is free. Instead each label hangs into its own pad's
    south approach, flush with that pad's west edge, leaving the rest of the
    120 um face for the line landing on it — and :func:`add_top2_dc_pad_routes`
    registers the labels as obstacles so those lines keep off them.

    Placed here rather than after routing precisely so that registration is
    possible. Texts mirror :func:`..dc_routing.dc_pad_label_texts` with a ``T2-``
    prefix, since on R1B this row and the main array both serve a modulator head
    and identical texts would be ambiguous.
    """
    for i, text in _TOP2_PAD_LABEL_TEXTS.items():
        pb = cell.instances[f"{prefix}_{i}"].bbox
        add_vertical_label(
            cell,
            text,
            wg_x=pb.xmin,
            y_top=pb.ymin - _TOP2_LABEL_PAD_GAP,
            gap=0.0,
            height=DC_PAD_LABEL_HEIGHT,
            name=f"label_{prefix}_{i}",
        )


def add_top2_routes(cell: fw.Component, mod_name: str = "gsg_modulator_top_2") -> ObstacleSet:
    """Route the extra top modulator's head in and its output DC out.

    The 180 deg-rotated twin of :func:`add_mzm_input_routes` (head -> MZM) plus
    :func:`add_mzm_output_routes` (MZM -> output DC) for the block placed by
    :func:`add_top_head_and_coupler`. Same specs, strategies, bundling and
    ``start_straight`` as the un-rotated pair -- only the port names differ, because
    the head and the DC are rotated 180 deg while the modulator is not:

    - **input** (2-lane bundle): the head's outputs face **west** after rotation
      (``o3`` / ``o4``) and feed the modulator's **west** arms (``o1`` / ``o2``) --
      the mirror of head-east-outputs into modulator-east-arms.
    - **output** (2-lane bundle): the modulator's **east** arms (``o3`` / ``o4``)
      feed the output DC's **east** ports (``o1`` / ``o2``), which after rotation are
      the ones facing the modulator -- the mirror of west-arms into DC-west-ports.

    Both pairings are y-monotonic (upper source -> upper target), which is what the
    un-rotated pair uses and what the mirror preserves, so the lanes don't cross.

    Returns the output route's :class:`~picasso.routing.ObstacleSet`, seeded with the
    modulator electrode and with the materialised route registered back (per-wire-
    shape bboxes) -- the same contract as :func:`add_mzm_output_routes`, so a caller
    can keep routing this DC onward (nothing does yet; the DC's far side is still
    open). Targeted registration, not the ``add_routes`` live rule: the live rule
    fingerprints and extracts **every** route on the die on each query, which
    measures ~35% slower on the full build for these chain-local sets.
    """
    head = "test_modulator_head_top2"
    dc = "test_dc_out_top2"
    # Head (west-facing outputs) -> modulator west arms: o3 is the lower output after
    # the 180 deg rotation, so it pairs with the lower arm o2.
    cell.autoroute(
        ports_a=[(head, "o3"), (head, "o4")],
        ports_b=[(mod_name, "o2"), (mod_name, "o1")],
        spec="routing_sm_default",
        strategy="vgraph_rect",
        name="mzm_in_top2",
    )
    # Modulator east arms -> output DC east ports, planned against the electrode.
    obs = ObstacleSet(name="top2_output_chain")
    obs.add_instance(cell.instances[mod_name])
    cell.autoroute(
        ports_a=[(mod_name, "o3"), (mod_name, "o4")],
        ports_b=[(dc, "o1"), (dc, "o2")],
        obstacles=obs,
        spec="routing_sm_default",
        strategy="vgraph_rect",
        name="mzm_dc_top2",
        start_straight=120.0,
    )
    obs.add_polygons(route_element_bboxes_for_child(cell, "mzm_dc_top2"))
    return obs


def add_top2_gc_routes(
    cell: fw.Component, obstacles: ObstacleSet, gc_prefix: str = "mod_top2_gc"
) -> None:
    """Route the extra top modulator's 4 open grating couplers to its head and DC.

    The fibre I/O counterpart of :func:`add_head_input_routes` (coupler -> head
    input) and :func:`add_dc_output_to_ec_routes` (output DC -> couplers), with
    the top-right ``{gc_prefix}`` open-GC-array block
    (:func:`..gc_test_array.open_gc_array_block`, exposed ports ``o1_r0_c0..c3``
    facing **south**) standing in for the circuit edge couplers. All four
    channels are used -- the block has one 2x2 head (two inputs) and one output
    DC (two outputs):

    - the **two western** couplers (``c0`` / ``c1``) feed the head's inputs, which
      face east after the 180 deg rotation (``o1`` / ``o2``);
    - the **two eastern** couplers (``c2`` / ``c3``) take the output DC's open ports
      (``o3`` / ``o4``), which face **west** -- away from the couplers -- so they get
      the same :func:`add_dc_uturn_stubs` treatment as the standard top DC's drop,
      re-orienting them east before the bundle is planned. Without the stubs the
      lanes wrap the long way round the electrode's far (west) end and cross the
      head's own routes.

    Both pairings are planar: within a bundle the more-eastern coupler drops to the
    lower target, so its westward leg passes below -- not across -- its neighbour's
    descent. Splitting the head and DC halves at ``c1`` / ``c2`` keeps the two
    bundles apart too: the head lanes stay west of the DC lanes' descent.

    ``obstacles`` is the top2 chain from :func:`add_top2_routes` (electrode + the
    MZM -> DC route); the head bundle is registered back (per-wire-shape bboxes),
    so the DC lanes avoid the head lanes.
    """
    head = "test_modulator_head_top2"
    dc = "test_dc_out_top2"
    arr = gc_prefix  # the open-GC-array block instance; coupler ports exposed on it
    # Western pair -> head inputs. c0 (west) takes the upper input o1, c1 the lower
    # o2, so c1's westward leg runs below c0's descent instead of crossing it.
    cell.autoroute(
        ports_a=[(arr, "o1_r0_c0"), (arr, "o1_r0_c1")],
        ports_b=[(head, "o1"), (head, "o2")],
        obstacles=obstacles,
        spec="routing_sm_default",
        strategy="vgraph_rect",
        name="gc_head_top2",
    )
    obstacles.add_polygons(route_element_bboxes_for_child(cell, "gc_head_top2"))
    # Eastern pair -> output DC, off east-facing U-turn stubs. Same ordering rule:
    # c2 (west of c3) takes the upper stub end, c3 the lower one. Nothing consumes
    # the set after this call, so the bundle is not registered back.
    stub_ends = add_dc_uturn_stubs(cell, dc, "dc_top2_stub")
    cell.autoroute(
        ports_a=[(arr, "o1_r0_c2"), (arr, "o1_r0_c3")],
        ports_b=sorted(stub_ends, key=lambda s: -cell.instances[s[0]].ports[s[1]].position[1]),
        obstacles=obstacles,
        spec="routing_sm_default",
        strategy="vgraph_rect",
        name="gc_dc_top2",
    )


def add_top2_dc_pad_routes(cell: fw.Component, prefix: str = "top2_dc_pad") -> None:
    """Wire the extra top modulator's head heaters to its north-west DC pads.

    The counterpart of :func:`..dc_routing.add_dc_pad_routes` for the rotated
    ``test_modulator_head_top2`` and the four pads placed by
    :func:`add_top2_dc_pads`, on the same ``routing_top_metal`` spec / ``vgraph_rect``
    planner and with the same ``avoid_port_owners=False`` (DC metal runs over the
    blocks it wires). One signal pad per heater, with a **ground pad at each end** of
    the row: the two TOPS phase shifters are grounded on their **west** terminals and
    the tunable coupler on its **east-most** terminal, so each heater's other end is
    its signal:

    - ``{prefix}_1`` (west-most) <- ``e_phase_2`` + ``e_phase2_2`` -- **ground** (the
      two west bias terminals).
    - ``{prefix}_2`` <- ``e_phase2_1``  (upper TOPS phase shifter, signal)
    - ``{prefix}_3`` <- ``e_phase_1``   (lower TOPS phase shifter, signal)
    - ``{prefix}_4`` <- ``e_coupler_2`` (tunable-coupler / split-ratio heater, signal)
    - ``{prefix}_5`` (east-most) <- ``e_coupler_1`` -- **ground** (the tunable
      coupler's east-most terminal).

    The two grounds are the fixed points of the scheme (each heater's outer terminal
    lands on the nearest end pad); the three centre signal pads follow from the pad
    row's 300 um east shift (see ``_TOP2_PAD_CORNER_GAP``) and from the coupler taking
    the **east-most** of them: ``e_coupler_2`` faces west and sits east of the whole
    row, so pad 4 is the one it reaches on a plain west-then-north leg without
    crossing anything. That leaves pads 2 + 3 for the head's two east-facing TOPS
    terminals as a **single two-lane bundle**, paired upper-terminal-to-western-pad
    (``e_phase2_1`` -> pad 2, ``e_phase_1`` -> pad 3): the upper lane turns north and
    doubles back west first, while the lower one runs east underneath it before rising
    to pad 3, so the lanes don't cross.

    Every line lands on its pad's **south** face -- the one looking back down at the
    head. Apart from the TOPS bundle each line is its own call, because a bundle needs
    every lane to share an outward heading and a multi-lane fan onto a single 120 um
    pad face is narrower than the bend offsets allow.
    """
    head = "test_modulator_head_top2"
    # The pad labels hang into these lines' approach corridor (there is no free
    # side for them up here -- see add_top2_dc_pad_labels), so reserve them first
    # and plan every line against the set. Grown by _TOP2_LABEL_KEEPOUT so a lane
    # keeps a full top-metal clearance off the glyphs rather than grazing them.
    obs = ObstacleSet(name="top2_dc_pad_labels")
    for i in _TOP2_PAD_LABEL_TEXTS:
        lb = cell.instances.get(f"label_{prefix}_{i}")
        if lb is None:
            continue
        b, m = lb.bbox, _TOP2_LABEL_KEEPOUT
        obs.add_polygons(
            [
                [
                    (b.xmin - m, b.ymin - m),
                    (b.xmax + m, b.ymin - m),
                    (b.xmax + m, b.ymax + m),
                    (b.xmin - m, b.ymax + m),
                ]
            ],
            key=f"label_{prefix}_{i}_keepout",
        )

    def line(terms: tuple[str, ...], pad: int, name: str, *, fan: bool = False) -> None:
        cell.autoroute(
            ports_a=[(head, t) for t in terms],
            ports_b=[(f"{prefix}_{pad}", "s")] * len(terms),
            obstacles=obs,
            spec="routing_top_metal",
            strategy="vgraph_rect",
            avoid_port_owners=False,
            fan_out=fan or None,
            name=name,
        )

    # Ground, west end: the two west bias terminals, one call each.
    line(("e_phase_2",), 1, "top2_dc_gnd_phase")
    line(("e_phase2_2",), 1, "top2_dc_gnd_phase2")
    # Coupler signal on the east-most centre pad -- the one its west-facing terminal
    # reaches without crossing anything. Its own call.
    line(("e_coupler_2",), 4, "top2_dc_bias_coupler")
    # Signals: the two east-facing TOPS terminals as one bundle onto the two centre
    # pads the coupler leaves free (2/3), upper terminal -> western pad so the lanes
    # stay planar.
    cell.autoroute(
        ports_a=[(head, "e_phase2_1"), (head, "e_phase_1")],
        ports_b=[(f"{prefix}_2", "s"), (f"{prefix}_3", "s")],
        obstacles=obs,
        spec="routing_top_metal",
        strategy="vgraph_rect",
        avoid_port_owners=False,
        fan_out=True,
        name="top2_dc_bias_tops",
    )
    # Ground, east end: the tunable coupler's east-most terminal.
    line(("e_coupler_1",), 5, "top2_dc_gnd_coupler")


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


def add_input_beam_dumps(cell: fw.Component, prefix: str = "beamdump") -> list[str]:
    """Terminate every unfed west input of the MZM circuit's input-stage devices.

    Each input-stage device (:data:`_INPUT_STAGE_DEVICES`) is a 2x2: the circuit
    drives **one** of its two west inputs from an edge coupler and leaves the other
    open, so the unused arm ends in a bare facet that reflects straight back into
    the coupler. This puts a PDK ``beam_dump_rib_sm_800nm`` on each such port.

    Thin wrapper over :func:`..beam_dumps.add_2x2_input_beam_dumps` naming this
    die family's roster: which of ``o1`` / ``o2`` is spare is not fixed (``o2`` on
    the common dies, but ``o1`` on R3A's lower head, which is fed on its nearer
    port), so the shared helper reads it off ``cell.nets`` and mirrors each dump
    away from the fed sibling. **Call this after the die's input routing**, or it
    will dump ports that are about to be fed.

    Returns:
        The instance names of the dumps placed, in the order they were added.
    """
    return add_2x2_input_beam_dumps(cell, _INPUT_STAGE_DEVICES, prefix=prefix)


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
    cell.autoroute(ports_a=src, ports_b=tgt, spec="routing_sm_default", strategy="vgraph_rect",
                   end_straight=1.0, start_straight=1.0
                   )


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
    set, materialised eagerly, then registered back into it as its whole-route
    bbox (``add_instance``) -- these loops are compact, so bbox ~= route and one
    rectangle is the cheapest footprint the downstream consumers can get. The
    second route avoids the first, and the caller can keep reusing the returned
    set for the downstream DC->EC routes, which then detour around both the
    electrodes and every route already placed (they share the west corridor).
    ``autoroute`` excludes each route's own endpoint-owner modulator, so routing
    off a modulator port is unaffected by the electrode obstacles. (Targeted
    registration, not the ``add_routes`` live rule -- the live rule tracks every
    route on the die and measures ~35% slower on the full build.)
    """
    obs = ObstacleSet(name="dc_output_chain")
    obs.add_instance(cell.instances["gsg_modulator_bot"])
    obs.add_instance(cell.instances["gsg_modulator_top"])
    # The scaffold's edge-coupler fiducials sit in the west corridor these routes
    # drop through (the western one straddles open-coupler axes these outputs
    # land on, so its footprint has to be reserved before the drops are planned),
    # so seed them too -- a route crossing a registration mark spoils it. Grown by
    # _FIDUCIAL_KEEPOUT: the guiding layer is the rib core, but each route also
    # drags a WG_RIB.field moat slab_width beyond it, which would otherwise clip
    # the mark even with the core routed clear.
    for fid_name in (
        "fiducial_ec_circuit",
        "fiducial_ec_circuit_mid",
        "fiducial_spiral_south",
        "fiducial_corner_bl",
    ):
        if fid_name in cell.instances:
            fb = cell.instances[fid_name].bbox
            m = _FIDUCIAL_KEEPOUT
            obs.add_polygons(
                [
                    [
                        (fb.xmin - m, fb.ymin - m),
                        (fb.xmax + m, fb.ymin - m),
                        (fb.xmax + m, fb.ymax + m),
                        (fb.xmin - m, fb.ymax + m),
                    ]
                ],
                key=f"{fid_name}_keepout",
            )
    pairs = (
        ("gsg_modulator_bot", "test_dc_out_bot", "mzm_dc_bot"),
        ("gsg_modulator_top", "test_dc_out_top", "mzm_dc_top"),
    )
    for mod, dc, name in pairs:
        cell.autoroute(
            ports_a=[(mod, "o1"), (mod, "o2")],
            ports_b=[(dc, "o2"), (dc, "o1")],
            obstacles=obs,
            spec="routing_sm_default",
            strategy="vgraph_rect",
            name=name,
            start_straight=120.0,
        )
        obs.add_instance(cell.instances[name])
    return obs


def add_dc_uturn_stubs(cell: fw.Component, dc_name: str, prefix: str) -> list[PortSpec]:
    """Flip a directional coupler's open ``o3`` / ``o4`` around with U-turn stubs.

    ``grid_astar`` (and, on a long haul, ``vgraph_rect`` too) wraps the long way
    round when a start port faces away from its goal -- see the routing handoff. A
    **bend-bend (two L-bend) U-turn stub** on each open port re-orients it 180 deg
    first, so the drop that follows starts pointing at its targets.

    The two U-turns are only ~21 um apart (the DC's port pitch), so the ``o4`` one is
    pushed clear: a 10 um straight before its first bend and a 40 um straight between
    its two bends, which also makes it the wider, outer U-turn. Instances
    ``{prefix}0_o4`` / ``{prefix}1_{p}`` / ``{prefix}_mid_o4`` / ``{prefix}2_{p}``.

    Returns the two stub end ports (``o3``'s first), ready as ``ports_a`` for the
    drop's ``autoroute``.
    """
    stub_ends: list[PortSpec] = []
    for p, pre_straight, mid_straight in (("o3", 0.0, 0.0), ("o4", 10.0, 40.0)):
        anchor: PortSpec = (dc_name, p)
        if pre_straight > 0.0:
            s = cell.put(
                pdk.cells["straight_rib_sm_800nm"](length=pre_straight), anchor,
                port_to="o1", name=f"{prefix}0_{p}",
            )
            anchor = (s.name, "o2")
        b1 = cell.put(
            pdk.cells["lbend_rib_sm_800nm"](), anchor, port_to="o1", name=f"{prefix}1_{p}"
        )
        anchor = (b1.name, "o2")
        if mid_straight > 0.0:
            s = cell.put(
                pdk.cells["straight_rib_sm_800nm"](length=mid_straight), anchor,
                port_to="o1", name=f"{prefix}_mid_{p}",
            )
            anchor = (s.name, "o2")
        b2 = cell.put(
            pdk.cells["lbend_rib_sm_800nm"](), anchor, port_to="o1", name=f"{prefix}2_{p}"
        )
        stub_ends.append((b2.name, "o2"))
    return stub_ends


def add_dc_output_to_ec_routes(
    cell: fw.Component, num_edge_couplers: int, obstacles: ObstacleSet
) -> None:
    """Route both output DCs down to the open circuit edge couplers.

    Edge-coupler allocation (see :func:`._frame.die_scaffold`): with ``c0`` / ``c1``
    the loopback, the two rightmost feeding the spiral and the next two the input
    block, the four *open* couplers are the middle ``c2..c5`` (for ``num=10``). The
    bottom output DC feeds the two rightmost open (``c_{num-5}`` / ``c_{num-6}``) and
    the top DC the next two (``c_{num-7}`` / ``c_{num-8}``).

    Both DCs face **east**. The bottom drop reaches the west corridor directly with
    vgraph_rect. The top drop would otherwise wrap the long way east (a grid_astar
    quirk when the start port faces away from the goal -- see the routing handoff),
    so its outputs get a **bend-bend (two L-bend) U-turn stub** first, re-orienting
    them **west**; the lower (``o4``) stub gets a 10 um straight before its first bend
    and a 40 um straight between its two bends, so the two U-turns (only ~21 um apart)
    don't collide -- the ``o4`` U-turn ends up wider and further west than the ``o3``
    one. ``obstacles`` is the shared DC-output-chain
    set from :func:`add_mzm_output_routes`; the bottom drop is registered back
    (per-wire-shape bboxes) so the top drop avoids it.
    """
    n = num_edge_couplers
    # Bottom output DC -> the two rightmost open edge couplers.
    cell.autoroute(
        ports_a =[("test_dc_out_bot", "o3"), ("test_dc_out_bot", "o4")],
        ports_b=[
            ("edge_couplers_circuit", f"o2_r0_c{n - 5}"),
            ("edge_couplers_circuit", f"o2_r0_c{n - 6}"),
        ],
        obstacles=obstacles,
        spec="routing_sm_default",
        strategy="grid_astar",
        step=30.0,
        # start_straight=50.0,
        end_straight=200.0,
        name="dc_ec_bot",
    )
    # Long L/U drop -- register per-wire-shape bboxes (route_element_bboxes_for_
    # child), not its whole-route bbox (mostly empty, would over-block the top
    # drop's shared west corridor) and not its exact wire outlines (a bend carries
    # ~150 vertices of curvature the consumers don't need and scale with).
    obstacles.add_polygons(route_element_bboxes_for_child(cell, "dc_ec_bot"))
    # Top output DC -> the next two open edge couplers, via a west-facing U-turn stub.
    top_stub_ends = add_dc_uturn_stubs(cell, "test_dc_out_top", "dc_top_stub")
    cell.autoroute(
        ports_a=top_stub_ends,
        ports_b=[
            ("edge_couplers_circuit", f"o2_r0_c{n - 7}"),
            ("edge_couplers_circuit", f"o2_r0_c{n - 8}"),
        ],
        obstacles=obstacles,
        spec="routing_sm_default",
        strategy="vgraph_rect",
        start_straight=50.0,
        end_straight=100.0,
        name="dc_ec_top",
    )


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
    # Shared hook (every die calls this helper): move the scaffold's parked
    # thermistance bonding pad onto its hard-coded per-die centre.
    place_thermistance_pad(cell)
