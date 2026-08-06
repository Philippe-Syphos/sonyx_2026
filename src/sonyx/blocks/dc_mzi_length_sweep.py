"""Back-to-back-coupler MZI coupling-length test (R4A).

Same coupling-length sweep and one-device-per-array grid as
:mod:`sonyx.blocks.dc_length_sweep`, but each DUT is a **zero-arm-length MZI**:
two directional couplers of length ``L`` connected back to back (DC1's outputs
feed DC2's inputs with no arm straight between them). Cascading two identical
couplers gives a bar/cross transfer that probes the coupler design more sharply
than a single DC (and, as a balanced MZI, is less sensitive to the input/output
coupling loss). All four ports front a grating coupler -- ``o1``/``o2`` (DC1
inputs, west) and ``o3``/``o4`` (DC2 outputs, east) -- so there is no beam dump.

This is **sweep block 1** -- placed on R4A east of the single-DC block at a whole
number of grating pitches (``block_x_base(1)``), so the two blocks' couplers form
one continuous pitch grid rather than two independently-positioned islands. Uses
the shared grid placer/router from :mod:`sonyx.blocks.dc_length_sweep` (with
``bb_dc_*`` instance-name prefixes so both blocks coexist on one die). Fully
routed with ``vgraph_rect`` -- the zero-arm MZIs are ~2x wider than a single DC,
so their east ports sit east of the array and reverse westward to their couplers.
"""

from __future__ import annotations

import picasso as fw
from picasso.recipe import recipe

from .dc_length_sweep import (
    _LENGTHS,
    _dc_dut,
    place_grid,
    route_grid,
)


@recipe
def _bb_dc_mzi(coupling_length: float) -> fw.Component:
    """Zero-arm-length MZI: two length-``L`` 50/50 directional couplers, back to back.

    DC1's outputs abut DC2's inputs directly (upper o3->o2, lower o4->o1), a
    balanced (dL=0) MZI. Each half is the PDK 50/50 DC cell at the swept
    ``coupling_length``.
    Ports: ``o1``/``o2`` (DC1 inputs, west), ``o3``/``o4`` (DC2 outputs, east).
    """
    cell = fw.Component()
    d1 = cell.add_placed(_dc_dut(coupling_length), name="dc1")
    d2 = cell.put(_dc_dut(coupling_length), (d1.name, "o3"), port_to="o2", name="dc2")
    cell.connect((d1.name, "o4"), (d2.name, "o1"))
    cell.add_port("o1", (d1.name, "o1"))
    cell.add_port("o2", (d1.name, "o2"))
    cell.add_port("o3", (d2.name, "o3"))
    cell.add_port("o4", (d2.name, "o4"))
    cell.cell_type = "mzi"
    cell.description = (
        f"Zero-arm MZI on the 800 nm SM rib -- two back-to-back directional "
        f"couplers (L={coupling_length:g} um each) -- coupling-length test DUT."
    )
    cell.calibration_status = "PLACEHOLDER"
    cell.parameters.band = "800nm"
    cell.parameters.coupling_length_um = coupling_length
    cell.parameters.num_couplers = 2
    return cell


@recipe
def dc_mzi_length_sweep_block() -> fw.Component:
    """The back-to-back-MZI coupling-length sweep as one self-contained block.

    Local frame: x = 0 on the row 0 / column 0 alignment-loop west edge, y = 0 on
    the GC/loop tops line. The die places this at
    :func:`~sonyx.blocks.dc_length_sweep.block_x_base` (block 1) -- east of
    the single-DC block on the shared grating grid.

    One 50/50 sweep (``_LENGTHS``, 12 lengths) of zero-arm MZIs as a 4-row x
    3-column grid of one-device arrays (:func:`place_grid`): each MZI under its own
    six-coupler array (two alignment + four device), fully routed by
    :func:`route_grid` (``vgraph_rect``) -- no beam dumps, since every port fronts a
    coupler. Instances ``bb_dc_gc_*`` / ``bb_dc_len_*``.
    """
    cell = fw.Component()
    place_grid(
        cell, lengths=_LENGTHS,
        dut_factory=_bb_dc_mzi, gc_prefix="bb_dc_gc", dut_prefix="bb_dc_len",
    )
    route_grid(cell, lengths=_LENGTHS, gc_prefix="bb_dc_gc", dut_prefix="bb_dc_len")
    cell.cell_type = "test_structure"
    cell.description = (
        "Back-to-back-coupler (zero-arm MZI) coupling-length sweep test block: "
        "12 zero-arm 50/50 MZIs, one device per six-coupler array (2 alignment + "
        "4 device) on a 4x3 grid, GC fibre I/O on all four ports, fully wired."
    )
    return cell
