"""DC bias routing on TOP_METAL — die bond pads to on-die DC terminals.

Wires each die's lower-right DC bond-pad array to the thermo-optic / DC
terminals scattered across the die, on the PDK ``routing_top_metal`` routing
spec (20 µm AlCu trace, flush Manhattan L-bends, 9.6 µm clearance / 29.6 µm
lane pitch). All the DC terminals we target (heater terminals on the modulator
head, TOPS phase shifters, …) already present their ports on
``routing_top_metal``, so no cross-section transition is needed.

**Pad numbering.** Pads are addressed by :func:`dc_pad_port` as ``0, 1, 2, …``
counting from the **bottom** of the array upward, independent of the array's
internal ``make_array`` column naming.

**Pad side.** Routes always land on a pad's **west** face — the pads sit at the
die's right edge, so the west face is the one looking back into the die. Note
the pad array is placed ``rotation=90`` by :func:`~sonyx.blocks.dies._frame.die_scaffold`,
which rotates the port *poses* but not their *names*: the cardinal port named
``"w"`` ends up facing **south**, and the physically west-facing port is the one
named ``"n"``. :func:`dc_pad_port` therefore selects by port **orientation**
(180°), not by name, so it stays correct if the array rotation ever changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .labels import DC_PAD_LABEL_HEIGHT, add_horizontal_label

if TYPE_CHECKING:
    import picasso as fw
    from picasso.component import PortSpec

# Routing spec for every DC bias line (see luqia_ln200.tech.routing_specs).
_DC_SPEC = "routing_top_metal"
# vgraph_rect is the only planner that gets out of the modulator head's dense
# neighbourhood: grid_astar's approach-lane carve finds the coupler terminal
# fully enclosed by the surrounding geometry at any usable step size.
_DC_STRATEGY = "vgraph_rect"

_PAD_ARRAY = "bondpads"

# Gap (um) between a bond pad's west face and its label's east moat edge.
_DC_PAD_LABEL_GAP = 9.0

# End-straight (um) on the shared-ground rail. Pushes the run off the pad faces
# before it turns north, so it sits mid-strip instead of hugging the array --
# there is room for it now that the array has moved west.
_DC_GND_RAIL_END_STRAIGHT = 20.0

# End-straight (um) on the head-ground bundle, which lands on the top pad's north
# face. The terminals sit at or below that face, so the lanes have to come back
# down onto it; without a forced approach the planner needs legs shorter than its
# minimum and gives up ("no candidate-line corner satisfies the minimum-leg
# floors"). 300 is what a four-lane bundle needs to clear that on both two-head
# dies -- 150 is enough for R3A but leaves R3B unroutable. ``fan_in`` / ``fan_out``
# do route R3A but never rescue R3B, and cost ~60% more elements where they work.
_DC_GND_HEAD_END_STRAIGHT = 300.0

# Pads 0..3 carry the modulator head's four independent bias lines; every pad
# above them is strapped together as the common ground land.
_NUM_BIAS_PADS = 4


# Physical face -> outward port orientation (deg). Names are the *physical*
# directions, which is why they are resolved by angle: see the module docstring
# on the rotation=90 port-naming quirk.
_FACE_ORIENTATION = {"east": 0.0, "north": 90.0, "west": 180.0, "south": 270.0}


def dc_pad_count(cell: fw.Component, pad_array: str = _PAD_ARRAY) -> int:
    """Number of pads in ``pad_array`` (counted by their west faces)."""
    pads = cell.instances[pad_array]
    return sum(
        1 for name in pads.ports if abs(pads.ports[name].orientation - 180.0) < 1e-6
    )


def _require_vertical_stack(cell: fw.Component, pad_array: str = _PAD_ARRAY) -> None:
    """Raise unless ``pad_array`` is a vertical (``rotation=90``) pad stack.

    The bottom-up pad numbering and the north/south ground straps both assume the
    pads are stacked in y at a common x. R1A places its array with
    ``bondpad_rotation=0``, i.e. a horizontal row -- numbering and straps would
    both be wrong there, so fail loudly instead of mis-routing.
    """
    pads = cell.instances[pad_array]
    xs = [
        pads.ports[name].position[0]
        for name in pads.ports
        if abs(pads.ports[name].orientation - 180.0) < 1e-6
    ]
    if len(xs) > 1 and max(xs) - min(xs) > 1e-6:
        raise ValueError(
            f"{pad_array!r} is a horizontal pad row (west faces span "
            f"x={min(xs):.1f}..{max(xs):.1f}), but the DC scheme assumes a vertical "
            "stack (bottom-up numbering, north/south straps). Dies placed with "
            "bondpad_rotation=0 (R1A) need the horizontal variant."
        )


def dc_pad_port(
    cell: fw.Component,
    index: int,
    face: str = "west",
    pad_array: str = _PAD_ARRAY,
) -> PortSpec:
    """``(instance, port)`` for one physical ``face`` of DC bond pad ``index``.

    Pads are numbered from the bottom of the array up: ``index=0`` is the
    bottom-most pad. Selection is by port orientation, so it is immune to the
    array-rotation port-naming quirk described in the module docstring.

    Args:
        cell: die cell carrying the bond-pad array.
        index: pad number, 0 = bottom-most.
        face: which physical pad edge to land on -- ``"west"`` (default, the
            face looking back into the die) / ``"north"`` / ``"east"`` /
            ``"south"``. The N/S faces are what the pad-to-pad ground straps
            use, so they stay off the west faces the bias lines land on.
        pad_array: instance name of the bond-pad array.

    Raises:
        KeyError: if ``face`` is not one of the four cardinal names.
        IndexError: if ``index`` is past the last pad in the array.
    """
    orientation = _FACE_ORIENTATION[face]
    pads = cell.instances[pad_array]
    matches = [
        (pads.ports[name].position[1], name)
        for name in sorted(pads.ports)
        if abs(pads.ports[name].orientation - orientation) < 1e-6
    ]
    matches.sort()  # bottom-up
    if not 0 <= index < len(matches):
        raise IndexError(
            f"DC pad {index} out of range: {pad_array!r} exposes "
            f"{len(matches)} pads with a {face} face"
        )
    return (pad_array, matches[index][1])


def add_dc_pad_routes(cell: fw.Component, second_head: str | None = None) -> None:
    """Route a die's ``test_modulator_head`` DC bias lines to its bond pads.

    Applies uniformly to every die whose pad array is a **vertical stack**
    (``bondpad_rotation=90``, the default) -- R1B, R2A, R2B, R3A, R3B, R4A, R4B.
    R1A's horizontal row is rejected by :func:`_require_vertical_stack`; it needs
    its own variant.

    The **primary** ``test_modulator_head`` gets the full four-line bias map.
    ``second_head`` names a die's second head (R3A/R3B: ``test_modulator_head_2``)
    and grounds *just* its two east bias terminals onto the same top pad -- its
    four independent bias lines are still to do, as is R1A/R1B's mirrored
    ``test_modulator_head_top2``.

    Args:
        cell: die cell carrying ``test_modulator_head`` and the pad array.
        second_head: instance name of a second modulator head whose two
            east-facing bias terminals join the common ground. ``None`` (default)
            wires the primary head only.

    Lines, each landing on its pad's west face:

    - **pad 0** (bottom-most) <- the tunable coupler's **west-most** terminal on
      ``test_modulator_head`` (``e_coupler_1``, the split-ratio heater).
    - **pad 1** <- the same coupler heater's **east / signal** terminal
      (``e_coupler_2``), the driven side of that heater.
    - **pads 2 + 3** <- the two **west-facing** bias terminals
      (``e_phase2_1`` -> pad 2, ``e_phase_1`` -> pad 3) as a **single autoroute
      call** (one 2-lane bundle). Paired lower-source-to-lower-pad so the two
      lanes don't cross.
    - **top-most pad** <- the modulator head's **two east-most** terminals
      (``e_phase_2`` + ``e_phase2_2``, the outer ends of the two TOPS phase
      shifters), tied together as a **common ground**.
    - **every pad above the bias four** is strapped into that ground, so the
      ground land scales with the array: pads 4/5/6 on the 7-pad dies, 4/5/6/7 on
      R3A's 8-pad array.
    - **top-most pad** also <- ``second_head``'s two east bias terminals, when a
      second head is given (R3A/R3B).

    Each line is its **own explicit** ``autoroute`` call (deliberately not
    looped) so per-call knobs -- ``strategy``, ``start_straight`` /
    ``end_straight``, ``bbox_margin``, ``bundle_keepout_factor``, ``fan_in`` /
    ``fan_out``, obstacle sources -- can be tuned line by line without touching
    the others. ``_DC_SPEC`` / ``_DC_STRATEGY`` are the shared defaults; override
    them inline on any single call.

    ``avoid_port_owners=False`` throughout: DC metal is allowed to run over the
    cells it wires, since the terminals sit inside dense optical blocks with no
    clear lane out.
    """
    _require_vertical_stack(cell)
    head = "test_modulator_head"
    # Bias pads: 0-3 for the primary head. A second head adds its two west bias
    # terminals on pads 4-5, pushing the ground land up by two. Everything above
    # the bias pads is strapped together as ground, with the top-most pad the
    # landing for the heads' east ground terminals.
    num_bias_pads = _NUM_BIAS_PADS + (2 if second_head is not None else 0)
    num_pads = dc_pad_count(cell)
    gnd_pads = list(range(num_bias_pads, num_pads))
    gnd_top = num_pads - 1

    # Tunable-coupler heater, west-most terminal -> pad 0 (bottom-most).
    cell.autoroute(
        ports_a=[(head, "e_coupler_1")],
        ports_b=[dc_pad_port(cell, 0)],
        spec=_DC_SPEC,
        strategy=_DC_STRATEGY,
        avoid_port_owners=False,
        name="dc_bias_head_coupler",
    )

    # Same coupler heater, east / signal terminal -> pad 1.
    cell.autoroute(
        ports_a=[(head, "e_coupler_2")],
        ports_b=[dc_pad_port(cell, 1)],
        spec=_DC_SPEC,
        strategy=_DC_STRATEGY,
        avoid_port_owners=False,
        name="dc_bias_head_coupler_signal",
        end_straight=850.0
    )

    # West-facing bias terminals, one bundle. Primary head -> pads 2/3 (paired
    # lower-source-to-lower-pad). With a second head its two west bias terminals
    # join the same bundle on pads 4/5 -- note the second head sits *below* the
    # primary while pads 4/5 sit *above* pads 2/3, so those two pairs run as
    # groups that swap order; the planner sorts the lanes out inside the bundle.
    phase_west: list[tuple[tuple[str, str], int]] = [
        ((head, "e_phase2_1"), 2),  # lower source -> lower pad
        ((head, "e_phase_1"), 3),  # upper source -> upper pad
    ]
    if second_head is not None:
        phase_west += [
            ((second_head, "e_phase2_1"), 4),
            ((second_head, "e_phase_1"), 5),
        ]
    cell.autoroute(
        ports_a=[port for port, _ in phase_west],
        ports_b=[dc_pad_port(cell, pad) for _, pad in phase_west],
        spec=_DC_SPEC,
        strategy=_DC_STRATEGY,
        avoid_port_owners=False,
        name="dc_bias_head_phase_west",
    )

    # Common ground: every head's two outer (east) TOPS terminals tied onto the
    # top-most pad, as one bundle -- two lanes on a single-head die, four when a
    # second head is given. They all share the same outward heading (east) and the
    # same destination, which is what a bundle wants.
    #
    # They land on the pad's **north** face, not its west one. West puts four
    # lanes on a single 120 um face, which the planner resolves by doubling back
    # over the pad array. North is the top pad's one free face -- the strap below
    # it uses its south, the rail its east -- and the space above the array is
    # open. Only the top pad has a free north face; every other pad keeps the
    # west-face convention.
    gnd_terminals = [(head, "e_phase_2"), (head, "e_phase2_2")]
    end_straight = 0.0
    if second_head is not None:
        gnd_terminals += [(second_head, "e_phase_2"), (second_head, "e_phase2_2")]
        end_straight = _DC_GND_HEAD_END_STRAIGHT
    cell.autoroute(
        ports_a=gnd_terminals,
        ports_b=[dc_pad_port(cell, gnd_top, "north")] * len(gnd_terminals),
        spec=_DC_SPEC,
        strategy=_DC_STRATEGY,
        avoid_port_owners=False,
        end_straight=end_straight,
        name="dc_gnd_head_tops",
    )

    # Ground strap: every otherwise-unused pad chained up into the top-pad ground
    # (4 -> 5 -> 6 [-> 7 on R3A]), so the top pads form one contiguous ground land
    # and a wirebond can go down on any of them.
    #
    # This has to be its own autoroute call: a bundle requires every lane to
    # share an outward heading, and the head's ground terminals above face east
    # (0°) while these pad-to-pad straps face north (90°). All strap lanes do
    # share 90°, so they ride together here. The straps use the pads' north/south
    # faces -- the shortest hop between stacked neighbours, and it leaves every
    # west face free for the bias lines.
    if len(gnd_pads) > 1:
        cell.autoroute(
            ports_a=[dc_pad_port(cell, i, "north") for i in gnd_pads[:-1]],
            ports_b=[dc_pad_port(cell, i + 1, "south") for i in gnd_pads[:-1]],
            spec=_DC_SPEC,
            strategy=_DC_STRATEGY,
            avoid_port_owners=False,
            name="dc_gnd_pad_strap",
        )

    add_dc_gnd_rail(cell)
    add_dc_pad_labels(cell, second_head=second_head is not None)


def add_dc_gnd_rail(cell: fw.Component, pad_array: str = _PAD_ARRAY) -> None:
    """Tie the array's two extreme pads together as one shared ground.

    A single line from the **bottom-most** pad to the **top-most**, landing on
    both **east** faces so it runs up the strip between the array and the die
    edge -- the one lane with nothing in it, now that the labels stand west
    (:func:`add_dc_pad_labels`) and every bias line lands on a west face. The
    strap in :func:`add_dc_pad_routes` already chains the upper pads through
    their north/south faces; this rail extends that net to the bottom of the
    stack, so the tunable coupler's ground end (pad 0) shares the ground land
    rather than needing its own wirebond.

    A no-op on an array of fewer than two pads.
    """
    num_pads = dc_pad_count(cell, pad_array)
    if num_pads < 2:
        return
    cell.autoroute(
        ports_a=[dc_pad_port(cell, 0, "east", pad_array)],
        ports_b=[dc_pad_port(cell, num_pads - 1, "east", pad_array)],
        spec=_DC_SPEC,
        strategy=_DC_STRATEGY,
        avoid_port_owners=False,
        end_straight=_DC_GND_RAIL_END_STRAIGHT,
        name="dc_gnd_pad_rail",
    )


def dc_pad_label_texts(num_pads: int, second_head: bool = False) -> dict[int, str]:
    """Label text per DC bond-pad index, from the same map :func:`add_dc_pad_routes` wires.

    Indices are bottom-up, as everywhere else in this module. Naming follows the
    layout's ``DEVICE-POSITION-FUNCTION`` convention:

    ==================  ==============  ==========================================
    Pad                 Label           Terminal
    ==================  ==============  ==========================================
    ``0``               TC-GND          ``e_coupler_1`` -- tunable-coupler heater,
                                        the undriven (ground) end
    ``1``               TC-SIG          ``e_coupler_2`` -- same heater, driven end
    ``2``               BIAS-SIG-1      ``e_phase2_1`` -- upper TOPS phase shifter
    ``3``               BIAS-SIG-2      ``e_phase_1``  -- lower TOPS phase shifter
    ``4`` / ``5``       BIAS2-SIG-1/2   the second head's two west bias terminals
                                        (R3A/R3B only, when ``second_head``)
    rest                BIAS-GND        the strapped common-ground land, which the
                                        heads' outer TOPS terminals land on
    ==================  ==============  ==========================================

    Every pad in the ground land carries the same text because they are the same
    net -- strapped together by ``dc_gnd_pad_strap`` -- so a wirebond may go down
    on any of them.
    """
    num_bias = _NUM_BIAS_PADS + (2 if second_head else 0)
    texts = {0: "TC-GND", 1: "TC-SIG", 2: "BIAS-SIG-1", 3: "BIAS-SIG-2"}
    if second_head:
        texts[4] = "BIAS2-SIG-1"
        texts[5] = "BIAS2-SIG-2"
    texts.update({i: "BIAS-GND" for i in range(num_bias, num_pads)})
    return {i: t for i, t in texts.items() if 0 <= i < num_pads}


def add_dc_pad_labels(cell: fw.Component, second_head: bool = False) -> None:
    """Name every DC bond pad, reading horizontally west of the array.

    One horizontal label per pad, its east edge ``_DC_PAD_LABEL_GAP`` west of
    that pad's west face and standing on the pad's bottom edge. West rather than
    east because the strip east of the array is now the shared-ground rail's lane
    (:func:`add_dc_gnd_rail`). Texts come from :func:`dc_pad_label_texts`.

    The west faces are also where every bias line lands, so a pad's own line
    crosses its label on the way in -- unavoidable here, and harmless: the line
    is TOP_METAL and the label is an LN etch beneath it, the same stacking this
    module already relies on with ``avoid_port_owners=False``.

    Called at the end of :func:`add_dc_pad_routes`, so the labels cannot drift out
    of step with the wiring they describe.
    """
    for i, text in dc_pad_label_texts(dc_pad_count(cell), second_head).items():
        pad_inst, pad_port = dc_pad_port(cell, i, "west")
        west_x = cell.instances[pad_inst].ports[pad_port].position[0]
        south_inst, south_port = dc_pad_port(cell, i, "south")
        pad_bottom = cell.instances[south_inst].ports[south_port].position[1]
        add_horizontal_label(
            cell,
            text,
            x_ref=west_x,
            y_bottom=pad_bottom,
            side="west",
            gap=_DC_PAD_LABEL_GAP,
            height=DC_PAD_LABEL_HEIGHT,
            name=f"label_dc_pad_{i}",
        )
