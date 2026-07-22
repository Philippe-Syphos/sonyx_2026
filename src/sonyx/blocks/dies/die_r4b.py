"""Die holder R4·B — bottom-right of the reticle.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): edge-coupled SM+ULL
spirals · OFDR reflectometry (E4). Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ...parameters import DieParameters
from ._frame import die_scaffold


def die_r4b() -> fw.Component:
    """Build and return the R4·B die."""
    cell = die_scaffold("die_R4B", DieParameters())
    # --- R4·B per-die content (see module docstring for planned DUTs) ---
    # Add geometry / routing here; shared placements are reachable on
    # cell.instances[...] (e.g. "edge_couplers_circuit", "bondpads").
    return cell
