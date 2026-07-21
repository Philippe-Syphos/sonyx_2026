"""Top-level chip assembly for sonyx — the ``build()`` entry point.

The full-reticle top cell is assembled in ``blocks/reticle.py`` (the 22x22 mm
2x4 die shuttle); this module is the thin ``Layout(build=...)`` adapter that
returns it. Die holders live in ``blocks/dies/``, pinned geometry in
``parameters.py``.
"""

from __future__ import annotations

import picasso as fw

from .blocks.reticle import reticle


def build(layout: fw.Layout) -> fw.Component:
    """Compose and return the top-level chip Component (the full reticle).

    The target PDK (luqia_ln200) is active for the duration of this call, so
    string-keyed cells / cross-sections / layers resolve.

    Args:
        layout: The owning :class:`~picasso.layout.Layout`. Used to stamp the
            declared design knobs (from ``knobs.py``) onto the top cell.

    Returns:
        The top-level :class:`~picasso.component.Component`.
    """
    top = reticle()
    layout.stamp_knobs(top)  # no knobs yet; harmless, and ready for later refs
    return top
