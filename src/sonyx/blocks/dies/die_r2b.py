"""Die holder R2·B — second row, right.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): heater Pπ MZI ·
thermal crosstalk. Frame only for now.
"""

from __future__ import annotations

import picasso as fw

from ...parameters import DieParameters
from ._frame import die_frame


def die_r2b() -> fw.Component:
    """Return the R2·B die holder."""
    return die_frame("die_R2B", DieParameters())
