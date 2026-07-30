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


def dc_pad_port(cell: fw.Component, index: int, pad_array: str = _PAD_ARRAY) -> PortSpec:
    """``(instance, port)`` for the **west** face of DC bond pad ``index``.

    Pads are numbered from the bottom of the array up: ``index=0`` is the
    bottom-most pad. Selection is by port orientation (180° = facing west), so
    it is immune to the array-rotation port-naming quirk described in the module
    docstring.

    Args:
        cell: die cell carrying the bond-pad array.
        index: pad number, 0 = bottom-most.
        pad_array: instance name of the bond-pad array.

    Raises:
        IndexError: if ``index`` is past the last pad in the array.
    """
    pads = cell.instances[pad_array]
    west = [
        (pads.ports[name].position[1], name)
        for name in sorted(pads.ports)
        if abs(pads.ports[name].orientation - 180.0) < 1e-6
    ]
    west.sort()  # bottom-up
    if not 0 <= index < len(west):
        raise IndexError(
            f"DC pad {index} out of range: {pad_array!r} exposes {len(west)} west-facing pads"
        )
    return (pad_array, west[index][1])


def add_dc_pad_routes(cell: fw.Component) -> None:
    """Route R4A's DC bias lines from on-die terminals to the bond pads.

    Lines, each landing on its pad's west face:

    - **pad 0** (bottom-most) <- the tunable coupler's **west-most** terminal on
      ``test_modulator_head`` (``e_coupler_1``, the split-ratio heater).
    - **pad 1** <- the same coupler heater's **east / signal** terminal
      (``e_coupler_2``), the driven side of that heater.
    - **pad 6** (top-most) <- the modulator head's **two east-most** terminals
      (``e_phase_2`` + ``e_phase2_2``, the outer ends of the two TOPS phase
      shifters), tied together as a **common ground**.

    Placement is additive -- one named route instance per bias line, so lines
    can be added one at a time as the pad map fills in. A line may carry several
    source ports, which then share one pad (a common node).
    """
    # (source ports, pad index, route name)
    lines: list[tuple[list[tuple[str, str]], int, str]] = [
        ([("test_modulator_head", "e_coupler_1")], 0, "dc_bias_head_coupler"),
        ([("test_modulator_head", "e_coupler_2")], 1, "dc_bias_head_coupler_signal"),
        # Common ground: both TOPS outer terminals onto one pad.
        (
            [("test_modulator_head", "e_phase_2"), ("test_modulator_head", "e_phase2_2")],
            6,
            "dc_gnd_head_tops",
        ),
    ]
    for src_ports, pad_index, route_name in lines:
        pad = dc_pad_port(cell, pad_index)
        cell.autoroute(
            ports_a=list(src_ports),
            ports_b=[pad] * len(src_ports),
            spec=_DC_SPEC,
            strategy=_DC_STRATEGY,
            # DC metal is allowed to run over the cells it wires -- the terminals
            # sit inside dense optical blocks and there is no lane out otherwise.
            avoid_port_owners=False,
            name=route_name,
        )
