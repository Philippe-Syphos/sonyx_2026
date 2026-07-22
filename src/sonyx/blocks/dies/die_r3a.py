"""Die holder R3·A — third row, left.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): RF (probe) —
termination · TRL · standalone TW electrode (length sweep). Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ...parameters import DieParameters
from ._frame import die_frame


def die_r3a() -> fw.Component:
    """Return the R3·A die holder."""
    return die_frame("die_R3A", DieParameters())
