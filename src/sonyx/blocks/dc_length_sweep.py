"""Directional-coupler coupling-length test (R4A).

Directional couplers with a swept parallel coupling length ``L`` map the
bar/cross power split ``cos^2(kappa L)`` / ``sin^2(kappa L)``, so fitting the
measured split vs. L extracts the coupling coefficient / beat length and
calibrates the coupler design. One 50/50 sweep is placed (L = 75.47 um nominal):
12 coupling lengths bracketing that nominal.

**One device per grating-coupler array.** Each DUT gets its own array of
**six** ``gratingcoupler_rib_sm_800nm_ext`` couplers -- two form the left
alignment loopback (``gratingcoupler_alignment_rib_sm_800nm_ext``, an insertion-loss
reference) and the remaining **four** front the DUT's four ports: ``o1``/``o2``
(the two west inputs) and ``o3``/``o4`` (bar/cross, the two east outputs). Every
port radiates into its own fibre grating, so there is **no beam dump** -- the old
spare-input dump is gone now that ``o1`` has a coupler of its own. Each DUT is the
PDK 50/50 DC cell (``directionalcoupler_rib_sm_800nm_ord_50_50``) with the
surfaced ``coupling_length`` overridden per instance -- the gap stays at the PDK
design point, and the PDK cell carries the blackbox flag.

The 12 arrays tile a **4-row x 3-column grid** (:func:`_grid_cells`): the couplers
of an array sit on the continuous ``grating_coupling_pitch_for_tests`` grid
(alignment loopback then the four device couplers), and columns step by one whole
:func:`group_pitch` so the grid stays unbroken across a row (see
:func:`block_x_base`). Rows drop by :data:`_ROW_DROP`.

Per array the four device couplers face **south** and the DUT sits
:data:`_GC_TO_DC_GAP` below them; the two west ports route up to the two west
couplers and the two east ports up to the two east couplers, one bundle per side
(:func:`_route_array`). A block is therefore two passes -- :func:`place_grid`
then :func:`route_grid` -- taking the same ``lengths`` / prefixes.

The whole sweep is one self-contained Component (:func:`dc_length_sweep_block`)
built in its own local frame -- origin at the block's top-left content anchor
(row 0, column 0 alignment-loop west edge, GC/loop tops line). The die
(``dies/die_r4a.py``) places it with ``add_placed`` at :func:`block_x_base`
(block 0), which keeps the whole R4A top band's couplers on one grating grid.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import picasso as fw
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from luqia_ln200.cells.labels import label_moat_labels
from luqia_ln200.cells.splitters import (
    directionalcoupler_rib_sm_800nm_ord_50_50,
)
from picasso.leaves import make_array
from picasso.recipe import recipe

from ..parameters import parameters as _p

# Swept parallel coupling lengths (um) for the 50/50 coupler (nominal
# L = 75.47 um). 12 lengths, 10 -> 120 um, bracketing the nominal and reaching
# well past it toward the full-cross point (L = 150.94 um). Laid out row-major on
# a _NUM_ROWS x _NUM_COLS grid of one-device arrays (:func:`_grid_cells`).
_LENGTHS: tuple[float, ...] = (
    10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 120.0
)

# One device per array; its four ports each front a grating coupler.
_GC_PER_DC = 4  # o1, o2 (west inputs) + o3, o4 (bar/cross east outputs)
_PER_GROUP = 1  # devices per side-by-side array (one array = one DUT)
# Grating couplers in an array's alignment loopback (a 2-coupler U-turn, itself on
# the grating pitch) -- counted so the array pitch keeps the whole row on grid.
# Array total = _ALIGN_GC + _GC_PER_DC * _PER_GROUP = 6 couplers.
_ALIGN_GC = 2

# The four device couplers c0..c3 (west to east), and which DUT port each fronts.
# West couplers take the two west ports (o2 upper, o1 lower); east couplers take
# the two east ports (o4 lower, o3 upper) -- a mirror pairing that fans up to the
# coupler row without the two sides crossing (:func:`_route_array`).
_WEST_PORTS = ("o2", "o1")  # -> c0, c1
_EAST_PORTS = ("o4", "o3")  # -> c2, c3

# Grid shape: 12 one-device arrays as _NUM_ROWS rows of _NUM_COLS columns.
_NUM_COLS = 3  # arrays per row
_NUM_ROWS = 4  # rows

# Layout (um).
_LEFT_MARGIN = 1750.0  # die-level: block 0's left edge off the left inner edge
_GC_TO_DC_GAP = 60.0  # array bottom (alignment-loop bottom) down to the device top
_ROW_DROP = 320.0  # vertical drop from one row's tops line to the next below it

# Coupling-length label drawn as polygons (WG_RIB) below each device -- visible in
# any GDS viewer and on the mask, not a viewer-only annotation.
_LABEL_HEIGHT = 15.0  # glyph height (um)
_LABEL_GAP = 15.0  # gap (um) from the device's south edge down to the label's top


def _dc_dut(coupling_length: float) -> fw.Component:
    """The PDK 50/50 DC at the given coupling length; ports ``o1``-``o4``."""
    return directionalcoupler_rib_sm_800nm_ord_50_50(coupling_length=coupling_length)


@recipe
def _gc_line(num: int) -> fw.Component:
    """A row of ``num`` N-S grating couplers at ``grating_coupling_pitch_for_tests``."""
    return make_array(
        template=gratingcoupler_rib_sm_800nm_ext(),
        rows=1,
        cols=num,
        dx=_p.grating_coupling_pitch_for_tests.value,
        dy=0.0,
    )


def group_gc_width() -> float:
    """Horizontal extent (um) of one array's GC row (loop + pitch gap + couplers)."""
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    lb = gratingcoupler_alignment_rib_sm_800nm_ext().bbox
    return lb.dx + (pitch - gc_w) + _gc_line(_GC_PER_DC * _PER_GROUP).bbox.dx


