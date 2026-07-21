"""Die holder R4·A — bottom row, left.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): parallel-propagation
isolation (E2) · spare optical replicas. Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ._frame import die_frame


def die_r4a() -> fw.Component:
    """Return the R4·A die holder."""
    return die_frame("die_R4A")
