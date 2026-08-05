"""Edge-coupler arrays for sonyx dies.

The circuit-side edge-coupler array is a horizontal row of luqia
``edgecoupler_adiabatic_rib_sm_800nm_ext`` couplers -- the vendored Sonyx
adiabatic inverse-taper design (facet=o1 south, circuit=o2 north),
each built with a ``facet_extension`` lead of ``edge_coupler_extension_length``
on the ``ec_tip_800nm`` facet cross-section — the lead runs toward the die
edge, drawn inside the (blackboxed) PDK cell. The array exposes ``o2_r0_cN``
(circuit, north) and ``o1_r0_cN`` (facet tips, south) ports;
:mod:`sonyx.blocks.dies._frame` positions it at the die's lower-left corner so
the facets protrude ``edge_coupler_protrusion`` past the die edge.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.couplers import edgecoupler_adiabatic_rib_sm_800nm_ext
from picasso.leaves import make_array
from picasso.recipe import recipe

from ..parameters import parameters as _p


@recipe
def circuit_edge_coupler_array(num_couplers: int) -> fw.Component:
    """A row of ``num_couplers`` circuit edge couplers, facets pointing south.

    Pitch = ``edge_coupling_pitch_for_circuits``; each coupler carries a
    ``edge_coupler_extension_length`` facet lead (the PDK cell's surfaced
    ``facet_extension``). Array ports: ``o2_r0_cN`` (circuit) and ``o1_r0_cN``
    (facet tips).
    """
    unit = edgecoupler_adiabatic_rib_sm_800nm_ext(
        facet_extension=_p.edge_coupler_extension_length.value
    )
    return make_array(
        template=unit,
        rows=1,
        cols=num_couplers,
        dx=_p.edge_coupling_pitch_for_circuits.value,
        dy=0.0,
    )
