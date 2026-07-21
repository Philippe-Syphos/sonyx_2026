"""Die holder R2·A — second row, left.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): GC DOE — 51
variants (fills the test region). Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ._frame import die_frame


def die_r2a() -> fw.Component:
    """Return the R2·A die holder."""
    return die_frame("die_R2A")
