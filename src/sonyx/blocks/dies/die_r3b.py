"""Die holder R3·B — third row, right.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): DC reflectometer
(E3) · N-tree radiating-gap isolation (E1). Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ...parameters import DieParameters
from ._frame import die_scaffold


def die_r3b() -> fw.Component:
    """Build and return the R3·B die."""
    cell = die_scaffold("die_R3B", DieParameters())
    # --- R3·B per-die content (see module docstring for planned DUTs) ---
    # Add geometry / routing here; shared placements are reachable on
    # cell.instances[...] (e.g. "edge_couplers_circuit", "bondpads").
    return cell
