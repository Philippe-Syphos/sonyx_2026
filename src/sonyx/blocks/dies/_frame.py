"""Shared die-holder frame for the sonyx 2x4 reticle.

Every die is the **same shape**: a ``die_width x die_height`` rectangle
(10.775 x 5.3125 mm) that sits just inside the deep-etch dicing trench which
surrounds it (the trench is owned by the reticle assembler,
``blocks.reticle``, not by the die). The die-defining rectangle is the ONLY
geometry here — on the ``DIE`` layer (luqia's "Die outline", GDS 0/0,
reference-only). Real DUTs / labels land in each die later via the per-die
modules (``die_r1a`` … ``die_r4b``).

The frame is centred on the origin so the reticle assembler places it by its
centre.
"""

from __future__ import annotations

import picasso as fw
from picasso.geometry.ops import rectangle
from picasso.leaves import make_label

from ...parameters import parameters as _p

# String layers → resolved against the active PDK at materialize time.
#   DIE.boundary  = the die-defining rectangle (GDS 0/0, reference, not printed).
#   WG_RIB.drawing = the rib-waveguide drawing layer the die-ID glyphs print on.
_DIE_LAYER = "DIE.boundary"
_LABEL_LAYER = "WG_RIB.drawing"

# Die-ID label: ~200 um tall glyphs, inset 150 um from the top-left die corner.
_LABEL_HEIGHT = 200.0
_LABEL_MARGIN = 150.0


def die_frame(name: str) -> fw.Component:
    """Return an empty die holder named ``name``, centred at the origin.

    The die boundary is a single ``die_width x die_height`` rectangle drawn
    directly on the ``DIE`` layer (its edges abut the surrounding trench's
    inner wall). A die-ID label (= ``name``) is rendered as visible filled
    polygons via :func:`picasso.leaves.make_label` on the ``WG_RIB.drawing``
    layer and left-aligned in the die's top-left corner. Content is added by
    callers.

    Args:
        name: Cell name (also the die-ID shown in the corner label).

    Returns:
        The die-holder :class:`~picasso.component.Component`.
    """
    half_w = _p.die_width.value / 2.0
    half_h = _p.die_height.value / 2.0
    cell = fw.Component(name=name)

    rectangle(cell, width=_p.die_width.value, height=_p.die_height.value, layer=_DIE_LAYER)

    # Die-ID label as visible glyph polygons. make_label centres the text on
    # x=0 with its top edge (valign="top") at y=0, so offset by half its width
    # to left-align it, inset from the top-left corner.
    label = make_label(text=name, layer=_LABEL_LAYER, magnification=_LABEL_HEIGHT, valign="top")
    label_width = label.bbox.dx
    cell.add_placed(
        label,
        "die_id",
        x=-half_w + _LABEL_MARGIN + label_width / 2.0,
        y=half_h - _LABEL_MARGIN,
    )

    cell.cell_type = "die_assembly"
    return cell
