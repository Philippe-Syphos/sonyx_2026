"""Shared die-holder frame for the sonyx 2x4 reticle.

Every die is the **same shape**: a ``die_width x die_height`` rectangle
(10.775 x 5.3125 mm) that sits just inside the deep-etch dicing trench which
surrounds it (the trench is owned by the reticle assembler,
``blocks.reticle``, not by the die). The frame carries the die boundary
(``DIE``), a perimeter keep-out ring (``KEEPOUT``), the die-ID label
(``WG_RIB.drawing``), and the circuit-side edge-coupler array in the
lower-left corner. Further DUTs land in each die later via the per-die
modules (``die_r1a`` … ``die_r4b``).

The frame is centred on the origin so the reticle assembler places it by its
centre.
"""

from __future__ import annotations

import picasso as fw
from picasso.geometry.ops import rectangle
from picasso.leaves import make_label

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ..edge_couplers import circuit_edge_coupler_array

# String layers → resolved against the active PDK at materialize time.
#   DIE.boundary   = the die-defining rectangle (GDS 0/0, reference, not printed).
#   KEEPOUT.drawing = die-edge exclusion ring, "no geometry here" (900/0, design-side).
#   WG_RIB.drawing = the rib-waveguide drawing layer the die-ID glyphs print on.
_DIE_LAYER = "DIE.boundary"
_KEEPOUT_LAYER = "KEEPOUT.drawing"
_LABEL_LAYER = "WG_RIB.drawing"

# Die-ID label: ~200 um tall glyphs, inset 150 um from the top-left die corner.
_LABEL_HEIGHT = 200.0
_LABEL_MARGIN = 150.0


def die_frame(name: str, die_params: DieParameters) -> fw.Component:
    """Return a die holder named ``name``, centred at the origin.

    The die boundary is a single ``die_width x die_height`` rectangle drawn
    directly on the ``DIE`` layer (its edges abut the surrounding trench's
    inner wall). A ``keepout_width`` perimeter keep-out band (die-edge
    exclusion ring) is drawn just inside that edge on ``KEEPOUT.drawing``. A
    die-ID label (= ``name``) is rendered as visible filled polygons via
    :func:`picasso.leaves.make_label` on the ``WG_RIB.drawing`` layer and
    left-aligned in the die's top-left corner. The circuit-side edge-coupler
    array (``die_params.num_edge_couplers_circuit`` couplers) sits in the
    lower-left corner, facets protruding south past the die edge. Further
    content is added by callers.

    Args:
        name: Cell name (also the die-ID shown in the corner label).
        die_params: This die's :class:`~sonyx.parameters.DieParameters`.

    Returns:
        The die-holder :class:`~picasso.component.Component`.
    """
    half_w = _p.die_width.value / 2.0
    half_h = _p.die_height.value / 2.0
    cell = fw.Component(name=name)

    rectangle(cell, width=_p.die_width.value, height=_p.die_height.value, layer=_DIE_LAYER)

    # Perimeter keep-out band (die-edge exclusion ring), width keepout_width,
    # outer edge on the die edge. Four non-overlapping rectangle tiles (top /
    # bottom full-width, left / right filling the gap between) — an exact ring
    # with no corner gaps.
    kw = _p.keepout_width.value
    w, h = _p.die_width.value, _p.die_height.value
    band_h = h - 2.0 * kw
    top_y = half_h - kw / 2.0
    side_x = half_w - kw / 2.0
    rectangle(cell, width=w, height=kw, layer=_KEEPOUT_LAYER, center=(0.0, top_y))
    rectangle(cell, width=w, height=kw, layer=_KEEPOUT_LAYER, center=(0.0, -top_y))
    rectangle(cell, width=kw, height=band_h, layer=_KEEPOUT_LAYER, center=(-side_x, 0.0))
    rectangle(cell, width=kw, height=band_h, layer=_KEEPOUT_LAYER, center=(side_x, 0.0))

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

    # Circuit-side edge-coupler array in the lower-left corner: horizontal row,
    # facets south. Leftmost coupler clears the left keep-out band plus an extra
    # edge_coupler_horizontal_shift; the facet tips land edge_coupler_protrusion
    # past (south of) the die bottom edge, into the deep-trench zone.
    num = int(die_params.num_edge_couplers_circuit.value)
    if num > 0:
        arr = circuit_edge_coupler_array(num)
        arr_bb = arr.bbox
        left_x = -half_w + _p.keepout_width.value + _p.edge_coupler_horizontal_shift.value
        facet_y = -half_h - _p.edge_coupler_protrusion.value
        cell.add_placed(
            arr,
            "edge_couplers_circuit",
            x=left_x - arr_bb.xmin,
            y=facet_y - arr_bb.ymin,
        )

    cell.cell_type = "die_assembly"
    return cell
