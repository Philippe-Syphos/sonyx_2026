"""Bond-pad arrays for sonyx dies.

``num_cols`` vertical columns of luqia ``bondpad_top_metal`` pads (TOP_METAL
only — wirebondable / DC-probeable, with the mandatory BONDPADS size/location
marker), built directly in the placed orientation: columns run along +x at the
PDK ``bondpad_pitch``, pads stack along +y at the same pitch. Each column is
its own ``make_array`` call, so a per-column vertical ``col_stagger`` can offset
adjacent columns (see :mod:`sonyx.blocks.dies._frame`, which raises the right
column by half a pitch on the two-column dies). :mod:`sonyx.blocks.dies._frame`
positions the whole block in each die's lower-right corner.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.dc import bondpad_top_metal
from luqia_ln200.tech.parameters import parameters as _pdk
from picasso.connectivity import PortMapping
from picasso.leaves import make_array
from picasso.recipe import recipe


@recipe
def bondpad_array(
    num_cols: int, pads_per_col: int, col_stagger: float = 0.0
) -> fw.Component:
    """A ``num_cols``-column block of TOP_METAL bond pads at the PDK ``bondpad_pitch``.

    Built in the final placed orientation: column ``c`` is a vertical stack of
    ``pads_per_col`` pads (its own ``make_array``) placed at ``x = c * pitch``
    and raised by ``y = c * col_stagger``. ``col_stagger = 0`` gives an aligned
    rectangular grid; ``col_stagger = pitch`` steps each successive (rightward)
    column up by one pad pitch.

    Each column's ports are re-exposed on the returned Component as
    ``"{port}_c{col}"`` (e.g. ``"w_r0_c0_c1"`` — the west face of the bottom pad
    of column 1), so the whole block is addressable through the parent's flat
    ``(instance, port)`` port-spec form.
    """
    pitch = _pdk.bondpad_pitch.value
    arr = fw.Component()
    for col in range(num_cols):
        column = make_array(
            template=bondpad_top_metal(),
            rows=pads_per_col,
            cols=1,
            dx=pitch,
            dy=pitch,
        )
        col_name = f"c{col}"
        arr.add_placed(column, name=col_name, x=col * pitch, y=col * col_stagger)
        for port_name in column.ports:
            arr.port_mappings.append(
                PortMapping(
                    external_name=f"{port_name}_{col_name}",
                    instance_name=col_name,
                    port_name=port_name,
                )
            )
    return arr
