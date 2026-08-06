"""Shared die scaffold for the sonyx 2x4 reticle.

:func:`die_scaffold` builds the placements **common to every die** — the die
boundary (``DIE``), a perimeter keep-out ring (``KEEPOUT``), the die-ID label
(``WG_RIB.drawing`` in a moat), the circuit-side edge-coupler array (lower-left), and a
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

from collections.abc import Iterable

import picasso as fw
from luqia_ln200.cells.bends import cbend_rib_sm_800nm_127um
from luqia_ln200.cells.couplers import gratingcoupler_alignment_rib_sm_800nm_ext
from luqia_ln200.cells.dc import bonding_pad
from luqia_ln200.cells.fiducials import fiducial_cross_stepped_moat_labels
from luqia_ln200.cells.labels import label_moat_labels
from luqia_ln200.cells.waveguides import spiral_rib_sm_800nm
from luqia_ln200.tech.parameters import parameters as _pdk
from picasso.component import PortSpec
from picasso.geometry.ops import rectangle

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ..bondpads import bondpad_array
from ..edge_couplers import circuit_edge_coupler_array
from ..labels import add_circuit_edge_coupler_labels
from ..pcm import add_pcm_block

# String layers → resolved against the active PDK at materialize time.
#   DIE.boundary   = the die-defining rectangle (GDS 0/0, reference, not printed).
#   KEEPOUT.drawing = die-edge exclusion ring, "no geometry here" (900/0, design-side).
# The die-ID goes through the PDK's moated label cell (label_moat_labels): glyphs
# on WG_RIB.drawing (10/0) in a WG_RIB.field moat, like every other label in the
# layout (see ..labels).
_DIE_LAYER = "DIE.boundary"
_KEEPOUT_LAYER = "KEEPOUT.drawing"

# Die-ID label: ~40 um tall glyphs, inset 150 um from the top-left die corner.
_LABEL_HEIGHT = 40.0
_LABEL_MARGIN = 60.0

# Gap (um) between the bond-pad array and the thermistance bonding pad to its
# left, and how far the pad drops below the array bottom.
_THERMISTANCE_GAP = 300.0
_THERMISTANCE_DROP = 100.0
# Hard-coded centre (x, y) in um of the thermistance bonding pad, identical on
# every die -- see :func:`place_thermistance_pad`.
_THERMISTANCE_CENTER = (4950.0, 1300.0)
# Gap (um) between a reference block's west edge and the thermistance pad parked
# beside it by :func:`place_thermistance_pad_west_of` -- the R1A/R1B override of
# the shared centre. Mirrors _THERMISTANCE_GAP, the pad's gap to the bond-pad
# array it sits beside on the other six dies, so the pad keeps one clearance
# convention wherever it lands.
_THERMISTANCE_GC_GAP = 300.0

# Extra westward shift (um) of the DC bond-pad array, on top of
# bondpad_horizontal_shift. Widens the strip between the array and the die edge
# so the DC bias lines landing on the pads' east faces have a lane to run the
# length of the stack in.
_BONDPAD_WEST_SHIFT = 150.0

# Gap (um) between the per-die PCM & calibration block's right edge and the
# thermistance bonding pad it sits next to (docs/pcm_cells.md).
_PCM_GAP = 200.0
# Extra westward shift (um) of the whole PCM block, on every die. Trimmed
# 1500 -> 1300 when the PCM bond-pad pair grew into the 9-pad AEPONYX probe
# row (~1.75 mm wider, packed westward): at 1500 the block's west end (the
# open-GSG cell) landed on R1A's SM delay spiral; 1300 clears it while every
# die keeps >= 750 um to its nearest eastern neighbour.
_PCM_WEST_SHIFT = 1300.0

# Single SM loss/delay spiral placed just east of the rightmost circuit edge
# coupler: target path length (5 cm), loop count, and gap from the array edge.
_SPIRAL_TEST_LENGTH = 50000.0
_SPIRAL_N_LOOPS = 8
_SPIRAL_GAP = 100.0
# Raise the spiral off the bottom keep-out edge. 150 rather than the original
# 100: the extra 50 opens the strip beneath it to 150 um, enough for the 110 um
# moated south fiducial to sit clear instead of overshooting into the spiral.
_SPIRAL_VERTICAL_SHIFT = 150.0

# Clearance (um) between the circuit edge-coupler array's top edge and the
# bottom of the stepped-cross fiducials above it -- their moat edge, since the
# marks are the moated PDK variant. Shared by both marks, so they sit on one
# horizontal line; 200 clears the spiral feed routes, which rise ~167 um off the
# two easternmost couplers to meet the (raised) spiral's west ports.
_FIDUCIAL_EC_GAP = 200.0

# Clearance (um) between a keep-out ring inner wall and a fiducial's moat edge.
# Both the mark under the spiral and the bottom-left corner mark anchor off the
# ring this way rather than being centred in their band (see the placement
# comments), so the ring stays clear and the slack goes to the functional side.
_FIDUCIAL_KEEPOUT_GAP = 10.0

# Northward shift (um) of the bottom-left corner pair -- the alignment grating
# coupler (``gc_align_bl``) and the die-ID label stacked above it. Lifting both
# by the same amount opens a band on the keep-out ring for the corner fiducial
# without changing their spacing relative to each other.
_BL_CORNER_NORTH_SHIFT = 150.0

# Circuit edge-coupler pair (0-based column indices, west to east) the western
# stepped-cross fiducial is centred over. The eastern one takes the last pair.
_FIDUCIAL_MID_PAIR = (2, 3)


def die_scaffold(
    name: str,
    die_params: DieParameters,
    num_bondpads: int | None = None,
    num_bondpad_cols: int | None = None,
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
      ``WG_RIB.drawing``, in their ``WG_RIB.field`` moat, reading up the
      bottom-left corner (instance ``"die_id"``) — lifted together with
      ``gc_align_bl`` by ``_BL_CORNER_NORTH_SHIFT`` so a corner fiducial
      (instance ``"fiducial_corner_bl"``) fits on the keep-out ring below;
    - the circuit-side edge-coupler array (``die_params.num_edge_couplers_circuit``
      couplers) lower-left, facets south past the die edge (instance
      ``"edge_couplers_circuit"``, ports ``o2_r0_cN``), with the leftmost pair
      looped back (instance ``"ec_loopback_circuit"``), three moated
      stepped-cross fiducials — two on one line above the array (over the two
      easternmost couplers and over the ``_FIDUCIAL_MID_PAIR`` couplers,
      instances ``"fiducial_ec_circuit"`` / ``"fiducial_ec_circuit_mid"``) and
      one in the bottom strip under the test spiral
      (``"fiducial_spiral_south"``) — and one visible ``WG_RIB.drawing`` name per
      facet (instances ``"label_ec_c*"`` / ``"label_ec_ref"``, see
      :mod:`..labels`);
    - a TOP_METAL bond-pad array (``die_params.num_bondpads`` pads in
      ``die_params.num_bondpad_cols`` columns) lower-right (instance
      ``"bondpads"``).

    Args:
        name: Cell name (also the die-ID shown in the corner label).
        die_params: This die's :class:`~sonyx.parameters.DieParameters`.
        num_bondpads: Override for the total number of pads in the bond-pad
            array; ``None`` (default) uses ``die_params.num_bondpads``.
        num_bondpad_cols: Override for the number of physical columns in the
            bond-pad array; ``None`` (default) uses
            ``die_params.num_bondpad_cols``. Multi-pad columns are staggered so
            each rightward column steps up half a pad pitch (R1A's single-pad
            columns — a plain horizontal row — are left un-staggered).

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

    # Die-ID label as visible glyph polygons in their WG_RIB.field moat, reading
    # south-to-north up the bottom-left corner. The PDK cell centres the text on
    # x=0 with its top edge (valign="top") at y=0, so offset by half its
    # (moat-inclusive) width to left-align it, inset from the corner and lifted
    # by _BL_CORNER_NORTH_SHIFT along with the alignment coupler below it.
    label = label_moat_labels(text=name, height=_LABEL_HEIGHT, valign="top")
    cell.add_placed(
        label,
        name="die_id",
        x=-half_w + _LABEL_MARGIN + _p.keepout_width.value,
        y=(
            -half_h
            + _LABEL_MARGIN
            + label.bbox.dx / 2.0
            + _p.keepout_width.value
            + _BL_CORNER_NORTH_SHIFT
        ),
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
            name="edge_couplers_circuit",
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
                name="edge_coupler_extra",
                x=(left_x - arr_bb.xmin) - _p.edge_coupling_pitch_for_circuits.value,
                y=facet_y - arr_bb.ymin,
            )
        # Single SM loss/delay spiral (3 cm, long side E-W) just east of the
        # rightmost circuit edge coupler, sitting inside the bottom keep-out.
        spiral = spiral_rib_sm_800nm(
            target_length=_SPIRAL_TEST_LENGTH, n_loops=_SPIRAL_N_LOOPS
        )
        sp_bb = spiral.bbox
        cell.add_placed(
            spiral,
            name="test_spiral_sm",
            x=((left_x + arr_bb.dx) + _SPIRAL_GAP) - sp_bb.xmin,
            y=(-half_h + _p.keepout_width.value + _SPIRAL_VERTICAL_SHIFT) - sp_bb.ymin,
        )
        # Feed the spiral (a 2-port line, both ports west-facing at its west edge)
        # from the two rightmost circuit edge couplers (north-facing, just west of
        # the spiral). Bundle autoroute: the rightmost EC -> spiral o1 (lower port),
        # the next EC left -> spiral o2 (upper port), so the two risers/horizontals
        # don't cross and both routes stay west of the spiral body (no obstacles).
        if num >= 2:
            ec_ports: list[PortSpec] = [
                ("edge_couplers_circuit", f"o2_r0_c{num - 1}"),
                ("edge_couplers_circuit", f"o2_r0_c{num - 2}"),
            ]
            spiral_ports: list[PortSpec] = [
                ("test_spiral_sm", "o1"),
                ("test_spiral_sm", "o2"),
            ]
            cell.autoroute(
                ports_a=ec_ports,
                ports_b=spiral_ports,
                spec="routing_sm_tight",
                strategy="vgraph_rect",
            )
        # Stepped-cross registration fiducials over the coupler array: one
        # centred between the two easternmost couplers, one between the
        # _FIDUCIAL_MID_PAIR couplers. Both float the same _FIDUCIAL_EC_GAP above
        # the array top, so the pair sits on a single horizontal line. Every mark
        # is the moated PDK variant, so its bbox (and every gap measured off it
        # here) is the WG_RIB.field moat edge, not the cross itself.
        ec_top = facet_y - arr_bb.ymin + arr_bb.ymax
        fiducial_pairs = {
            "fiducial_ec_circuit": (num - 2, num - 1),
            "fiducial_ec_circuit_mid": _FIDUCIAL_MID_PAIR,
        }
        for fid_name, (c_west, c_east) in fiducial_pairs.items():
            if c_west < 0 or c_east >= num:
                continue
            fid = fiducial_cross_stepped_moat_labels()
            west_x = ec_inst.ports[f"o2_r0_c{c_west}"].position[0]
            east_x = ec_inst.ports[f"o2_r0_c{c_east}"].position[0]
            cell.add_placed(
                fid,
                name=fid_name,
                x=(east_x + west_x) / 2.0,
                y=(ec_top + _FIDUCIAL_EC_GAP) - fid.bbox.ymin,
            )
        # A third mark in the bottom strip east of the array, tucked under the
        # spiral: west moat edge flush with the spiral's west edge (both stand
        # _SPIRAL_GAP east of the array), sitting on the keep-out ring's inner
        # wall plus _FIDUCIAL_KEEPOUT_GAP. Moated, the mark is 110 um tall,
        # which is why _SPIRAL_VERTICAL_SHIFT lifts the spiral to leave a 150 um
        # strip here: anchored off the keep-out wall the mark clears the ring
        # below and the spiral above outright, no moat-merge needed.
        fid = fiducial_cross_stepped_moat_labels()
        fid_bb = fid.bbox
        cell.add_placed(
            fid,
            name="fiducial_spiral_south",
            x=((left_x + arr_bb.dx) + _SPIRAL_GAP) - fid_bb.xmin,
            y=((-half_h + kw) + _FIDUCIAL_KEEPOUT_GAP) - fid_bb.ymin,
        )
        # Visible per-facet names (WG_RIB.drawing glyphs in their moat), read off
        # the placed ports — one vertical label alongside each coupler body.
        add_circuit_edge_coupler_labels(cell, num)

    # Bond-pad array (TOP_METAL) in the lower-right corner: num_bondpad_cols
    # vertical columns, built directly in the placed orientation (one make_array
    # per column, see ..bondpads.bondpad_array). Rightmost column clears the right
    # keep-out band plus bondpad_horizontal_shift; the (lowest) column bottom
    # clears the bottom keep-out plus bondpad_vertical_shift (so wirebonded pads
    # stay off the die edge).
    num_bp = int(num_bondpads if num_bondpads is not None else die_params.num_bondpads.value)
    num_cols = int(
        num_bondpad_cols if num_bondpad_cols is not None else die_params.num_bondpad_cols.value
    )
    right_x = half_w - _p.keepout_width.value - _p.bondpad_horizontal_shift.value
    bottom_y = -half_h + _p.keepout_width.value + _p.bondpad_vertical_shift.value
    # Thermistance pad's placed left / top edges — the PCM block anchors to them.
    therm_left: float | None = None
    therm_top: float | None = None
    if num_bp > 0:
        if num_cols < 1 or num_bp % num_cols != 0:
            raise ValueError(
                f"num_bondpads ({num_bp}) must be a positive multiple of "
                f"num_bondpad_cols ({num_cols}) so the pads split evenly into columns"
            )
        pads_per_col = num_bp // num_cols
        # Stagger multi-pad columns up by half a pad pitch each (right column
        # higher), opening a lane between the columns' west faces for the DC bias
        # routing. Single-pad columns (R1A's horizontal row) get no stagger -- it
        # would just splay the row into a diagonal.
        col_stagger = _pdk.bondpad_pitch.value / 2.0 if pads_per_col > 1 else 0.0
        bp = bondpad_array(
            num_cols=num_cols, pads_per_col=pads_per_col, col_stagger=col_stagger
        )
        bp_bb = bp.bbox
        array_width = bp_bb.dx
        # _BONDPAD_WEST_SHIFT moves the array only -- right_x still anchors the
        # thermistance pad and, through it, the PCM block, so those stay put.
        # Anchor the (lowest, un-staggered) column's bottom-right corner to
        # (right_x, bottom_y); the staggered columns rise above bottom_y.
        cell.add_placed(
            bp,
            name="bondpads",
            x=right_x - bp_bb.xmax - _BONDPAD_WEST_SHIFT,
            y=bottom_y - bp_bb.ymin,
        )
        # Thermistance bonding pad in the lower-right region, _THERMISTANCE_GAP
        # left of the bond-pad array and bottom-aligned to it.
        therm = bonding_pad(
            x=_p.thermistance_bonding_pad_width.value,
            y=_p.thermistance_bonding_pad_height.value,
        )
        tb = therm.bbox
        therm_x = ((right_x - array_width) - _THERMISTANCE_GAP) - tb.xmax
        therm_y = (bottom_y - _THERMISTANCE_DROP) - tb.ymin
        cell.add_placed(therm, name="thermistance_bonding_pad", x=therm_x, y=therm_y)
        therm_left = therm_x + tb.xmin
        therm_top = therm_y + tb.ymax

    # One N-S grating-coupler alignment loop tucked into each of the four die
    # corners, flush to the keep-out inner walls (fibre-alignment references
    # common to every die). The bottom-left one rides _BL_CORNER_NORTH_SHIFT
    # above the wall instead, clearing the band its corner fiducial sits in.
    left_inner, right_inner = -half_w + kw, half_w - kw
    bot_inner, top_inner = -half_h + kw, half_h - kw
    ab = gratingcoupler_alignment_rib_sm_800nm_ext().bbox
    corners = {
        "gc_align_tl": (left_inner - ab.xmin, top_inner - ab.ymax),
        "gc_align_tr": (right_inner - ab.xmax, top_inner - ab.ymax),
        "gc_align_bl": (left_inner - ab.xmin, bot_inner - ab.ymin + _BL_CORNER_NORTH_SHIFT),
        "gc_align_br": (right_inner - ab.xmax, bot_inner - ab.ymin),
    }
    for cname, (cx, cy) in corners.items():
        cell.add_placed(gratingcoupler_alignment_rib_sm_800nm_ext(), name=cname, x=cx, y=cy)

    # Corner fiducial in the band the shift above opened: sitting on the bottom
    # and left keep-out inner walls plus _FIDUCIAL_KEEPOUT_GAP, so it is keyed to
    # the die corner itself rather than to any structure that might move. The
    # band is _BL_CORNER_NORTH_SHIFT tall and the mark 110 um, and to the east the
    # nearest neighbour is the extra reference edge coupler.
    corner_fid = fiducial_cross_stepped_moat_labels()
    cf_bb = corner_fid.bbox
    cell.add_placed(
        corner_fid,
        name="fiducial_corner_bl",
        x=(left_inner + _FIDUCIAL_KEEPOUT_GAP) - cf_bb.xmin,
        y=(bot_inner + _FIDUCIAL_KEEPOUT_GAP) - cf_bb.ymin,
    )

    # Per-die PCM & calibration block (docs/pcm_cells.md): placed left of where
    # the thermistance bonding pad is anchored (its DC-pad end nearest it), tops
    # aligned, then shifted a further _PCM_WEST_SHIFT west.
    # Falls back to the top margin if this die has no bond-pad array.
    if therm_left is not None and therm_top is not None:
        add_pcm_block(
            cell, x_right=therm_left - _PCM_GAP - _PCM_WEST_SHIFT, y_top=therm_top
        )
    else:
        add_pcm_block(cell, x_right=right_inner - _PCM_WEST_SHIFT, y_top=top_inner)

    cell.cell_type = "die_assembly"
    return cell


def place_thermistance_pad(cell: fw.Component) -> None:
    """Move the scaffold's thermistance pad onto the shared hard-coded centre.

    :func:`die_scaffold` parks ``thermistance_bonding_pad`` next to the bond-pad
    array, and the PCM block anchors off that parked position -- so the pad is
    placed there first and re-placed here rather than being positioned once.
    This puts it on ``_THERMISTANCE_CENTER``, the same absolute (x, y) on every
    die, independent of the RF launch or the bond-pad array.

    A no-op on a die with no thermistance pad (one with no bond-pad array).
    """
    if "thermistance_bonding_pad" not in cell.instances:
        return
    therm = cell.instances["thermistance_bonding_pad"]
    tb = therm.bbox
    assert tb is not None  # placed instances always have geometry
    cx, cy = _THERMISTANCE_CENTER
    therm.move(cx - tb.center_x, cy - tb.center_y)


def place_thermistance_pad_west_of(
    cell: fw.Component, ref_names: Iterable[str], *, gap: float = _THERMISTANCE_GC_GAP
) -> None:
    """Re-place the thermistance pad just west of ``ref_names``, top edges aligned.

    The per-die override of :func:`place_thermistance_pad`'s shared
    ``_THERMISTANCE_CENTER``, used by R1A / R1B: those two dies carry the extra top
    modulator's open grating-coupler array in the top-right corner, and their
    thermistance pad is wanted beside it rather than on the reticle-wide centre.
    The other six dies keep the shared centre, so the pad only moves where a die
    asks for it.

    ``ref_names`` is the reference **block** -- for the GC array that is both the
    coupler row and its alignment loop, since the loop sits one pitch west of the
    row and is the block's true west edge. The pad's east edge lands ``gap`` west
    of the union's west edge and its top edge flush with the union's top, so the
    pad reads as part of the same top-edge row rather than floating below it.

    Because the pad is re-placed (``move``) rather than re-created, this must run
    **after** the referenced instances exist, and it leaves the PCM block alone:
    that anchors off the pad's original parked position back in
    :func:`die_scaffold`, not off wherever the pad ends up.

    A no-op on a die with no thermistance pad, or if none of ``ref_names`` is
    present.

    Args:
        cell: die cell carrying the pad and the reference block (mutated in place).
        ref_names: instance names whose union defines the reference block.
        gap: clearance (um) from the block's west edge to the pad's east edge.
    """
    if "thermistance_bonding_pad" not in cell.instances:
        return
    boxes = [
        b
        for b in (cell.instances[n].bbox for n in ref_names if n in cell.instances)
        if b is not None  # placed instances always have geometry
    ]
    if not boxes:
        return
    west = min(b.xmin for b in boxes)
    top = max(b.ymax for b in boxes)
    therm = cell.instances["thermistance_bonding_pad"]
    tb = therm.bbox
    assert tb is not None  # placed instances always have geometry
    therm.move((west - gap) - tb.xmax, top - tb.ymax)
