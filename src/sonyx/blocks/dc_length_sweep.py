"""Directional-coupler coupling-length test (R4A) -- placement-only pass.

Directional couplers with a swept parallel coupling length ``L`` map the
bar/cross power split ``cos^2(kappa L)`` / ``sin^2(kappa L)``, so fitting the
measured split vs. L extracts the coupling coefficient / beat length and
calibrates the coupler design. Two tiers are placed: a sweep around the 50/50
point (L = 75.47 um nominal) on top and a sweep around the 5/95-tap point
(L = 94.38 um nominal, its nominal included) below it.

Per DUT the intended wiring connects **three** ports to grating couplers --
``o1`` (input), ``o4`` (bar output), ``o3`` (cross output) -- and leaves ``o2``
(the second, unused input) **open**. The eight DCs are split into **two groups
of four**, each with its own N-S grating-coupler array
(``gratingcoupler_rib_sm_800nm_ext``, three couplers per DC) + left alignment
loop, placed side by side. The PDK ships only fixed-length DCs (50/50, 5/95), so
the length sweep calls ``make_directional_coupler`` directly.

This pass **places the DCs + GC array only** (no routing), consistent with the
other R4x test blocks; the o1/o3/o4 -> coupler routing (and o2 left open) is a
follow-up.
"""

from __future__ import annotations

from collections.abc import Callable

import picasso as fw
from luqia_ln200.cells.bends import sbend_rib_sm_800nm
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from picasso.leaves import make_array, make_directional_coupler
from picasso.recipe import recipe

from ..parameters import parameters as _p

# Swept parallel coupling lengths (um). Two sweeps, one per tap ratio, each
# centred on the PDK nominal for that coupler:
#   50/50 -> nominal L = 75.47 um; 5/95 tap -> nominal L = 94.38 um.
# The tap sweep includes its nominal (94.38) and brackets it.
_LENGTHS_5050: tuple[float, ...] = (10.0, 30.0, 55.0, 75.0, 95.0, 120.0, 150.0, 190.0)
_LENGTHS_TAP: tuple[float, ...] = (45.0, 65.0, 80.0, 94.38, 108.0, 125.0, 155.0, 195.0)
_DC_GAP = 0.8  # edge-to-edge coupler gap (um), the PDK design point

# One input + two output couplers per DC (o1 / o4 / o3); o2 left open.
_GC_PER_DC = 3
# The 8 DCs split into two side-by-side groups of this many.
_PER_GROUP = 4

# Layout (um). Each group: GC array north (left loop + couplers) with its 4 DCs
# stacked below, input (o1) left-aligned to the group's left edge.
_LEFT_MARGIN = 250.0  # first group's left edge off the left inner edge
_TOP_MARGIN = 40.0  # coupler/loop tops below the top inner edge
_GC_TO_DC_GAP = 120.0  # GC array bottom down to the top DC
_DC_ROW_PITCH = 120.0  # vertical centre-to-centre of stacked DCs
_GROUP_GAP = 200.0  # horizontal gap between the two groups' GC arrays
_TIER_DROP = 750.0  # vertical drop from the 50/50 tier to the 5/95 tier below it


@recipe
def _dc_dut(coupling_length: float) -> fw.Component:
    """A directional coupler of the given coupling length; ports ``o1``-``o4``."""
    inner = make_directional_coupler(
        coupling_length=coupling_length,
        gap=_DC_GAP,
        cross_section="rib_sm_800nm",
        sbend_cell=sbend_rib_sm_800nm(),
        name=f"_dc_len_inner_{coupling_length:g}um",
    )
    cell = fw.Component()
    di = cell.add_placed(inner, "dc")
    for k in ("o1", "o2", "o3", "o4"):
        cell.add_port(k, (di.name, k))
    cell.cell_type = "directional_coupler"
    cell.description = (
        f"Directional coupler on the 800 nm SM rib (L={coupling_length:g} um, "
        f"gap={_DC_GAP:g} um) -- coupling-length test DUT."
    )
    cell.calibration_status = "PLACEHOLDER"
    cell.parameters.band = "800nm"
    cell.parameters.axis = "ord"
    cell.parameters.coupling_length_um = coupling_length
    cell.parameters.gap_um = _DC_GAP
    return cell


@recipe
def _gc_line(num: int) -> fw.Component:
    """A row of ``num`` N-S grating couplers at ``grating_coupling_pitch_for_tests``."""
    return make_array(
        template=gratingcoupler_rib_sm_800nm_ext(),
        rows=1,
        cols=num,
        dx=_p.grating_coupling_pitch_for_tests.value,
        dy=0.0,
    )