def group_pitch() -> float:
    """Array-to-array (column) x pitch (um) -- a whole number of grating pitches.

    An array's couplers form an unbroken pitch chain: ``_ALIGN_GC`` in the alignment
    loopback then ``_GC_PER_DC * _PER_GROUP`` device couplers. Stepping the next
    column by exactly that many pitches continues the chain across the column
    boundary instead of leaving an arbitrary gap, so **every** coupler in a row --
    both blocks, loopbacks included -- lands on one grid and a fibre array steps it
    uniformly.
    """
    per_group = _ALIGN_GC + _GC_PER_DC * _PER_GROUP
    return per_group * _p.grating_coupling_pitch_for_tests.value


def block_x_base(block_index: int) -> float:
    """Left edge (um) of sweep block ``block_index``, in the die frame.

    The die-level ``add_placed`` x anchor: block ``0`` is the single-DC sweep
    (:func:`dc_length_sweep_block`), block ``1`` the back-to-back-MZI sweep
    (:func:`~sonyx.blocks.dc_mzi_length_sweep.dc_mzi_length_sweep_block`). Blocks
    tile west to east at ``_NUM_COLS`` whole :func:`group_pitch` steps, which is
    what keeps the grating grid continuous *between* blocks as well as within them
    -- so the MZI block's position is derived here rather than carrying its own
    margin (an independent margin silently drifts off the grid).
    """
    half_w = _p.die_width.value / 2.0
    x0 = (-half_w + _p.keepout_width.value) + _LEFT_MARGIN
    return x0 + block_index * _NUM_COLS * group_pitch()


def _grid_cells(lengths: tuple[float, ...]) -> Iterator[tuple[float, int, int, str]]:
    """Yield ``(length, row, col, tag)`` for each one-device array, row-major.

    The block's whole sweep fills a ``_NUM_ROWS x _NUM_COLS`` grid: the first
    ``_NUM_COLS`` lengths on row 0 (top), the next on row 1, and so on. ``tag`` =
    ``r{row}c{col}`` names the array's couplers uniquely. One source of truth for
    the grid, shared by :func:`place_grid` and :func:`route_grid` so placement and
    routing can never drift apart.
    """
    for i, length in enumerate(lengths):
        row, col = divmod(i, _NUM_COLS)
        yield length, row, col, f"r{row}c{col}"


