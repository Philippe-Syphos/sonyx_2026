"""Die holders for the sonyx 2x4 reticle (``tapeout_plan_reticle_v1.md`` §2/§4.0).

Eight dies, one module each — row **R1 (top) → R4 (bottom)**, column
**A (left) / B (right)**. Each module is the full builder for its die: it
calls the shared :func:`._frame.die_scaffold` for the common placements, then
adds that die's own geometry / routing on the returned cell. The per-module
docstrings record the planned test content that fills each die later.

:data:`DIE_GRID` is the row-major placement map consumed by
:func:`sonyx.blocks.reticle.reticle`: ``DIE_GRID[row][col]`` with ``row=0`` at
the top of the reticle and ``col=0`` on the left.
"""

from __future__ import annotations

from collections.abc import Callable

import picasso as fw

from .die_r1a import die_r1a
from .die_r1b import die_r1b
from .die_r2a import die_r2a
from .die_r2b import die_r2b
from .die_r3a import die_r3a
from .die_r3b import die_r3b
from .die_r4a import die_r4a
from .die_r4b import die_r4b

# Row-major (top→bottom, left→right). Kept in lockstep with DIE_ROWS/DIE_COLUMNS.
DIE_GRID: list[list[Callable[[], fw.Component]]] = [
    [die_r1a, die_r1b],  # R1 — top
    [die_r2a, die_r2b],  # R2
    [die_r3a, die_r3b],  # R3
    [die_r4a, die_r4b],  # R4 — bottom
]

__all__ = [
    "DIE_GRID",
    "die_r1a",
    "die_r1b",
    "die_r2a",
    "die_r2b",
    "die_r3a",
    "die_r3b",
    "die_r4a",
    "die_r4b",
]
