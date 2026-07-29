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
    spiral_rib_sm_800nm_for_length,
    spiral_rib_ssm_800nm_for_length,
    spiral_rib_ull_horizontal_800nm_for_length,
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
# SM: 10 loops -> each spiral is long and thin (the 10 cm spiral is ~4.5 x 0.33 mm),
# so the vertical stack of four stays compact (~1.4 mm tall).
_SM_SPIRAL_N_LOOPS = 10
# ULL: fewer loops -- each long arm is taper -> ULL straight -> taper (30 um each),
# so short totals need longer arms; 12 keeps the 2 cm ULL spiral feasible.
_ULL_SPIRAL_N_LOOPS = 12
# SSM: super-single-mode; matches the SM loop count so the two share a length
# lever arm (the gentler SSM bend just makes each spiral a touch larger).
_SSM_SPIRAL_N_LOOPS = 10
_SPIRAL_STACK_GAP = 20.0  # um, vertical gap between adjacent stacked spirals
_COUPLER_ROW_GAP = 100.0  # um, base gap between the coupler array and the spiral stack
_SPIRAL_DROP = 40.0  # um, extra downward shift of the spiral stack (widens the coupler gap)
_SPIRAL_X_OFFSET = 200.0  # um, x-shift of the spiral stack relative to the gratings


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

    # Delay spirals: horizontal, stacked vertically, left edges aligned at
    # x=_SPIRAL_X_OFFSET (shifted right of the gratings), _SPIRAL_STACK_GAP apart.
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
        cell.add_placed(
            spiral, name=f"spiral_{idx}", x=_SPIRAL_X_OFFSET - sb.xmin, y=y_cursor - sb.ymax
        )
        y_cursor -= sb.dy + _SPIRAL_STACK_GAP

    # Grating-coupler array (horizontal row, facet south) on top of the stack.
    arr = make_array(
        template=gratingcoupler_rib_sm_800nm_ext(),
        rows=1,
        cols=2 * _SPIRAL_N,
        dx=pitch,
        dy=0.0,
    )
    # Coupler row raised ``extra_coupler_gap`` above its base position (the spirals
    # stay put), so the couplers-to-spirals spacing widens without moving spirals.
    coupler_gap = _COUPLER_ROW_GAP + extra_coupler_gap
    ab = arr.bbox
    cell.add_placed(arr, name="couplers", x=-ab.xmin, y=coupler_gap - ab.ymin)
    # The placed array's left edge is at x=0, top at coupler_gap + ab.dy.

    # Grating-coupler alignment loop one pitch to the left of the array, GC tops
    # on the same line (align bbox tops) so it continues the array's pitch.
    gc_w = gratingcoupler_rib_sm_800nm_ext().bbox.dx
    loop = gratingcoupler_alignment_rib_sm_800nm_ext()
    lb = loop.bbox
    cell.add_placed(
        loop,
        name="gc_align",
        x=-(pitch - gc_w) - lb.xmax,
        y=(coupler_gap + ab.dy) - lb.ymax,
    )
    return cell


@recipe
def test_waveguide_cutback_sm(extra_coupler_gap: float = 0.0) -> fw.Component:
    """SM waveguide-loss (cutback) test cell — SM-rib delay spirals.

    See :func:`_build_cutback`. Delay spirals are
    :func:`spiral_rib_sm_800nm_for_length` (``_SM_SPIRAL_N_LOOPS`` loops).
    ``extra_coupler_gap`` raises the coupler row (spirals unchanged) -- used on
    R3A to lift the SM grating array onto the ULL array's line while the SM
    spirals stay interleaved below.
    """
    return _build_cutback(
        spiral_rib_sm_800nm_for_length, _SM_SPIRAL_N_LOOPS, extra_coupler_gap=extra_coupler_gap
    )


@recipe
def test_waveguide_cutback_ull() -> fw.Component:
    """ULL waveguide-loss (cutback) test cell — ULL-horizontal delay spirals.

    Structural twin of :func:`test_waveguide_cutback_sm`; the delay spirals are
    :func:`spiral_rib_ull_horizontal_800nm_for_length` (``_ULL_SPIRAL_N_LOOPS``
    loops), whose long horizontal arms ride the low-loss ULL ridge while ports
    stay SM. Built with ``reverse=True`` (longest spiral at the top) so that,
    placed mirrored on the right of the SM cell, the two imbricate.
    """
    return _build_cutback(
        spiral_rib_ull_horizontal_800nm_for_length, _ULL_SPIRAL_N_LOOPS, reverse=True
    )


@recipe
def test_waveguide_cutback_ssm() -> fw.Component:
    """SSM (super-single-mode) waveguide-loss (cutback) test cell.

    Structural twin of :func:`test_waveguide_cutback_sm`; the delay spirals are
    :func:`spiral_rib_ssm_800nm_for_length` (``_SSM_SPIRAL_N_LOOPS`` loops) on the
    weakly-confined SSM ridge. Built with ``reverse=True`` (longest spiral at the
    top -> short at the bottom, long at the top -- inverted in y vs the SM cell).
    """
    return _build_cutback(
        spiral_rib_ssm_800nm_for_length, _SSM_SPIRAL_N_LOOPS, reverse=True
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


# Standard cutback placement (the ULL-on-R3A convention, now shared by every die
# that carries a single waveguide-loss cutback): x-flipped in the clear top band
# (spirals extend left, coupler array + alignment loop on the right), right edge
# held _CUTBACK_RIGHT_MARGIN off the die right inner edge, coupler tops on the
# common line one alignment-loop below the top inner edge.
_CUTBACK_RIGHT_MARGIN = 250.0
_CUTBACK_COUPLER_LINE = 70.0  # coupler-tops line offset above (top_inner - corner_loop_dy)


def place_cutback_top_right(cell: fw.Component, cutback: fw.Component, name: str) -> None:
    """Place ``cutback`` x-flipped in the top-right band (see the constants above).

    Uniform placement for a die's single waveguide-loss cutback: ``mirror=True,
    rotation=180`` so the spirals extend left and the coupler array + alignment
    loop sit on the right, the block's right edge ``_CUTBACK_RIGHT_MARGIN`` off
    the right inner edge, coupler tops on the shared ``_CUTBACK_COUPLER_LINE``.
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
        x=(right_inner - _CUTBACK_RIGHT_MARGIN) + b.xmin,
        y=y_couplers - b.ymax,
        mirror=True,
        rotation=180.0,
    )
