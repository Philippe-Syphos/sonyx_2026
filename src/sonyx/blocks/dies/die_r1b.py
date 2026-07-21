"""Die holder R1·B — top-right of the reticle.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): unbalanced MZI x3
· DC splitter (direct / MZI / tree). Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ._frame import die_frame


def die_r1b() -> fw.Component:
    """Return the R1·B die holder."""
    return die_frame("die_R1B")
