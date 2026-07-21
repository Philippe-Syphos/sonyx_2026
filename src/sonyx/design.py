"""Top-level chip assembly for sonyx — the ``build()`` entry point.

Knobs live in ``knobs.py``, the die frame in ``floorplan.py``, reusable
sub-circuits in ``blocks/``. This module owns the one-off top-level
composition.
"""

from __future__ import annotations

import picasso as fw


def build(layout: fw.Layout) -> fw.Component:
    """Compose and return the top-level chip Component.

    The target PDK (luqia_ln200) is active for the duration of this call, so
    string-keyed cells / cross-sections / layers resolve.

    Args:
        layout: The owning :class:`~picasso.layout.Layout`. Use it to stamp
            the declared design knobs (from ``knobs.py``) onto the top cell.

    Returns:
        The top-level :class:`~picasso.component.Component`.
    """
    top = fw.Component(name="sonyx")
    layout.stamp_knobs(top)  # define knobs before adding any fw.ref(...) children
    # --- Build the chip here ------------------------------------------------
    #   top.add_placed(
    #       fw.make_straight(length=fw.ref("arm_length"), cross_section="rib_sm_1550nm"),
    #       "wg",
    #   )
    #   top.route(...); top.add_port(...)
    return top
