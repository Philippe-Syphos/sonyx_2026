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
from luqia_ln200.cells.couplers import gratingcoupler_alignment_rib_sm_800nm_ext
from luqia_ln200.cells.dc import bonding_pad
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
_LABEL_HEIGHT = 40.0
_LABEL_MARGIN = 60.0

# Gap (um) between the bond-pad array and the thermistance bonding pad to its
# left, and how far the pad drops below the array bottom.
_THERMISTANCE_GAP = 300.0
_THERMISTANCE_DROP = 100.0


def die_scaffold(
    name: str,
    die_params: DieParameters,
    bondpad_rotation: float = 90.0,
    num_bondpads: int | None = None,
) -> fw.Component:
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
        bondpad_rotation: Rotation (deg) of the lower-right bond-pad array —
            ``90`` (default) stands the row up into a vertical column against the
            right edge; ``0`` keeps the original horizontal row.
        num_bondpads: Override for the number of pads in the bond-pad array;
            ``None`` (default) uses ``die_params.num_bondpads``.

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
            # One additional edge coupler just outboard (one pitch left) of the
            # alignment loop, aligned to the array (same identical coupler+lead
            # unit) — an extra reference facet beside the loopback.
            extra = circuit_edge_coupler_array(1)
            cell.add_placed(
                extra,
                "edge_coupler_extra",
                x=(left_x - arr_bb.xmin) - _p.edge_coupling_pitch_for_circuits.value,
                y=facet_y - arr_bb.ymin,
            )

    # Bond-pad array (TOP_METAL) in the lower-right corner: horizontal row tiled
    # with make_array. Rightmost pad clears the right keep-out band plus
    # bondpad_horizontal_shift; the row bottom clears the bottom keep-out plus
    # bondpad_vertical_shift (so wirebonded pads stay off the die edge).
    num_bp = int(num_bondpads if num_bondpads is not None else die_params.num_bondpads.value)
    right_x = half_w - _p.keepout_width.value - _p.bondpad_horizontal_shift.value
    bottom_y = -half_h + _p.keepout_width.value + _p.bondpad_vertical_shift.value
    if num_bp > 0:
        bp = bondpad_array(num_bp)
        bp_bb = bp.bbox
        # Anchor the array's (post-rotation) bottom-right corner to (right_x,
        # bottom_y). rotation=90 maps (x, y) -> (-y, x), so the placed right edge
        # is -ymin and the placed bottom is xmin; rotation=0 keeps the raw bbox.
        if bondpad_rotation == 90.0:
            placed_xmax, placed_ymin = -bp_bb.ymin, bp_bb.xmin
            array_width = bp_bb.dy
        else:
            placed_xmax, placed_ymin = bp_bb.xmax, bp_bb.ymin
            array_width = bp_bb.dx
        cell.add_placed(
            bp,
            "bondpads",
            x=right_x - placed_xmax,
            y=bottom_y - placed_ymin,
            rotation=bondpad_rotation,
        )
        # Thermistance bonding pad in the lower-right region, _THERMISTANCE_GAP
        # left of the bond-pad array and bottom-aligned to it.
        therm = bonding_pad(
            x=_p.thermistance_bonding_pad_width.value,
            y=_p.thermistance_bonding_pad_height.value,
        )
        tb = therm.bbox
        cell.add_placed(
            therm,
            "thermistance_bonding_pad",
            x=((right_x - array_width) - _THERMISTANCE_GAP) - tb.xmax,
            y=(bottom_y - _THERMISTANCE_DROP) - tb.ymin,
        )

    # One N-S grating-coupler alignment loop tucked into each of the four die
    # corners, flush to the keep-out inner walls (fibre-alignment references
    # common to every die).
    left_inner, right_inner = -half_w + kw, half_w - kw
    bot_inner, top_inner = -half_h + kw, half_h - kw
    ab = gratingcoupler_alignment_rib_sm_800nm_ext().bbox
    corners = {
        "gc_align_tl": (left_inner - ab.xmin, top_inner - ab.ymax),
        "gc_align_tr": (right_inner - ab.xmax, top_inner - ab.ymax),
        "gc_align_bl": (left_inner - ab.xmin, bot_inner - ab.ymin),
        "gc_align_br": (right_inner - ab.xmax, bot_inner - ab.ymin),
    }
    for cname, (cx, cy) in corners.items():
        cell.add_placed(gratingcoupler_alignment_rib_sm_800nm_ext(), cname, x=cx, y=cy)

    cell.cell_type = "die_assembly"
    return cell
