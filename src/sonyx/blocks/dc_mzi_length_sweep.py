"""Back-to-back-coupler MZI coupling-length test (R4A).

Same coupling-length sweeps and two-group layout as
:mod:`sonyx.blocks.dc_length_sweep`, but each DUT is a **zero-arm-length MZI**:
two directional couplers of length ``L`` connected back to back (DC1's outputs
feed DC2's inputs with no arm straight between them). Cascading two identical
couplers gives a bar/cross transfer that probes the coupler design more sharply
than a single DC (and, as a balanced MZI, is less sensitive to the input/output
coupling loss). Per DUT three ports are connected -- ``o2`` (input, upper west),
``o3`` (bar, upper east) and ``o4`` (cross, lower east) -- and ``o1`` is left open.

Two stacked tiers, matching the single-DC block: the 50/50 sweep on top and the
5/95-tap sweep (centred on the 94.38 um nominal) below it. This is **sweep block
1** -- placed on R4A east of the single-DC block at a whole number of grating
pitches (``block_x_base(1)``), so the two blocks' couplers form one continuous
pitch grid rather than two independently-positioned islands. Uses the shared group
placer/router from :mod:`sonyx.blocks.dc_length_sweep` (with ``bb_``/``tap_bb_``
instance-name prefixes so all sweeps coexist on one die). Fully routed -- inputs and
outputs, two bundles per group.
"""

from __future__ import annotations

import picasso as fw
from picasso.recipe import recipe

from ..parameters import parameters as _p
from .dc_length_sweep import (
    _LENGTHS_5050,
    _LENGTHS_TAP,
    _TIER_DROP,
    _TOP_MARGIN,
    _dc_dut,
    _tap_dc_dut,
    block_x_base,
    place_two_groups,
    route_two_groups,
)


@recipe
def _bb_dc_mzi(coupling_length: float, tap: bool = False) -> fw.Component:
    """Zero-arm-length MZI: two length-``L`` directional couplers, back to back.

    DC1's outputs abut DC2's inputs directly (upper o3->o2, lower o4->o1), a
    balanced (dL=0) MZI. Each half is the PDK DC cell for the tier's split
    ratio (``tap`` selects 5/95 over 50/50) at the swept ``coupling_length``.
    Ports: ``o1``/``o2`` (DC1 inputs, west), ``o3``/``o4`` (DC2 outputs, east).
    """
    dut = _tap_dc_dut if tap else _dc_dut
    cell = fw.Component()
    d1 = cell.add_placed(dut(coupling_length), name="dc1")
    d2 = cell.put(dut(coupling_length), (d1.name, "o3"), port_to="o2", name="dc2")
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


def _bb_tap_dc_mzi(coupling_length: float) -> fw.Component:
    """The 5/95-tap tier's zero-arm MZI (a ``dut_factory`` for the tap tier)."""
    return _bb_dc_mzi(coupling_length, tap=True)


def add_dc_mzi_length_sweep(cell: fw.Component) -> None:
    """Place the back-to-back-MZI sweep on R4A -- 50/50 tier + 5/95 tier.

    Sweep block ``1`` -- east of the single-DC block on the shared grating grid
    (``block_x_base(1)``) -- two stacked tiers (50/50 on top, 5/95 tap ``_TIER_DROP``
    below), each two side-by-side groups of four zero-arm MZIs. Instances
    ``bb_dc_*`` (50/50) and ``tap_bb_dc_*`` (5/95). Both groups of both tiers are
    fully routed by :func:`route_two_groups` (inputs and outputs).
    """
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    x_base = block_x_base(1)
    y1 = (half_h - kw) - _TOP_MARGIN
    place_two_groups(
        cell, lengths=_LENGTHS_5050, x_base=x_base, y_top=y1,
        dut_factory=_bb_dc_mzi, gc_prefix="bb_dc_gc", dut_prefix="bb_dc_len",
    )
    place_two_groups(
        cell, lengths=_LENGTHS_TAP, x_base=x_base, y_top=y1 - _TIER_DROP,
        dut_factory=_bb_tap_dc_mzi, gc_prefix="tap_bb_dc_gc", dut_prefix="tap_bb_dc_len",
    )
    # Routing pass: per group, the four west couplers -> the MZI inputs, then the MZI
    # outputs -> the eight remaining couplers.
    route_two_groups(cell, lengths=_LENGTHS_5050, gc_prefix="bb_dc_gc", dut_prefix="bb_dc_len")
    route_two_groups(
        cell, lengths=_LENGTHS_TAP, gc_prefix="tap_bb_dc_gc", dut_prefix="tap_bb_dc_len"
    )
