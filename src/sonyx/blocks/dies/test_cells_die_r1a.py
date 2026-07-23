"""Test cells for die R1A.

Per-die test-cell builders for die R1A, kept out of the die body so the die
builder stays a thin assembler. Each is a ``@recipe`` a caller places on the
die.

- :func:`test_waveguide_cutback_sm` — SM waveguide-loss (cutback) structure.
- :func:`test_waveguide_cutback_ull` — same structure, but the delay spirals ride
  the low-loss ULL ridge (horizontal arms) instead of the SM rib.

Both share :func:`_build_cutback`: an ext grating-coupler interface row whose two
outermost couplers form a connected loopback reference pair, plus four delay
spirals of increasing total length. The graded waveguide spans between the inner
coupler pairs land in a later step.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import picasso as fw
from luqia_ln200.cells.couplers import (
    gratingcoupler_loopback_rib_sm_800nm_ext,
    gratingcoupler_rib_sm_800nm_ext,
)
from luqia_ln200.cells.waveguides import (
    spiral_rib_sm_800nm_for_length,
    spiral_rib_ull_horizontal_800nm_for_length,
)
from picasso.leaves import make_array
from picasso.recipe import recipe

from ...parameters import parameters as _p

if TYPE_CHECKING:
    from collections.abc import Callable

# Ext-axis grating couplers along the cutback interface (one per cutback arm end).
_NUM_COUPLERS = 10

# Waveguide-loss delay spirals: four spirals of fixed loop count, total centerline
# path swept evenly from 2 cm to 10 cm (an even length lever arm for the loss fit).
# n_loops is held fixed per cell so the spirals differ only in delay.
_SPIRAL_N = 4
_SPIRAL_MIN_CM = 2.0
_SPIRAL_MAX_CM = 10.0
# SM: 16 keeps the 2 cm spiral feasible and the 10 cm one compact (~2.9 x 0.45 mm).
_SM_SPIRAL_N_LOOPS = 16
# ULL: fewer loops -- each long arm is taper -> ULL straight -> taper (30 um each),
# so short totals need longer arms; 12 keeps the 2 cm ULL spiral feasible.
_ULL_SPIRAL_N_LOOPS = 12
_SPIRAL_COL_GAP = 100.0  # um, horizontal gap between adjacent (rotated) spirals
# Gap below the coupler row. Kept small on purpose: rotated, the longest spiral is
# a few mm tall and the vertical budget down to the top modulator is limited, so
# this row sits just under the couplers. Widen it if that constraint eases.
_SPIRAL_ROW_GAP = 25.0


def _build_cutback(
    spiral_factory: Callable[..., fw.Component],
    spiral_n_loops: int,
) -> fw.Component:
    """Build a GC-cutback test cell with a given delay-spiral factory.

    Ext grating-coupler interface of ``_NUM_COUPLERS`` positions on a row at
    ``grating_coupling_pitch_for_tests`` (``gratingcoupler_rib_sm_800nm_ext``,
    facet south). The two **outermost** positions (c0 and c(N-1)) are a single
    connected :func:`gratingcoupler_loopback_rib_sm_800nm_ext` reference pair,
    spaced ``(N-1) * pitch`` apart with its connection routed behind (north of)
    the whole row (instance ``"loopback_outer"``). The inner ``N-2`` positions
    are the still-unconnected cutback couplers, tiled with ``make_array``
    (instance ``"inner"``, ports ``o1_r0_cN``).

    Below the row sit ``_SPIRAL_N`` delay spirals from
    ``spiral_factory(target_length=..., n_loops=spiral_n_loops)`` with total path
    lengths swept evenly from ``_SPIRAL_MIN_CM`` to ``_SPIRAL_MAX_CM`` cm. Each is
    rotated -90 deg so its two ports face north (up, toward the couplers), laid
    out left-to-right shortest first (instances ``"spiral_0"`` .. ``"spiral_{N-1}"``,
    ports ``o1`` / ``o2``). They connect to the inner coupler pairs in a later step.
    """
    pitch = _p.grating_coupling_pitch_for_tests.value
    n = _NUM_COUPLERS
    cell = fw.Component()

    # Inner couplers c1..c(N-2): a row shifted one pitch right of c0.
    inner = make_array(
        template=gratingcoupler_rib_sm_800nm_ext(),
        rows=1,
        cols=n - 2,
        dx=pitch,
        dy=0.0,
    )
    cell.add_placed(inner, "inner", x=pitch, y=0.0)

    # Outermost pair c0 & c(N-1): connected loopback spanning the row, routed
    # behind (north). Its gc_left lands on c0 (x=0), gc_right on c(N-1).
    pair = gratingcoupler_loopback_rib_sm_800nm_ext(spacing=(n - 1) * pitch)
    cell.add_placed(pair, "loopback_outer", x=0.0, y=0.0)

    # Delay spirals rotated -90 deg so both ports face north (up), toward the
    # inner coupler row above, and laid out left-to-right (shortest first) in a
    # row just below the couplers. A -90 deg rotation maps (x, y) -> (y, -x), so
    # the placed left edge is the cell's ymin and the placed top is -xmin. Started
    # below whatever the row already occupies so they never overlap it.
    span_cm = _SPIRAL_MAX_CM - _SPIRAL_MIN_CM
    y_top = cell.bbox.ymin - _SPIRAL_ROW_GAP
    x_cursor = 0.0
    for i in range(_SPIRAL_N):
        length_cm = _SPIRAL_MIN_CM + i * span_cm / (_SPIRAL_N - 1)
        spiral = spiral_factory(
            target_length=length_cm * 10000.0,
            n_loops=spiral_n_loops,
        )
        sb = spiral.bbox
        cell.add_placed(
            spiral,
            f"spiral_{i}",
            x=x_cursor - sb.ymin,
            y=y_top + sb.xmin,
            rotation=-90.0,
        )
        x_cursor += sb.dy + _SPIRAL_COL_GAP
    return cell


@recipe
def test_waveguide_cutback_sm() -> fw.Component:
    """SM waveguide-loss (cutback) test cell — SM-rib delay spirals.

    See :func:`_build_cutback`. Delay spirals are
    :func:`spiral_rib_sm_800nm_for_length` (``_SM_SPIRAL_N_LOOPS`` loops).
    """
    return _build_cutback(spiral_rib_sm_800nm_for_length, _SM_SPIRAL_N_LOOPS)


@recipe
def test_waveguide_cutback_ull() -> fw.Component:
    """ULL waveguide-loss (cutback) test cell — ULL-horizontal delay spirals.

    Structural twin of :func:`test_waveguide_cutback_sm`; the delay spirals are
    :func:`spiral_rib_ull_horizontal_800nm_for_length` (``_ULL_SPIRAL_N_LOOPS``
    loops), whose long horizontal arms ride the low-loss ULL ridge while ports
    stay SM.
    """
    return _build_cutback(spiral_rib_ull_horizontal_800nm_for_length, _ULL_SPIRAL_N_LOOPS)
