"""Test cells for die R1A.

Per-die test-cell builders for die R1A, kept out of the die body so the die
builder stays a thin assembler. Each is a ``@recipe`` a caller places on the
die.

- :func:`test_waveguide_cutback_sm` — SM waveguide-loss (cutback) structure.
- :func:`test_waveguide_cutback_ull` — same structure, but the delay spirals ride
  the low-loss ULL ridge (horizontal arms) instead of the SM rib.

Both share :func:`_build_cutback`: an ext grating-coupler array on top of a
vertical stack of four horizontal delay spirals of increasing total length. The
graded waveguide spans between the couplers and the spiral ports land in a later
step.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import picasso as fw
from luqia_ln200.cells.couplers import (
    gratingcoupler_alignment_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from luqia_ln200.cells.waveguides import (
    spiral_rib_sm_800nm,
    spiral_rib_ssm_800nm,
    spiral_rib_ull_horizontal_800nm,
    taper_rib_sm_to_ssm_linear_800nm,
)
from picasso.leaves import make_array
from picasso.recipe import recipe

from ...parameters import parameters as _p

if TYPE_CHECKING:
    from collections.abc import Callable

# Waveguide-loss delay spirals: four spirals of fixed loop count, total centerline
# path swept evenly from 2 cm to 10 cm (an even length lever arm for the loss fit).
# n_loops is held fixed per cell so the spirals differ only in delay.
_SPIRAL_N = 4
_SPIRAL_MIN_CM = 2.0
_SPIRAL_MAX_CM = 10.0
# All three flavours run the same loop count so the cells stay structural twins.
# Loop count only sets the spiral's aspect ratio -- the factories solve for the
# requested ``target_length``, so the swept total path lengths (2 -> 10 cm) are
# unchanged; 8 loops just makes each spiral wider and shorter than 10/12 did.
_SM_SPIRAL_N_LOOPS = 8
_ULL_SPIRAL_N_LOOPS = 8
_SSM_SPIRAL_N_LOOPS = 8
_SPIRAL_STACK_GAP = 20.0  # um, vertical gap between adjacent stacked spirals
_COUPLER_ROW_GAP = 100.0  # um, base gap between the coupler array and the spiral stack
_SPIRAL_DROP = 40.0  # um, extra downward shift of the spiral stack (widens the coupler gap)
# x of the (west-facing) spiral ports -- every spiral in the stack is aligned on
# this line, so the coupler-to-spiral routing is identical for every length.
_SPIRAL_PORT_X = 200.0
# um, gap from the coupler array's east-most port to the spiral port line.
_GC_TO_SPIRAL_PORT_GAP = 100.0
# The couplers' cross-section: a spiral not already on it gets a width taper so
# the coupler bundle stays a single-cross-section route.
_SM_XS = "rib_sm_800nm"


def _build_cutback(
    spiral_factory: Callable[..., fw.Component],
    spiral_n_loops: int,
    reverse: bool = False,
    extra_coupler_gap: float = 0.0,
) -> fw.Component:
    """Build a GC-cutback test cell with a given delay-spiral factory.

    ``_SPIRAL_N`` delay spirals from ``spiral_factory(target_length=...,
    n_loops=spiral_n_loops)``, with total path lengths swept evenly from
    ``_SPIRAL_MIN_CM`` to ``_SPIRAL_MAX_CM`` cm, are laid **horizontally** and
    stacked **vertically**, left-aligned, ``_SPIRAL_STACK_GAP`` apart (instances
    ``"spiral_0"`` (shortest) .. ``"spiral_{N-1}"`` (longest), ports ``o1`` /
    ``o2``). ``reverse=False`` puts the shortest at the top; ``reverse=True`` puts
    the longest at the top (used by the ULL twin so it imbricates with the SM
    cell -- shortest-SM facing longest-ULL).

    A horizontal ext grating-coupler array (``gratingcoupler_rib_sm_800nm_ext``,
    facet south, ``2 * _SPIRAL_N`` couplers at ``grating_coupling_pitch_for_tests``)
    sits **on top** of the spiral stack (instance ``"couplers"``, ports
    ``o1_r0_cN``), ``_COUPLER_ROW_GAP`` above it. A grating-coupler alignment loop
    (:func:`~luqia_ln200.cells.couplers.gratingcoupler_alignment_rib_sm_800nm_ext`)
    sits one pitch to the **left** of the array, GC tops on the same line so it
    continues the array's constant pitch (instance ``"gc_align"``). The couplers
    connect to the spiral ports in a later step.
    """
    pitch = _p.grating_coupling_pitch_for_tests.value
    cell = fw.Component()

    # Delay spirals: horizontal, stacked vertically, **port-aligned** -- every
    # spiral's (west-facing) o1 sits on x=_SPIRAL_PORT_X, _SPIRAL_STACK_GAP apart.
    # Aligning on the ports rather than the bboxes keeps the coupler-to-spiral
    # routing identical across lengths (the bodies, whose width grows as the
    # spiral shortens, then extend east by varying amounts).
    # The top spiral's top edge is y=0; the stack grows downward. spiral_i keeps
    # its length identity (i=0 shortest .. N-1 longest); `order` sets top->bottom
    # (shortest-first normally, longest-first when reversed).
    span_cm = _SPIRAL_MAX_CM - _SPIRAL_MIN_CM
    order = list(range(_SPIRAL_N - 1, -1, -1) if reverse else range(_SPIRAL_N))
    # Top spiral's top edge starts _SPIRAL_DROP below y=0 (the couplers sit above
    # y=0), so the couplers-to-spirals gap is _COUPLER_ROW_GAP + _SPIRAL_DROP.
    y_cursor = -_SPIRAL_DROP  # top edge of the next spiral
    for idx in order:
        length_cm = _SPIRAL_MIN_CM + idx * span_cm / (_SPIRAL_N - 1)
        spiral = spiral_factory(target_length=length_cm * 10000.0, n_loops=spiral_n_loops)
        sb = spiral.bbox
        port_x = spiral.ports["o1"].position[0]
        cell.add_placed(
            spiral, name=f"spiral_{idx}", x=_SPIRAL_PORT_X - port_x, y=y_cursor - sb.ymax
        )
        y_cursor -= sb.dy + _SPIRAL_STACK_GAP

    # Grating-coupler array (horizontal row, facet south) on top of the stack,
    # placed so its **east-most** coupler port sits _GC_TO_SPIRAL_PORT_GAP west
    # of the spiral port line (the array therefore runs west from there).
    cols = 2 * _SPIRAL_N
    arr = make_array(
        template=gratingcoupler_rib_sm_800nm_ext(),
        rows=1,
        cols=cols,
        dx=pitch,
        dy=0.0,
    )
    # Coupler row raised ``extra_coupler_gap`` above its base position (the spirals
    # stay put), so the couplers-to-spirals spacing widens without moving spirals.
    coupler_gap = _COUPLER_ROW_GAP + extra_coupler_gap
    ab = arr.bbox
    east_port_x = arr.ports[f"o1_r0_c{cols - 1}"].position[0]
    x_arr = (_SPIRAL_PORT_X - _GC_TO_SPIRAL_PORT_GAP) - east_port_x
    cell.add_placed(arr, name="couplers", x=x_arr, y=coupler_gap - ab.ymin)
    array_left = x_arr + ab.xmin

    # Grating-coupler alignment loop one pitch to the left of the array, GC tops
    # on the same line (align bbox tops) so it continues the array's pitch.
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(
        loop,
        name="gc_align",
        x=(array_left - (pitch - gc_w)) - lb.xmax,
        y=(coupler_gap + ab.dy) - lb.ymax,
    )

    # Route endpoints, one per spiral end. The couplers are on ``rib_sm_800nm``, so
    # a spiral whose ports are on another cross-section (the SSM spirals -- the SM
    # and ULL ones already present SM ports) gets a PDK width taper mated to each
    # port, and the taper's SM side becomes the endpoint. Without it the bundle is
    # a mixed-cross-section route, which cannot take the spec's single bend
    # template. Both tapers are identical on every spiral, so the extra loss is
    # common-mode and lands in the cutback intercept, not the slope.
    route_ends: list[tuple[float, tuple[str, str]]] = []
    for i in range(_SPIRAL_N):
        sname = f"spiral_{i}"
        for p in ("o1", "o2"):
            port = cell.instances[sname].ports[p]
            if port.cross_section is not None and port.cross_section.name == _SM_XS:
                route_ends.append((port.position[1], (sname, p)))
                continue
            taper = cell.put(
                taper_rib_sm_to_ssm_linear_800nm(),
                (sname, p),
                port_to="o2",  # SSM side mates the spiral; o1 (SM) faces west
                name=f"{sname}_taper_{p}",
            )
            route_ends.append((taper.ports["o1"].position[1], (taper.name, "o1")))

    # Wire every spiral end to a coupler in ONE bundle (default SM routing). Every
    # endpoint faces west and every coupler port faces south, so all 2N lanes
    # share a heading at each end and the bundle is legal.
    #
    # Lane order is what keeps them from crossing: the routes run west out of the
    # spiral port line and then turn north into the couplers, so the *lowest*
    # endpoint must take the *westmost* coupler (it travels along the bottom and
    # turns up last). Sorting by actual y gives that, and it stays correct
    # whichever way ``reverse`` stacked the spirals. Each spiral's o1/o2 land on an
    # adjacent coupler pair.
    route_ends.sort()  # bottom-up
    cell.autoroute(
        ports_a=[spec for _, spec in route_ends],
        ports_b=[("couplers", f"o1_r0_c{j}") for j in range(cols)],  # west-to-east
        spec="routing_sm_default",
        name="spiral_gc_routes",
    )
    return cell


@recipe
def test_waveguide_cutback_sm(extra_coupler_gap: float = 0.0) -> fw.Component:
    """SM waveguide-loss (cutback) test cell — SM-rib delay spirals.

    See :func:`_build_cutback`. Delay spirals are
    :func:`spiral_rib_sm_800nm` (``_SM_SPIRAL_N_LOOPS`` loops).
    ``extra_coupler_gap`` raises the coupler row (spirals unchanged) -- used on
    R3A to lift the SM grating array onto the ULL array's line while the SM
    spirals stay interleaved below. Built with ``reverse=True`` (longest spiral
    at the top), matching the ULL and SSM twins.
    """
    return _build_cutback(
        spiral_rib_sm_800nm,
        _SM_SPIRAL_N_LOOPS,
        reverse=True,
        extra_coupler_gap=extra_coupler_gap,
    )


@recipe
def test_waveguide_cutback_ull() -> fw.Component:
    """ULL waveguide-loss (cutback) test cell — ULL-horizontal delay spirals.

    Structural twin of :func:`test_waveguide_cutback_sm`; the delay spirals are
    :func:`spiral_rib_ull_horizontal_800nm` (``_ULL_SPIRAL_N_LOOPS``
    loops), whose long horizontal arms ride the low-loss ULL ridge while ports
    stay SM. Built with ``reverse=True`` (longest spiral at the top) so that,
    placed mirrored on the right of the SM cell, the two imbricate.
    """
    return _build_cutback(
        spiral_rib_ull_horizontal_800nm, _ULL_SPIRAL_N_LOOPS, reverse=True
    )


@recipe
def test_waveguide_cutback_ssm() -> fw.Component:
    """SSM (super-single-mode) waveguide-loss (cutback) test cell.

    Structural twin of :func:`test_waveguide_cutback_sm`; the delay spirals are
    :func:`spiral_rib_ssm_800nm` (``_SSM_SPIRAL_N_LOOPS`` loops) on the
    weakly-confined SSM ridge. Built with ``reverse=True`` (longest spiral at the
    top -> short at the bottom, long at the top -- inverted in y vs the SM cell).
    """
    return _build_cutback(
        spiral_rib_ssm_800nm, _SSM_SPIRAL_N_LOOPS, reverse=True
    )


# Clearance (um) between the SM and ULL cutback geometries when imbricated.
_IMBRICATE_MARGIN = 40.0


def imbricated_ull_offset(
    sm: fw.Component, ull: fw.Component, margin: float = _IMBRICATE_MARGIN
) -> tuple[float, float]:
    """``(dx, dy)`` to nest the x-flipped ULL cutback against the SM cutback.

    The ULL cell is meant to be placed **x-flipped** (``mirror=True,
    rotation=180``: spirals extend left, couplers / alignment loop on the right)
    and translated by ``(Xsm + dx, Ysm + dy)``, where ``(Xsm, Ysm)`` is the SM
    cell's own placement offset. ``dy = 0`` aligns the spiral tops (shortest-SM
    facing longest-ULL); ``dx`` is the smallest rightward shift that keeps every
    x-flipped ULL sub-cell clear of every SM sub-cell by ``margin`` among
    vertically-overlapping pairs -- so the two triangular spiral profiles
    imbricate without touching. The result depends only on the two cells'
    geometry (not on ``Xsm`` / ``Ysm``).
    """
    def boxes(cell: fw.Component, xflip: bool) -> list[tuple[float, float, float, float]]:
        out: list[tuple[float, float, float, float]] = []
        for inst in cell.instances.values():
            b = inst.bbox
            assert b is not None  # placed instances always have geometry
            if xflip:
                out.append((-b.xmax, -b.xmin, b.ymin, b.ymax))
            else:
                out.append((b.xmin, b.xmax, b.ymin, b.ymax))
        return out

    sm_boxes = boxes(sm, xflip=False)
    ull_boxes = boxes(ull, xflip=True)
    dy = 0.0
    dx = max(
        sb[1] + margin - ub[0]
        for ub in ull_boxes
        for sb in sm_boxes
        if not (ub[3] + dy <= sb[2] or sb[3] <= ub[2] + dy)  # vertical overlap
    )
    return dx, dy


# Standard cutback placement, shared by every die that carries a single
# waveguide-loss cutback: **upright** in the clear top band (coupler array +
# alignment loop on the left, spirals extending east with their ports facing
# west), right edge held _CUTBACK_RIGHT_MARGIN off the die right inner edge,
# coupler tops on the common line one alignment-loop below the top inner edge.
_CUTBACK_RIGHT_MARGIN = 250.0
_CUTBACK_COUPLER_LINE = 70.0  # coupler-tops line offset above (top_inner - corner_loop_dy)


def place_cutback_top_right(cell: fw.Component, cutback: fw.Component, name: str) -> None:
    """Place ``cutback`` upright in the top-right band (see the constants above).

    Uniform placement for a die's single waveguide-loss cutback: no mirror /
    rotation, so the spiral ports face **west** toward the coupler array on the
    left and the spiral bodies extend east. The block's right edge sits
    ``_CUTBACK_RIGHT_MARGIN`` off the right inner edge, coupler tops on the
    shared ``_CUTBACK_COUPLER_LINE`` (same slot as the upright SSM cell on R3B).
    """
    half_h = _p.die_height.value / 2.0
    right_inner = _p.die_width.value / 2.0 - _p.keepout_width.value
    top_inner = half_h - _p.keepout_width.value
    corner_loop_dy = gratingcoupler_alignment_rib_sm_800nm_ext().bbox.dy
    y_couplers = top_inner - corner_loop_dy + _CUTBACK_COUPLER_LINE
    b = cutback.bbox
    cell.add_placed(
        cutback,
        name=name,
        x=(right_inner - _CUTBACK_RIGHT_MARGIN) - b.xmax,
        y=y_couplers - b.ymax,
    )
