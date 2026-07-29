"""GSG termination-resistance sweep — probeable lumped-terminator DUTs.

A small sweep of :func:`gsg_terminator_top_metal_50ohms_parallel` at a
range of ``target_resistance`` values, each fronted by a GSG probe-pad
launch so its DC resistance is directly measurable on-wafer. Every DUT is
composed *entirely* from existing PDK cells via ``put()`` -- no ad-hoc
geometry:

    gsg_bondpads_top_metal_50ohms (probe triplet, TOP_METAL ``gsg_pads``)
      -> gsg_taper_electrode_to_pads_top_metal_50ohms (pads <-> electrode)
        -> gsg_terminator_top_metal_50ohms_parallel(target_resistance=R)

Land a GSG probe on the pad triplet and read R looking into the
terminator (design value swept). The HEATER sheet resistance is still a
suspected-high placeholder, so the sweep brackets 50 ohm widely to bisect
the true match, and includes the nominal 50 ohm device.

:func:`add_gsg_termination_sweep` stamps the cached DUT recipe cells
straight into the die (no wrapper Component to collide at reticle
assembly), in a single row (7 cells, ascending R) along the die's top-left
edge. Placed only -- the pad triplets are probed directly, nothing is
routed.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.rf import (
    gsg_bondpads_top_metal_50ohms,
    gsg_taper_electrode_to_pads_top_metal_50ohms,
    gsg_terminator_top_metal_50ohms_parallel,
)
from picasso.recipe import recipe

from ..parameters import parameters as _p

# Swept termination resistances (ohm), ascending: option-1 bracket around
# 50 ohm (25..75, 10 ohm steps) plus the nominal 50 ohm device -> 7 DUTs.
_SWEEP_OHMS: tuple[float, ...] = (25.0, 35.0, 45.0, 50.0, 55.0, 65.0, 75.0)

# Single row (7 cells, ascending R). Centre-to-centre column spacing (um);
# DUT footprint ~600 x 425 um, so leave a clear gap for probe landing / dicing.
_COL_PITCH = 720.0
# Gaps (um) from the die inner edges (past the 50 um keepout) to the row:
# DUT left edges sit _LEFT_MARGIN off the left inner edge, tops _TOP_MARGIN
# below the top inner edge.
_LEFT_MARGIN = 260.0
_TOP_MARGIN = 60.0


@recipe
def _termination_dut(target_resistance: float) -> fw.Component:
    """Probeable termination DUT: GSG pad triplet -> taper -> terminator.

    All three stages are existing PDK cells abutted with ``put()``. Exposes
    one west port ``probe`` on the pad triplet's ``gsg_pads_top_metal_50ohms``
    line (the pads are landed on directly for a DC probe).
    """
    cell = fw.Component()
    pads = cell.add_placed(gsg_bondpads_top_metal_50ohms(), name="pads")
    # Abut the taper's pad side (e2) on the pads' east port; put() auto-rotates
    # so the electrode side (e1) then faces east for the terminator.
    taper = cell.put(
        gsg_taper_electrode_to_pads_top_metal_50ohms(),
        pads.ports.e2,
        port_to="e2",
        name="taper",
    )
    cell.put(
        gsg_terminator_top_metal_50ohms_parallel(target_resistance=target_resistance),
        taper.ports.e1,
        port_to="e1",
        name="term",
    )
    cell.add_port("probe", pads.ports.e1)
    cell.cell_type = "rf_terminator_dut"
    cell.description = (
        f"Probeable GSG termination DUT: {target_resistance:g} ohm parallel-strip "
        "terminator behind a bondpad triplet + electrode-to-pads taper (TOP_METAL)"
    )
    cell.calibration_status = "PLACEHOLDER"
    cell.parameters.target_resistance_ohms = target_resistance
    return cell


def add_gsg_termination_sweep(cell: fw.Component) -> None:
    """Place the GSG termination-resistance sweep along the die's top-left edge.

    A single row of :func:`_termination_dut` cells at the ``_SWEEP_OHMS``
    resistances, ascending left-to-right (25/35/45/50/55/65/75). DUT left
    edges sit ``_LEFT_MARGIN`` off the left inner edge (stepping east by
    ``_COL_PITCH``); their tops sit ``_TOP_MARGIN`` below the top inner edge.
    Instances are named ``term_dut_{R:g}ohm`` and left unrouted (the pad
    triplets are probed directly).
    """
    half_w = _p.die_width.value / 2.0
    half_h = _p.die_height.value / 2.0
    kw = _p.keepout_width.value
    x_left0 = (-half_w + kw) + _LEFT_MARGIN
    y_top0 = (half_h - kw) - _TOP_MARGIN

    for idx, r in enumerate(_SWEEP_OHMS):
        dut = _termination_dut(r)
        b = dut.bbox
        x_left = x_left0 + idx * _COL_PITCH
        cell.add_placed(
            dut,
            name=f"term_dut_{r:g}ohm",
            x=x_left - b.xmin,
            y=y_top0 - b.ymax,
        )
