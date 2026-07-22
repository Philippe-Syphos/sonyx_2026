"""Bond-pad arrays for sonyx dies.

A horizontal row of luqia ``bondpad_top_metal`` pads (TOP_METAL only —
wirebondable / DC-probeable, with the mandatory BONDPADS size/location
marker), tiled with the ``make_array`` leaf at the PDK ``bondpad_pitch``.
:mod:`sonyx.blocks.dies._frame` positions the array in each die's lower-right
corner.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.dc import bondpad_top_metal
from luqia_ln200.tech.parameters import parameters as _pdk
from picasso.leaves import make_array
from picasso.recipe import recipe


@recipe
def bondpad_array(num_pads: int) -> fw.Component:
    """A row of ``num_pads`` TOP_METAL bond pads at the PDK ``bondpad_pitch``."""
    return make_array(
        template=bondpad_top_metal(),
        rows=1,
        cols=num_pads,
        dx=_pdk.bondpad_pitch.value,
        dy=0.0,
    )
