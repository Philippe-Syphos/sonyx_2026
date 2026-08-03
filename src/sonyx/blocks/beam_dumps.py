"""Beam-dump termination for the layout's open 2x2-coupler ports.

Several blocks drive only **one** of a 2x2 coupler's two west inputs -- the MZM
circuits' input stage (:mod:`.dies._head_coupler_block`) and the R4A
coupling-length sweeps (:mod:`.dc_length_sweep`, :mod:`.dc_mzi_length_sweep`) --
so the other input ends in a bare facet that reflects straight back down the
chain. This module terminates those ports with the PDK
``beam_dump_rib_sm_800nm`` and, crucially, gets the **mirroring** right.

The dump is asymmetric: its spiral (plus moat and ``BOT_METAL`` contour) reaches
~72 um out on one side of the waveguide it terminates and only ~10 um on the
other. The two west inputs of a 2x2 are just 21.3 um apart, so the wrong
handedness swallows the *fed* input's waveguide. :func:`add_open_port_beam_dump`
picks the handedness that leans the body away from a named reference port;
:func:`add_2x2_input_beam_dumps` applies that to whichever of ``o1`` / ``o2`` a
block left unrouted, read off the cell's nets.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

import picasso as fw
from luqia_ln200 import pdk

# Offset (deg) from an open port's own orientation to the direction the
# un-mirrored dump's body extends in. The PDK dump's ``o1`` faces 270 deg in its
# own frame with the spiral toward local +x, and ``put`` turns it so ``o1`` faces
# *back* along the port it mates to (port + 180) -- which leaves the body 90 deg
# CCW of that, i.e. port + 270. ``mirror=True`` flips it to port + 90, the other
# side of the incoming waveguide.
_DUMP_BODY_OFFSET_DEG = 270.0

# The two west inputs of a 2x2 coupler / modulator head, in port-name order.
_2X2_INPUTS = ("o1", "o2")


def add_open_port_beam_dump(
    cell: fw.Component,
    inst_name: str,
    open_port: str,
    *,
    away_from: str,
    name: str,
) -> str:
    """Terminate ``(inst_name, open_port)`` with a PDK beam dump, mirrored away.

    Mirroring is chosen so the dump's body extends to the side of the terminated
    waveguide **opposite** ``(inst_name, away_from)``: the un-mirrored body
    heading is the open port's orientation plus :data:`_DUMP_BODY_OFFSET_DEG`,
    and the dump is mirrored whenever that heading has a positive component along
    the vector to the reference port. Deriving it from the two ports' geometry
    rather than hard-coding a handedness keeps it correct for either open port of
    a 2x2 and for any port orientation.

    Args:
        cell: cell owning ``inst_name`` (extended in place).
        inst_name: instance whose port is being terminated.
        open_port: the unfed port on that instance.
        away_from: port on the same instance the dump body must lean away from --
            in practice the sibling input that *is* fed.
        name: instance name for the dump.

    Returns:
        ``name``, so callers can collect what they placed.
    """
    inst = cell.instances[inst_name]
    port = inst.ports[open_port]
    body = math.radians(port.orientation + _DUMP_BODY_OFFSET_DEG)
    ref = inst.ports[away_from].position
    dx = ref[0] - port.position[0]
    dy = ref[1] - port.position[1]
    cell.put(
        pdk.cells["beam_dump_rib_sm_800nm"](),
        (inst_name, open_port),
        port_to="o1",
        name=name,
        mirror=math.cos(body) * dx + math.sin(body) * dy > 0.0,
    )
    return name


def add_2x2_input_beam_dumps(
    cell: fw.Component, inst_names: Iterable[str], *, prefix: str = "beamdump"
) -> list[str]:
    """Dump every unfed west input of the named 2x2 couplers / modulator heads.

    Which of ``o1`` / ``o2`` a block leaves spare is not fixed -- the MZM input
    stage feeds ``o1`` on most dies but ``o2`` on R3A's lower head, and the R4A
    sweeps feed ``o2`` throughout -- so rather than being told, the spare port is
    read off ``cell.nets``: a port carrying no net and no external port mapping is
    open. Each is dumped away from its sibling via
    :func:`add_open_port_beam_dump`, as instance ``{prefix}_{inst}_{port}``.

    **Call this after the block's input routing**, or it will dump ports that are
    about to be fed. Names in ``inst_names`` that are absent from ``cell`` are
    skipped, so a caller can pass the full roster of a family of blocks.

    Returns:
        The instance names of the dumps placed, in the order they were added.
    """
    connected = {
        (ref.instance_name, ref.port_name)
        for net in cell.nets
        for ref in (net.port_a, net.port_b)
    }
    connected |= {(pm.instance_name, pm.port_name) for pm in cell.port_mappings}
    placed: list[str] = []
    for inst_name in inst_names:
        if inst_name not in cell.instances:
            continue
        for port, sibling in (_2X2_INPUTS, _2X2_INPUTS[::-1]):
            if (inst_name, port) in connected:
                continue
            placed.append(
                add_open_port_beam_dump(
                    cell, inst_name, port,
                    away_from=sibling,
                    name=f"{prefix}_{inst_name}_{port}",
                )
            )
    return placed
