"""Die holder R1·A — top-left of the reticle.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): loss spirals
SM+ULL (GC, 4 lengths) · racetrack (Ls x gap). Frame only for now.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ._frame import die_scaffold


def die_r1a() -> fw.Component:
    """Build and return the R1·A die."""
    params = DieParameters()
    cell = die_scaffold("die_R1A", params)
    # Two GSG phase-modulator electrodes (SM on column A) stacked vertically:
    # bottom one gsg_modulator_vertical_shift above the die bottom edge, top one
    # gsg_modulator_spacing (centre-to-centre) above it. Placed directly so their
    # ports (o1-o4 optical, e1/e2 electrode) are reachable for per-die routing.
    half_h = _p.die_height.value / 2.0
    modulator = pdk.cells[params.gsg_modulator_cell.value](
        length=_p.gsg_modulator_electrode_length.value,
    )
    mb = modulator.bbox
    x0 = -mb.center_x  # centre the electrode in x
    bot_y = -half_h + _p.gsg_modulator_vertical_shift.value - mb.ymin
    top_y = bot_y + _p.gsg_modulator_spacing.value
    mod_bot = cell.add_placed(modulator, "gsg_modulator_bot", x=x0, y=bot_y)
    mod_top = cell.add_placed(modulator, "gsg_modulator_top", x=x0, y=top_y)
    # RF input on the right (east): a via lifts each modulator's bottom-metal
    # electrode (e2) up to top metal (same chain for SM and multimode).
    cell.put(
        pdk.cells["gsg_via_electrode_top_bot_holes_50ohms"](),
        mod_bot.ports.e2,
        port_to="bot_e1",
        name="rf_via_bot",
    )
    cell.put(
        pdk.cells["gsg_via_electrode_top_bot_holes_50ohms"](),
        mod_top.ports.e2,
        port_to="bot_e1",
        name="rf_via_top",
    )
    # --- R1·A per-die content (see module docstring for planned DUTs) ---
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    return cell
