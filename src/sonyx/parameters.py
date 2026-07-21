"""Layout-side fixed parameters for sonyx.

Designer-pinned values for this layout — distinct from :mod:`sonyx.knobs`,
which holds GUI-tunable :class:`picasso.Variable`s. Parameters here are
**not** exposed to the GUI, not sweepable via
``layout.materialize(overrides=...)``, and don't change without a code
edit. Use this module for compile-time configuration of the layout's
shape (block dimensions, fixed offsets, anything you want to pin once).

Mirrors the shape of the target PDK's ``tech/parameters.py`` at the
layout altitude: a :class:`Parameters` class with
:class:`~picasso.building_blocks.ParameterField` descriptors, exposing
a module-level :data:`parameters` instance designers import as::

    from sonyx.parameters import parameters as _layout_params
    value = _layout_params.some_field.value

The two namespaces (PDK params + layout params) stay separate — PDK
constants stay in the PDK's own ``parameters.py``.
"""

from __future__ import annotations

from picasso.building_blocks import ParameterField, ParametersBase


class Parameters(ParametersBase):
    """Flat namespace of sonyx's layout-side parameters."""

    # Declare entries here. The unit belongs in ``units=``, not the
    # name itself (so ``block_height``, not ``block_height_um``).
    #   block_height = ParameterField(
    #       2000.0, units="um",
    #       description="Vertical extent of the main block.",
    #   )


parameters = Parameters()
