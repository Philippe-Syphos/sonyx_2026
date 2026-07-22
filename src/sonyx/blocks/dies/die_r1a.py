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
    modulator = pdk.cells[params.gsg_modulator_cell.value]()
    bot_y = -half_h + _p.gsg_modulator_vertical_shift.value - modulator.bbox.ymin
    cell.add_placed(modulator, "gsg_modulator_bot", y=bot_y)
    cell.add_placed(modulator, "gsg_modulator_top", y=bot_y + _p.gsg_modulator_spacing.value)
    # --- R1·A per-die content (see module docstring for planned DUTs) ---
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    return cell
