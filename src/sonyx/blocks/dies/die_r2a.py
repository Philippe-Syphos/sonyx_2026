"""Die holder R2·A — second row, left.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): GC DOE — 51
variants (fills the test region). Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ...parameters import DieParameters
from ._frame import die_scaffold


def die_r2a() -> fw.Component:
    """Build and return the R2·A die."""
    cell = die_scaffold("die_R2A", DieParameters())
    # --- R2·A per-die content (see module docstring for planned DUTs) ---
    # Add geometry / routing here; shared placements are reachable on
    # cell.instances[...] (e.g. "edge_couplers_circuit", "bondpads").
    return cell