def _add_array(
    cell: fw.Component, x_left: float, y_top: float, length: float, tag: str, *,
    dut_factory: Callable[[float], fw.Component] = _dc_dut,
    gc_prefix: str = "dc_gc", dut_prefix: str = "dc_len",
) -> None:
    """Place one array: alignment loop + four device couplers (north), one DUT below.

    The alignment loop's left edge sits at ``x_left``; loop/couplers tops at
    ``y_top``. The array's first coupler continues the loopback's pitch chain, so the
    array is one unbroken grating grid. The single DUT (from ``dut_factory``) is
    centred in x on the four-coupler row and hangs ``_GC_TO_DC_GAP`` below the
    (taller) alignment loop's bottom, with a polygon-drawn ``L{length}`` coupling-
    length label centred below it. Instances ``{gc_prefix}_align_{tag}`` /
    ``{gc_prefix}_array_{tag}`` / ``{dut_prefix}_{L}`` / ``{dut_prefix}_label_{tag}``
    -- prefixes keep the two sibling blocks distinct on one die.
    """
    pitch = _p.grating_coupling_pitch_for_tests.value
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(loop, name=f"{gc_prefix}_align_{tag}", x=x_left - lb.xmin, y=y_top - lb.ymax)
    arr = _gc_line(_GC_PER_DC * _PER_GROUP)
    ab = arr.bbox
    array_x = (x_left + lb.dx) + (pitch - gc_w) - ab.xmin  # placement offset
    cell.add_placed(arr, name=f"{gc_prefix}_array_{tag}", x=array_x, y=y_top - ab.ymax)
    array_center_x = array_x + ab.center_x
    dut = dut_factory(length)
    y_dut_top = (y_top - lb.dy) - _GC_TO_DC_GAP
    cell.add_placed(
        dut, name=f"{dut_prefix}_{length:g}",
        x=array_center_x - dut.bbox.center_x, y=y_dut_top - dut.bbox.ymax,
    )
    # Coupling-length label, drawn as polygons, centred in the free band below the
    # device (its top _LABEL_GAP under the device's south edge).
    label = label_moat_labels(text=f"L{length:g}", height=_LABEL_HEIGHT, valign="bottom")
    lab_bb = label.bbox
    cell.add_placed(
        label, name=f"{dut_prefix}_label_{tag}",
        x=array_center_x - lab_bb.center_x,
        y=((y_dut_top - dut.bbox.dy) - _LABEL_GAP) - lab_bb.ymax,
    )


def place_grid(
    cell: fw.Component, *, lengths: tuple[float, ...], x_base: float = 0.0,
    y_top: float = 0.0, dut_factory: Callable[[float], fw.Component] = _dc_dut,
    gc_prefix: str = "dc_gc", dut_prefix: str = "dc_len",
) -> None:
    """Place a sweep as a ``_NUM_ROWS x _NUM_COLS`` grid of one-device arrays.

    Anchored at (x_base, y_top) = the top-left array's alignment-loop west edge /
    tops line. Columns step by one :func:`group_pitch` (continuing the grating grid
    across the column boundary); rows drop by :data:`_ROW_DROP`. Shared by the
    single-DC and back-to-back-MZI blocks.
    """
    step = group_pitch()
    for length, row, col, tag in _grid_cells(lengths):
        _add_array(
            cell, x_base + col * step, y_top - row * _ROW_DROP, length, tag,
            dut_factory=dut_factory, gc_prefix=gc_prefix, dut_prefix=dut_prefix,
        )


