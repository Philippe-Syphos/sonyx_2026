"""Die holder R2·B — second row, right.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): heater Pπ MZI ·
thermal crosstalk. Frame only for now.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk

from ...parameters import DieParametersMultimode
from ...parameters import parameters as _p
from ._frame import die_scaffold


def die_r2b() -> fw.Component:
    """Build and return the R2·B die."""
    params = DieParametersMultimode()
    cell = die_scaffold("die_R2B", params)
    # Two GSG phase-modulator electrodes (multimode on column B) stacked
    # vertically: bottom one gsg_modulator_vertical_shift above the die bottom
    # edge, top one gsg_modulator_spacing (centre-to-centre) above it. Placed
    # directly so their ports (o1-o4 optical, e1/e2 electrode) are reachable.
    half_h = _p.die_height.value / 2.0
    modulator = pdk.cells[params.gsg_modulator_cell.value]()
    bot_y = -half_h + _p.gsg_modulator_vertical_shift.value - modulator.bbox.ymin
    cell.add_placed(modulator, "gsg_modulator_bot", y=bot_y)
    cell.add_placed(modulator, "gsg_modulator_top", y=bot_y + _p.gsg_modulator_spacing.value)
    # --- R2·B per-die content (see module docstring for planned DUTs) ---
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    return cell
