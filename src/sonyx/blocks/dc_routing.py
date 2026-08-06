"""DC bias routing on TOP_METAL — die bond pads to on-die DC terminals.

Wires each die's lower-right DC bond-pad block to the thermo-optic / DC
terminals on the modulator head(s), on the PDK ``routing_top_metal`` routing
spec (20 µm AlCu trace, flush Manhattan L-bends). All the DC terminals we
target already present their ports on ``routing_top_metal``, so no
cross-section transition is needed.

**Pad block.** The lower-right array is now two staggered columns of pads (see
:mod:`sonyx.blocks.bondpads` / :func:`~sonyx.blocks.dies._frame.die_scaffold`):
an **inner** column (``"I"``, west, nearer the circuits) and an **outer**
column (``"O"``, east, at the die edge, raised one pad pitch). Pads are
addressed by :func:`dc_pad_port` as ``(column, row, face)`` — ``row`` counts
from the **bottom** of that column upward, and ``face`` is the physical pad edge
(``"w"``/``"e"``/``"n"``/``"s"``), selected by port orientation so it is immune
to the array's internal port naming.

**Status.** Being rebuilt one ``autoroute`` call at a time against the new
2-column block; :func:`add_dc_pad_routes` currently wires only the calls added
so far.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import picasso as fw
    from picasso.component import PortSpec

# Routing spec for every DC bias line (see luqia_ln200.tech.routing_specs).
_DC_SPEC = "routing_top_metal"
# vgraph_rect is the only planner that gets out of the modulator head's dense
# neighbourhood: grid_astar's approach-lane carve finds the terminals fully
# enclosed by the surrounding geometry at any usable step size.
_DC_STRATEGY = "vgraph_rect"

_PAD_ARRAY = "bondpads"

# Physical pad face -> outward port orientation (deg). Pads are selected by
# angle, so this is immune to the array's internal make_array port naming.
_FACE_ORIENTATION = {"w": 180.0, "e": 0.0, "n": 90.0, "s": 270.0}
# Column label -> index, west (inner) to east (outer).
_COLUMN_INDEX = {"I": 0, "O": 1}


def dc_pad_port(
    cell: fw.Component,
    col: str | int,
    row: int,
    face: str = "w",
    pad_array: str = _PAD_ARRAY,
) -> PortSpec:
    """``(instance, port)`` for one physical ``face`` of a bond pad in the block.

    Args:
        cell: die cell carrying the bond-pad block.
        col: column — ``"I"`` (inner/west) / ``"O"`` (outer/east), or an int
            column index with ``0`` = the westmost column.
        row: pad number within the column, ``0`` = bottom-most, increasing up.
        face: physical pad edge — ``"w"`` (default, looks back into the die) /
            ``"e"`` / ``"n"`` / ``"s"``. Resolved by port orientation.
        pad_array: instance name of the bond-pad block.

    Raises:
        KeyError: if ``face``/``col`` label is not recognised.
        IndexError: if ``col`` or ``row`` is out of range.
    """
    col_index = _COLUMN_INDEX[col] if isinstance(col, str) else col
    orientation = _FACE_ORIENTATION[face]
    pads = cell.instances[pad_array]
    matches = [
        (pads.ports[name].position[0], pads.ports[name].position[1], name)
        for name in pads.ports
        if abs(pads.ports[name].orientation - orientation) < 1e-6
    ]
    column_xs = sorted({round(x, 3) for x, _, _ in matches})
    if not 0 <= col_index < len(column_xs):
        raise IndexError(
            f"column {col!r} out of range: {pad_array!r} has {len(column_xs)} columns"
        )
    col_x = column_xs[col_index]
    column = sorted((y, name) for x, y, name in matches if abs(x - col_x) < 1e-3)
    if not 0 <= row < len(column):
        raise IndexError(
            f"row {row} out of range: column {col!r} of {pad_array!r} has "
            f"{len(column)} pads"
        )
    return (pad_array, column[row][1])


def add_dc_pad_routes(cell: fw.Component, second_head: str | None = None) -> None:
    """Route a die's modulator-head DC terminals to its 2-column bond-pad block.

    Rebuilt incrementally — one ``autoroute`` call per reviewed line. ``avoid_port_owners=False``
    throughout: DC metal is allowed to run over the cells it wires, since the
    terminals sit inside dense optical blocks with no clear lane out.

    Args:
        cell: die cell carrying ``test_modulator_head`` and the pad block.
        second_head: instance name of a die's second modulator head (R3A/R3B:
            ``"test_modulator_head_2"``); ``None`` for the single-head dies.
    """
    head = "test_modulator_head"
    # Heads present on this die, sorted bottom-up by their coupler terminal. The
    # single-head dies are just the length-1 case -- every call below is written
    # over this list so the two-head behaviour collapses automatically.
    heads = [head] + ([second_head] if second_head is not None else [])
    heads = sorted(heads, key=lambda h: cell.instances[h].ports["e_coupler_1"].position[1])

    # Tunable-coupler west (undriven) terminals -> I0 west face, tied together as
    # a common ground: every head's coupler ground lands on the one pad, so a
    # single wirebond on I0 grounds them all. One lane on the single-head dies.
    cell.autoroute(
        ports_a=[(h, "e_coupler_1") for h in heads],
        ports_b=[dc_pad_port(cell, "I", 0, "w")] * len(heads),
        spec=_DC_SPEC,
        strategy=_DC_STRATEGY,
        avoid_port_owners=False,
        name="dc_gnd_coupler1",
    )

    # Tunable-coupler east (driven / signal) terminals -> the inner column from
    # row 1 up, one independent pad each. Lowest head -> I1, next up -> I2, ... so
    # the lanes stay parallel. Collapses to a single lane H1 -> I1 on the
    # single-head dies.
    cell.autoroute(
        ports_a=[(h, "e_coupler_2") for h in heads],
        ports_b=[dc_pad_port(cell, "I", i + 1, "w") for i in range(len(heads))],
        spec=_DC_SPEC,
        strategy=_DC_STRATEGY,
        avoid_port_owners=False,
        end_straight=500.0,
        name="dc_bias_coupler2",
    )

    # Both TOPS phase shifters' west "_1" terminals (e_phase_1 + e_phase2_1),
    # every head, all tied onto I3's west face as one common node. 4 lanes on the
    # two-head dies, 2 lanes on the single-head dies.
    cell.autoroute(
        ports_a=[(h, t) for h in heads for t in ("e_phase_1", "e_phase2_1")],
        ports_b=[dc_pad_port(cell, "I", 3, "w")] * (2 * len(heads)),
        spec=_DC_SPEC,
        strategy=_DC_STRATEGY,
        avoid_port_owners=False,
        name="dc_phase1_common",
    )

    # The two TOPS phase shifters' east "_2" terminals (e_phase_2 + e_phase2_2),
    # every head, each to its own outer-column pad on the pad's EAST face (facing
    # the die edge, reached via the strip east of the array). Sorted bottom-up so
    # the lanes stay parallel: O0 <- lowest terminal, ... up to O3. Collapses to
    # O0/O1 on the single-head dies.
    phase2 = sorted(
        ((h, t) for h in heads for t in ("e_phase_2", "e_phase2_2")),
        key=lambda ht: cell.instances[ht[0]].ports[ht[1]].position[1],
    )
    cell.autoroute(
        ports_a=list(phase2),
        ports_b=[dc_pad_port(cell, "O", row, "e") for row in range(len(phase2))],
        spec=_DC_SPEC,
        strategy=_DC_STRATEGY,
        avoid_port_owners=False,
        name="dc_bias_phase2",
    )
