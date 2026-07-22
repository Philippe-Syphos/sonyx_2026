"""Die holder R2·B — second row, right.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): heater Pπ MZI ·
thermal crosstalk. Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ...parameters import DieParameters
from ._frame import die_scaffold


def die_r2b() -> fw.Component:
    """Build and return the R2·B die."""
    cell = die_scaffold("die_R2B", DieParameters())
    # --- R2·B per-die content (see module docstring for planned DUTs) ---
    # Add geometry / routing here; shared placements are reachable on
    # cell.instances[...] (e.g. "edge_couplers_circuit", "bondpads").
    return cell