def _route_array(
    cell: fw.Component, length: float, tag: str, *,
    gc_prefix: str = "dc_gc", dut_prefix: str = "dc_len",
    strategy: str = "vgraph_rect",
) -> None:
    """Route one array's DUT ports to its four device couplers -- two bundles.

    The four couplers face **south** and the DUT sits below them; the two west
    ports (``o2`` upper, ``o1`` lower) fan up to the two west couplers ``c0``/``c1``
    (:data:`_WEST_PORTS`) and the two east ports (``o4`` lower, ``o3`` upper) up to
    the two east couplers ``c2``/``c3`` (:data:`_EAST_PORTS`). One ``autoroute``
    bundle per side keeps each pair crossing-free, and the two sides leave the DUT
    on opposite edges so they share no corridor. ``vgraph_rect`` is the default
    planner (see :func:`route_grid`): the arrays pack tightly on the grid and the
    bundles become each other's obstacles, which ``grid_astar`` cannot plan. The
    back-to-back-MZI DUTs are ~2x wider than a single DC, so their east ports also
    sit well east of the array and reverse westward to ``c2``/``c3``.
    """
    dut = f"{dut_prefix}_{length:g}"
    arr = f"{gc_prefix}_array_{tag}"
    cell.autoroute(
        ports_a=[(dut, _WEST_PORTS[0]), (dut, _WEST_PORTS[1])],
        ports_b=[(arr, "o1_r0_c0"), (arr, "o1_r0_c1")],
        spec="routing_sm_tight", strategy=strategy, start_straight=30.0,
        name=f"{dut_prefix}_w_{tag}",
    )
    cell.autoroute(
        ports_a=[(dut, _EAST_PORTS[0]), (dut, _EAST_PORTS[1])],
        ports_b=[(arr, "o1_r0_c2"), (arr, "o1_r0_c3")],
        spec="routing_sm_tight", strategy=strategy, start_straight=30.0,
        name=f"{dut_prefix}_e_{tag}",
    )


def route_grid(
    cell: fw.Component, *, lengths: tuple[float, ...],
    gc_prefix: str = "dc_gc", dut_prefix: str = "dc_len",
    strategy: str = "vgraph_rect",
) -> None:
    """Route every array of the grid: a west bundle and an east bundle per DUT.

    The routing counterpart of :func:`place_grid` -- same ``lengths`` / ``gc_prefix``
    / ``dut_prefix`` and the same :func:`_grid_cells`, so a block is placed and
    routed with a matching pair of calls. ``strategy`` defaults to ``vgraph_rect``,
    which plans both blocks' packed grids cleanly; ``grid_astar`` cannot -- the
    arrays sit close together and the per-array bundles become mutual obstacles.
    """
    for length, _row, _col, tag in _grid_cells(lengths):
        _route_array(
            cell, length, tag, gc_prefix=gc_prefix, dut_prefix=dut_prefix,
            strategy=strategy,
        )


@recipe
def dc_length_sweep_block() -> fw.Component:
    """The single-DC coupling-length sweep as one self-contained block.

    Local frame: x = 0 on the row 0 / column 0 alignment-loop west edge, y = 0 on
    the GC/loop tops line. The die places this at :func:`block_x_base` (block 0).

    One 50/50 sweep (``_LENGTHS``, 12 lengths) as a 4-row x 3-column grid of
    one-device arrays (:func:`place_grid`): each DUT under its own six-coupler array
    (two alignment + four device), fully routed by :func:`route_grid` -- no beam
    dumps, since every port now fronts a coupler. Instances ``dc_gc_*`` / ``dc_len_*``.
    """
    cell = fw.Component()
    place_grid(cell, lengths=_LENGTHS)
    route_grid(cell, lengths=_LENGTHS)
    cell.cell_type = "test_structure"
    cell.description = (
        "Directional-coupler coupling-length sweep test block: 12 single 50/50 DCs, "
        "one device per six-coupler array (2 alignment + 4 device) on a 4x3 grid, "
        "GC fibre I/O on all four ports, fully wired."
    )
    return cell
