"""Regenerate sonyx build artifacts.

GDS only: the layout binary is the deliverable, verified numerically rather
than by rendered preview. (Netlist / DRC / design report / floorplan SVGs are
one kwarg away — drop ``gds_only=True`` below, or run the CLI without
``--gds-only`` — if you ever want them.)

Run directly::

    uv run python -m sonyx.artifacts
    # equivalently: uv run python -m picasso.layout_artifacts sonyx --gds-only

Add ``--blackbox`` to also write ``sonyx_blackbox.gds`` — the IP-protected
export, with every ``Component.blackbox``-flagged PDK device reduced to its
stub (see-through frame + scaled name + ports) while routing, bondpads,
fiducials and circuit topology stay real. The shareable deliverable for
recipients who should read the circuit, not the geometry. Once written it is
refreshed on every later run; delete the file to opt back out.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from picasso.layout_artifacts import update_layout

from . import layout

_SOURCE_DIR = Path(__file__).resolve().parent
_ARTIFACTS_DIR = _SOURCE_DIR.parents[1] / "layout_artifacts"


def update(*, blackbox: bool | None = None) -> None:
    """Rebuild the GDS under ``layout_artifacts/``.

    Wall-clock of the (build + route + write) pass is reported to stderr —
    eager autoroute front-loads the A* into the build, so this is the number
    to watch when iterating on routing.

    Args:
        blackbox: Also write the protected ``sonyx_blackbox.gds``. The
            default ``None`` is sticky — refresh it iff it already exists —
            so an opted-in checkout can't ship a stale protected GDS.
    """
    if blackbox is None:
        blackbox = (_ARTIFACTS_DIR / f"{layout.name}_blackbox.gds").exists()
    start = time.perf_counter()
    paths = update_layout(
        layout, _ARTIFACTS_DIR, source_dir=_SOURCE_DIR, gds_only=True, blackbox=blackbox
    )
    elapsed = time.perf_counter() - start
    for kind, path in paths.items():
        print(f"{kind}: {path}")
    print(f"GDS generation: {elapsed:.2f} s", file=sys.stderr)


if __name__ == "__main__":
    update(blackbox=True if "--blackbox" in sys.argv[1:] else None)
