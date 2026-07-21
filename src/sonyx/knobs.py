"""Design knobs for sonyx — tunable Variables exposed to the GUI / sweeps.

Each entry is a :class:`picasso.Variable` with optional metadata: ``bounds``
renders a slider, ``allowed`` a dropdown, ``description`` a tooltip, and
``gui`` forces a specific widget. ``build()`` stamps these onto the top cell
via ``layout.stamp_knobs(top)``; read them in geometry with ``fw.ref("name")``
(numerics) or ``top.lookup_variable("name")`` (variant choices). Sweep them
with ``layout.materialize(overrides={"name": value})``.
"""

from __future__ import annotations

import picasso as fw

knobs: dict[str, fw.Variable] = {
    # "arm_length": fw.Variable(
    #     "arm_length", 500.0, units="um", bounds=(100.0, 5000.0), gui="slider"
    # ),
    # "splitter": fw.Variable("splitter", "mmi", allowed=["mmi", "dc"], gui="dropdown"),
}
