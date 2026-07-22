"""Die holder R1·A — top-left of the reticle.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): loss spirals
SM+ULL (GC, 4 lengths) · racetrack (Ls x gap). Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ...parameters import DieParameters
from ._frame import die_frame


def die_r1a() -> fw.Component:
    """Return the R1·A die holder."""
    return die_frame("die_R1A", DieParameters())
