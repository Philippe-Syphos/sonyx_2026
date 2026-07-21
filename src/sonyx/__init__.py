"""sonyx — a Picasso layout targeting the luqia_ln200 PDK."""

from luqia_ln200 import pdk as _pdk
from picasso.layout import Layout

from .design import build
from .floorplan import floorplan
from .knobs import knobs
from .parameters import parameters
from .signoff import drc_rules

# The canonical entry point. Designers and tooling (CLI, artifacts, GUI)
# drive the design through this one object. The PDK is activated lazily
# inside `layout.materialize()` (`with self.pdk: ...`), so a bare
# `import sonyx` neither activates the PDK nor builds the chip:
#
#     from sonyx import layout
#     layout.materialize(); layout.validate(); layout.write_gds("sonyx.gds")
layout = Layout(
    name="sonyx",
    pdk=_pdk,
    build=build,
    floorplan=floorplan,
    knobs=knobs,
    parameters=parameters,
    drc_rules=drc_rules,
)

__all__ = ["layout"]
