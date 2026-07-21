"""Die floorplan for sonyx — the optional die-frame config.

``None`` means frameless. When set, ``layout.materialize()`` stamps the die
boundary (``CHIP.boundary``) and label (``LABELS``) onto the top cell
automatically. The ``origin`` convention ("center" / "corner") is the
contract a future reticle / shuttle layer composes against.
"""

from __future__ import annotations

import picasso as fw

# Two modes (mutually exclusive on the geometry, both accept a label):
#
# 1. Cell mode — point at a PDK-registered die cell that owns the floorplan
#    geometry (exclusion ring, corner keep-outs, markers). Preferred when
#    your PDK ships a die template.
#
#        floorplan = fw.Floorplan(cell="die_default", label="sonyx")
#
# 2. Primitive mode — the framework draws a single rectangle on
#    `boundary_layer` (default "CHIP.boundary"). Fallback for PDKs that
#    don't ship a die template.
#
#        floorplan = fw.Floorplan(width=5000.0, height=5000.0, label="sonyx")
floorplan: fw.Floorplan | None = None
