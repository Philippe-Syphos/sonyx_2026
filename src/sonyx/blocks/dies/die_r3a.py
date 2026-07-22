"""Die holder R3·A — third row, left.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): RF (probe) —
termination · TRL · standalone TW electrode (length sweep). Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ...parameters import DieParameters
from ._frame import die_scaffold


def die_r3a() -> fw.Component:
    """Build and return the R3·A die."""
    cell = die_scaffold("die_R3A", DieParameters())
    # --- R3·A per-die content (see module docstring for planned DUTs) ---
    # Add geometry / routing here; shared placements are reachable on
    # cell.instances[...] (e.g. "edge_couplers_circuit", "bondpads").
    return cell
