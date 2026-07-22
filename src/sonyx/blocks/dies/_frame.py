"""Shared die scaffold for the sonyx 2x4 reticle.

:func:`die_scaffold` builds the placements **common to every die** — the die
boundary (``DIE``), a perimeter keep-out ring (``KEEPOUT``), the die-ID label
(``WG_RIB.drawing``), the circuit-side edge-coupler array (lower-left), and a
TOP_METAL bond-pad array (lower-right) — and returns the **live, mutable**
``Component``. Each per-die module (``die_r1a`` … ``die_r4b``) is the real
builder for its die: it calls :func:`die_scaffold`, then adds that die's own
geometry / routing on the returned cell (reaching the shared elements' ports
via ``cell.instances[...]``), and returns it. So the shared frame stays a
single source of truth while every die is wired independently.

Every die is the **same shape**: a ``die_width x die_height`` rectangle
(10.775 x 5.3125 mm) that sits just inside the deep-etch dicing trench (owned
by the reticle assembler, ``blocks.reticle``, not the die). The scaffold is
centred on the origin so the reticle assembler places it by its centre.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.bends import cbend_rib_sm_800nm_127um
from picasso.geometry.ops import rectangle
from picasso.leaves import make_label

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ..bondpads import bondpad_array
from ..edge_couplers import circuit_edge_coupler_array

# String layers → resolved against the active PDK at materialize time.
#   DIE.boundary   = the die-defining rectangle (GDS 0/0, reference, not printed).
#   KEEPOUT.drawing = die-edge exclusion ring, "no geometry here" (900/0, design-side).
#   WG_RIB.drawing = the rib-waveguide drawing layer the die-ID glyphs print on.
_DIE_LAYER = "DIE.boundary"
_KEEPOUT_LAYER = "KEEPOUT.drawing"
_LABEL_LAYER = "WG_RIB.drawing"

# Die-ID label: ~200 um tall glyphs, inset 150 um from the top-left die corner.
_LABEL_HEIGHT = 75.0
_LABEL_MARGIN = 0.0


def die_scaffold(name: str, die_params: DieParameters) -> fw.Component:
    """Build the shared die scaffold and return the **live, mutable** cell.

    The caller (a per-die builder) keeps building on the returned cell, adding
    that die's own geometry / routing and reaching the shared placements'
    ports through ``cell.instances[...]`` (named below).

    Places, on a ``die_width x die_height`` cell centred at the origin:

    - the die-defining rectangle on ``DIE`` (edges abut the surrounding
      trench's inner wall);
    - a ``keepout_width`` perimeter keep-out ring on ``KEEPOUT.drawing``;
    - a die-ID label (= ``name``) as filled glyph polygons on
      ``WG_RIB.drawing`` in the top-left corner (instance ``"die_id"``);
    - the circuit-side edge-coupler array (``die_params.num_edge_couplers_circuit``
      couplers) lower-left, facets south past the die edge (instance
      ``"edge_couplers_circuit"``, ports ``o2_r0_cN``), with the leftmost pair
      looped back (instance ``"ec_loopback_circuit"``);
    - a TOP_METAL bond-pad array (``die_params.num_bondpads`` pads) lower-right
      (instance ``"bondpads"``).

    Args:
        name: Cell name (also the die-ID shown in the corner label).
        die_params: This die's :class:`~sonyx.parameters.DieParameters`.

    Returns:
        The live die :class:`~picasso.component.Component` for the caller to
        extend and return.
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
    cell.add_placed(
        label,
        "die_id",
        x=-half_w + _LABEL_MARGIN + _p.keepout_width.value,
        y=-half_h + _LABEL_MARGIN + label.bbox.dx / 2.0 + _p.keepout_width.value,
        rotation=90.0
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
        ec_inst = cell.add_placed(
            arr,
            "edge_couplers_circuit",
            x=left_x - arr_bb.xmin,
            y=facet_y - arr_bb.ymin,
        )
        # Loop back the leftmost edge-coupler pair (c0, c1) with a tight 127 um
        # C-bend U-turn (matches the 127 um coupler pitch) — an alignment loopback.
        if num >= 2:
            loop = cell.put(
                cbend_rib_sm_800nm_127um(),
                ec_inst.ports.o2_r0_c0,
                port_to="o2",
                name="ec_loopback_circuit",
            )
            cell.connect(loop.ports.o1, ec_inst.ports.o2_r0_c1)

    # Bond-pad array (TOP_METAL) in the lower-right corner: horizontal row tiled
    # with make_array. Rightmost pad clears the right keep-out band plus
    # bondpad_horizontal_shift; the row bottom clears the bottom keep-out plus
    # bondpad_vertical_shift (so wirebonded pads stay off the die edge).
    num_bp = int(die_params.num_bondpads.value)
    if num_bp > 0:
        bp = bondpad_array(num_bp)
        bp_bb = bp.bbox
        right_x = half_w - _p.keepout_width.value - _p.bondpad_horizontal_shift.value
        bottom_y = -half_h + _p.keepout_width.value + _p.bondpad_vertical_shift.value
        cell.add_placed(
            bp,
            "bondpads",
            x=right_x - bp_bb.xmax,
            y=bottom_y - bp_bb.ymin,
        )

    cell.cell_type = "die_assembly"
    return cell