def group_gc_width() -> float:
    """Horizontal extent (um) of a group's GC array (loop + pitch gap + couplers)."""
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    lb = gratingcoupler_alignment_rib_sm_800nm_ext().bbox
    return lb.dx + (pitch - gc_w) + _gc_line(_GC_PER_DC * _PER_GROUP).bbox.dx


def _add_group(
    cell: fw.Component, x_left: float, y_top: float, y0: float,
    lengths: tuple[float, ...], tag: str, *,
    dut_factory: Callable[[float], fw.Component] = _dc_dut,
    gc_prefix: str = "dc_gc", dut_prefix: str = "dc_len",
) -> None:
    """Place one group: GC array + left alignment loop (north) and its DUTs below.

    The alignment loop's left edge sits at ``x_left``; couplers/loop tops at
    ``y_top``. Each DUT (from ``dut_factory``, a coupling-length -> Component) is
    centred horizontally on its GC array and stacked downward from ``y0``.
    Instances ``{gc_prefix}_align_{tag}`` / ``{gc_prefix}_array_{tag}`` /
    ``{dut_prefix}_{L}`` -- prefixes keep sibling sweeps on one die distinct.
    """
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(loop, f"{gc_prefix}_align_{tag}", x=x_left - lb.xmin, y=y_top - lb.ymax)
    arr = _gc_line(_GC_PER_DC * len(lengths))
    ab = arr.bbox
    array_x = (x_left + lb.dx) + (pitch - gc_w) - ab.xmin  # placement offset
    cell.add_placed(arr, f"{gc_prefix}_array_{tag}", x=array_x, y=y_top - ab.ymax)
    array_center_x = array_x + ab.center_x  # GC array horizontal centre
    for i, length in enumerate(lengths):
        dut = dut_factory(length)
        o1 = dut.ports["o1"].position
        b = dut.bbox
        cell.add_placed(
            dut, f"{dut_prefix}_{length:g}",
            x=array_center_x - b.center_x, y=(y0 - i * _DC_ROW_PITCH) - o1[1],
        )


def place_two_groups(
    cell: fw.Component, *, lengths: tuple[float, ...], x_base: float, y_top: float,
    dut_factory: Callable[[float], fw.Component] = _dc_dut,
    gc_prefix: str = "dc_gc", dut_prefix: str = "dc_len",
) -> None:
    """Place a length sweep as two side-by-side groups anchored at (x_base, y_top).

    Splits ``lengths`` into two groups of ``_PER_GROUP`` (first half / second
    half), each a GC array + left alignment loop with its DUTs centred below; the
    second group is offset right by the GC-array width + ``_GROUP_GAP``. Shared by
    the 50/50 and 5/95-tap tiers and by the single-DC and back-to-back-MZI blocks.
    """
    lb = gratingcoupler_alignment_rib_sm_800nm_ext().bbox
    y0 = (y_top - lb.dy) - _GC_TO_DC_GAP  # top DUT below the (tallest) alignment loop
    group_width = group_gc_width()
    groups = ((lengths[:_PER_GROUP], "a"), (lengths[_PER_GROUP:], "b"))
    for g, (lens, tag) in enumerate(groups):
        x_left = x_base + g * (group_width + _GROUP_GAP)
        _add_group(
            cell, x_left, y_top, y0, lens, tag,
            dut_factory=dut_factory, gc_prefix=gc_prefix, dut_prefix=dut_prefix,
        )


def add_dc_length_sweep(cell: fw.Component) -> None:
    """Place the single-DC coupling-length sweep on R4A -- 50/50 tier + 5/95 tier.

    Two stacked tiers, each two side-by-side groups of four: the 50/50 sweep
    (``_LENGTHS_5050``) at the top, and the 5/95-tap sweep (``_LENGTHS_TAP``,
    centred on the 94.38 um nominal) ``_TIER_DROP`` below it. Instances
    ``dc_*`` (50/50) and ``tap_dc_*`` (5/95). Placement-only (o2 open; not routed).
    """
    half_w = _p.die_width.value / 2.0
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    x_base = (-half_w + kw) + _LEFT_MARGIN
    y1 = (half_h - kw) - _TOP_MARGIN
    place_two_groups(cell, lengths=_LENGTHS_5050, x_base=x_base, y_top=y1)
    place_two_groups(
        cell, lengths=_LENGTHS_TAP, x_base=x_base, y_top=y1 - _TIER_DROP,
        gc_prefix="tap_dc_gc", dut_prefix="tap_dc_len",
    )
