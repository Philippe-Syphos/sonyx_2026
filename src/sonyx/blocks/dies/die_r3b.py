"""Die holder R3·B — third row, right.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): DC reflectometer
(E3) · N-tree radiating-gap isolation (E1). Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ...parameters import DieParameters
from ._frame import die_frame


def die_r3b() -> fw.Component:
    """Return the R3·B die holder."""
    return die_frame("die_R3B", DieParameters())
