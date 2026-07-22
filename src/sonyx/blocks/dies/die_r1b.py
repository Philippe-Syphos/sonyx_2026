"""Die holder R1·B — top-right of the reticle.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): unbalanced MZI x3
· DC splitter (direct / MZI / tree). Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ...parameters import DieParameters
from ._frame import die_scaffold


def die_r1b() -> fw.Component:
    """Build and return the R1·B die."""
    cell = die_scaffold("die_R1B", DieParameters())
    # --- R1·B per-die content (see module docstring for planned DUTs) ---
    # Add geometry / routing here; shared placements are reachable on
    # cell.instances[...] (e.g. "edge_couplers_circuit", "bondpads").
    return cell
