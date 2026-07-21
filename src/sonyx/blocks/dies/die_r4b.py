"""Die holder R4·B — bottom-right of the reticle.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): edge-coupled SM+ULL
spirals · OFDR reflectometry (E4). Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ._frame import die_frame


def die_r4b() -> fw.Component:
    """Return the R4·B die holder."""
    return die_frame("die_R4B")
