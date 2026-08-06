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

The whole sweep is one self-contained Component
(:func:`gsg_termination_sweep_block`) built in its own local frame -- origin
at the block's top-left content anchor (row-0 DUT left edges, row-0 DUT
tops) -- in two rows (4 then 3 cells, ascending R). The die
(``dies/die_r2b.py``) places that single instance with ``add_placed``.
Placed only -- the pad triplets are probed directly, nothing is routed.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.rf import (
    gsg_bondpads_top_metal_50ohms,
    gsg_taper_electrode_to_pads_top_metal_50ohms,
    gsg_terminator_top_metal_50ohms_parallel,
)
from picasso.recipe import recipe

# Swept termination resistances (ohm), ascending: option-1 bracket around
# 50 ohm (25..75, 10 ohm steps) plus the nominal 50 ohm device -> 7 DUTs.
_SWEEP_OHMS: tuple[float, ...] = (25.0, 35.0, 45.0, 50.0, 55.0, 65.0, 75.0)

# Two rows, 4 then 3 cells (ascending R, filling row 0 left-to-right first), so
# the block stays clear of what else sits in the die's top band.
_ROW_SIZES: tuple[int, ...] = (4, 3)
# Centre-to-centre column spacing (um); DUT footprint ~595 x 425 um, so leave a
# clear gap for probe landing / dicing.
_COL_PITCH = 720.0
# Top-to-top spacing (um) between the two rows -- one DUT height (~425) plus a
# probe-landing gap.
_ROW_PITCH = 545.0


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


@recipe
def gsg_termination_sweep_block() -> fw.Component:
    """The GSG termination-resistance sweep as one self-contained block.

    Local frame: x = 0 on row 0's DUT left edges, y = 0 on row 0's DUT tops
    (the block's top-left content anchor). The die places this single
    Component with ``add_placed``.

    :func:`_termination_dut` cells at the ``_SWEEP_OHMS`` resistances, ascending
    (25/35/45/50/55/65/75), laid out in ``_ROW_SIZES`` rows -- 4 then 3 -- each
    row filling left-to-right before the next starts (stepping east by
    ``_COL_PITCH``); each later row drops ``_ROW_PITCH``. Instances are named
    ``term_dut_{R:g}ohm`` and left unrouted (the pad triplets are probed
    directly).
    """
    cell = fw.Component()
    idx = 0
    for row, count in enumerate(_ROW_SIZES):
        y_top = -row * _ROW_PITCH
        for col in range(count):
            r = _SWEEP_OHMS[idx]
            idx += 1
            dut = _termination_dut(r)
            b = dut.bbox
            x_left = col * _COL_PITCH
            cell.add_placed(
                dut,
                name=f"term_dut_{r:g}ohm",
                x=x_left - b.xmin,
                y=y_top - b.ymax,
            )
    cell.cell_type = "test_structure"
    cell.description = (
        "GSG termination-resistance sweep test block: 7 probeable "
        "pad-taper-terminator DUTs (25-75 ohm) in two rows, unrouted."
    )
    return cell
