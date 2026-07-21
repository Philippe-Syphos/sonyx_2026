"""DRC sign-off configuration for sonyx — the layout's rule deck.

``drc_rules`` overrides the PDK's deck for this layout's sign-off run
(``layout.run_drc()`` and the DRC step of ``python -m sonyx.artifacts``).
Leave it ``None`` to fall back to the PDK's deck (if the PDK ships one).

Build a layout-specific deck from picasso's DRC primitives when you need
checks beyond the PDK's — extra keep-outs, project density targets, or
tighter rules on a critical layer:

    drc_rules = fw.DRCDeck(
        name="sonyx_signoff",
        rules=[
            fw.min_width((2, 10), 0.3, name="LT_RIDGE.min_width"),
            fw.min_space((2, 10), 0.3, name="LT_RIDGE.min_space"),
        ],
    )
"""

from __future__ import annotations

import picasso as fw

drc_rules: fw.DRCDeck | None = None
