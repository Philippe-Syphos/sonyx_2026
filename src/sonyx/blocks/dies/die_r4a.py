"""Die holder R4·A — bottom row, left.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): parallel-propagation
isolation (E2) · spare optical replicas. Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ...parameters import DieParameters
from ._frame import die_scaffold


def die_r4a() -> fw.Component:
    """Build and return the R4·A die."""
    cell = die_scaffold("die_R4A", DieParameters())
    # --- R4·A per-die content (see module docstring for planned DUTs) ---
    # Add geometry / routing here; shared placements are reachable on
    # cell.instances[...] (e.g. "edge_couplers_circuit", "bondpads").
    return cell
