"""Edge-coupler arrays for sonyx dies.

The circuit-side edge-coupler array is a horizontal row of luqia
``edgecoupler_rib_sm_800nm_ext`` couplers (facet=o1 south, circuit=o2 north),
each carrying a straight facet-side lead of ``edge_coupler_extension_length``
on the ``ec_tip_800nm`` facet cross-section — the lead runs toward the die
edge. The array exposes ``o2_r0_cN`` (circuit, north) and ``facet_r0_cN``
(facet tips, south) ports; :mod:`sonyx.blocks.dies._frame` positions it at
the die's lower-left corner so the facets protrude ``edge_coupler_protrusion``
past the die edge.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.couplers import edgecoupler_rib_sm_800nm_ext
from picasso.leaves import make_array, make_straight
from picasso.recipe import recipe

from ..parameters import parameters as _p

# The coupler's o1 (facet) cross-section; the straight lead extends it.
_FACET_XS = "ec_tip_800nm"


@recipe
def _edge_coupler_with_lead(extension_length: float) -> fw.Component:
    """One edge coupler + a straight facet-side (o1) lead of ``extension_length``.

    Ports: ``facet`` (south tip, on ``ec_tip_800nm``) and ``o2`` (circuit
    side, north, on ``rib_sm_800nm``).
    """
    unit = fw.Component()
    ec = unit.add_placed(edgecoupler_rib_sm_800nm_ext(), "ec")
    lead = unit.put(
        make_straight(length=extension_length, cross_section=_FACET_XS),
        ec.ports.o1,
        port_to="o1",
        name="lead",
    )
    unit.add_port("facet", lead.ports.o2)
    unit.add_port("o2", ec.ports.o2)
    return unit


@recipe
def circuit_edge_coupler_array(num_couplers: int) -> fw.Component:
    """A row of ``num_couplers`` circuit edge couplers, facets pointing south.

    Pitch = ``edge_coupling_pitch_for_circuits``; each coupler carries a
    ``edge_coupler_extension_length`` facet lead. Array ports: ``o2_r0_cN``
    (circuit) and ``facet_r0_cN`` (facet tips).
    """
    unit = _edge_coupler_with_lead(_p.edge_coupler_extension_length.value)
    return make_array(
        template=unit,
        rows=1,
        cols=num_couplers,
        dx=_p.edge_coupling_pitch_for_circuits.value,
        dy=0.0,
    )
