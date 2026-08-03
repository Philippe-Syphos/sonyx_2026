"""Per-die PCM & calibration block (see ``docs/pcm_cells.md``).

One contiguous, reusable block of process-control-monitor / calibration cells
stamped onto every die by the die scaffold (:func:`add_pcm_block`). Built
PDK-first; each cell is a ``@recipe`` so it is a cached Component shared across
all eight dies (like a PDK cell), and :func:`add_pcm_block` places them
directly into the die -- no wrapper Component to collide at reticle assembly.

Cells (left to right):

1. ``open GSG``   -- open GSG landing pads (RF de-embed, parasitic C).
2. ``short GSG``  -- GSG pads shorted signal->ground by the low-R
                     ``gsg_short_top_metal_50ohms`` bar.
3. ``MRR g800``   -- all-pass ring (800 nm coupler gap), GC-column I/O, rot 90.
4. ``MRR g400``   -- all-pass ring (400 nm coupler gap), GC-column I/O, rot 90.
5. ``bondpad row`` -- 9-pad AEPONYX probe row with the heater_cr DUT wired to
                     the third and fourth pads (0-based pads 2-3).

The grating loopback has been removed pending a rebuild. The rings follow the
buddha ring-test pattern (2-up 127 um GC column, ring on a folded bus) built
from the ``ringresonator_allpass_rib_sm_800nm`` PDK cell, and the whole element
is rotated 90 deg.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk
from picasso.recipe import recipe

from ..parameters import parameters as _p

# Layout knobs.
_CELL_GAP = 300.0  # um, horizontal gap between adjacent PCM cells in the block
_GSG_CLOSER = 250.0  # um, extra tightening of the open<->short GSG gap
_RING_STACK_GAP = 25.0  # um, vertical gap between the two stacked rings
_BONDPAD_ARRAY_GAP = 100.0  # um, vertical gap from the pad row down to the heater
# Probe pads in the DC row: the AEPONYX automated-probe card expects a
# provision for 9 pads (200 x 200 um at the 250 um pitch) with every needle
# landing on metal. The heater DUT wires to pads 2-3; the rest are unwired.
_NUM_BONDPADS = 9
# Raise (um) of the heater_cr toward the bond-pad row. Dropped 75 -> 25 (the
# heater sits 50 um further south) to open vertical room for the bias routes'
# S-jogs between the terminals and the pad faces.
_HEATER_RAISE = 25.0
_GC_TOWARD_GSG = 225.0  # um, shift of the ring/GC stack toward the GSG cells
_BONDPAD_TOWARD_RING = 250.0  # um, shift of the bond-pad array toward the ring

# Ring test element (buddha pattern).
_FIBER_PITCH = 127.0  # um, grating-coupler fibre-array pitch
_RING_RADIUS = 40.0  # um, microring radius
_RING_GAPS = (0.8, 0.4)  # um, the two ring coupler gaps (800 nm / 400 nm)


@recipe(register_as="pcm_open_gsg")
def _open_gsg() -> fw.Component:
    """1. Open GSG pads -- stock GSG landing, signal/grounds unconnected."""
    c = fw.Component()
    c.add_placed(pdk.cells["gsg_bondpads_top_metal_50ohms"](), name="gsg")
    return c


@recipe(register_as="pcm_shorted_gsg")
def _shorted_gsg() -> fw.Component:
    """2. GSG pads shorted signal->ground by the low-R GSG short bar."""
    c = fw.Component()
    pads = c.add_placed(pdk.cells["gsg_bondpads_top_metal_50ohms"](), name="gsg")
    c.put(
        pdk.cells["gsg_short_top_metal_50ohms"](),
        pads.ports.e2,
        port_to="e1",
        name="short",
    )
    return c


def _ring_element(gap: float) -> fw.Component:
    """All-pass ring on a 2-up GC column, folded bus (buddha pattern), rotated 90.

    GC(out) at the bottom of a 127 um GC column, GC(in) at the top; the top GC
    feeds a short lead straight -> tight L-bend onto the ring's bus -> ring (PDK
    ``ringresonator_allpass_rib_sm_800nm``, circle hung to one side) -> tight
    L-bend -> bridge straight -> back into the bottom GC. Probed by the standard
    grating-coupler fibre alignment. The assembled element is rotated 90 deg.
    """
    inner = fw.Component()
    gc_out = inner.add_placed(
        pdk.cells["gratingcoupler_rib_sm_800nm_ord"](), name="gc_out", x=0.0, y=0.0
    )
    gc_in = inner.add_placed(
        pdk.cells["gratingcoupler_rib_sm_800nm_ord"](), name="gc_in", x=0.0, y=_FIBER_PITCH
    )
    fold = pdk.cells["lbend_rib_sm_800nm_tight"]().ports["o2"].position[0]
    bus_len = _FIBER_PITCH - 2.0 * fold
    bend_in = inner.put(
        pdk.cells["lbend_rib_sm_800nm_tight"](), gc_in.ports.o1, port_to="o1", name="bend_in"
    )
    ring = inner.put(
        pdk.cells["ringresonator_allpass_rib_sm_800nm"](
            radius=_RING_RADIUS, gap=gap, bus_length=bus_len
        ),
        bend_in.ports.o2, port_to="o1", name="ring", mirror=True,
    )
    bend_out = inner.put(
        pdk.cells["lbend_rib_sm_800nm_tight"](), ring.ports.o2, port_to="o1", name="bend_out"
    )
    # No lead-in / bridge straights: the two folds return the path exactly to the
    # bottom GC, so bend_out mates gc_out directly.
    inner.connect(bend_out.ports.o2, gc_out.ports.o1)
    # Rotate the whole ring element 90 deg.
    c = fw.Component()
    c.add_placed(inner, name="ring_elem", rotation=90.0)
    return c


@recipe(register_as="pcm_ring_g800")
def _ring_g800() -> fw.Component:
    """All-pass ring, 800 nm coupler gap."""
    return _ring_element(_RING_GAPS[0])


@recipe(register_as="pcm_ring_g400")
def _ring_g400() -> fw.Component:
    """All-pass ring, 400 nm coupler gap."""
    return _ring_element(_RING_GAPS[1])


@recipe(register_as="pcm_ring_stack")
def _ring_stack() -> fw.Component:
    """3. The two rings (g800, g400) stacked vertically, _RING_STACK_GAP apart."""
    c = fw.Component()
    top = _ring_g800()
    bot = _ring_g400()
    tb, bb = top.bbox, bot.bbox
    c.add_placed(top, name="ring_g800", x=-tb.center_x, y=_RING_STACK_GAP / 2.0 - tb.ymin)
    c.add_placed(bot, name="ring_g400", x=-bb.center_x, y=-_RING_STACK_GAP / 2.0 - bb.ymax)
    return c


@recipe(register_as="pcm_bondpad_row")
def _bondpad_row() -> fw.Component:
    """4. A 9-pad DC probe row (AEPONYX provision) with heater_cr below pads 2-3.

    ``_NUM_BONDPADS`` 200 x 200 um pads at the 250 um probe pitch, centred on
    x=0 -- the AEPONYX 9-pad provision, so every needle of the probe card
    lands on metal. A ``heater_cr`` sits below the row, centred between the
    third and fourth pads (0-based pads 2-3; instances ``pad_3`` / ``pad_4``)
    and raised _HEATER_RAISE um toward them -- the heater-resistor DUT --
    with each terminal autorouted up to its pad's south face (e1 -> pad_3,
    e2 -> pad_4; one call per line, the terminals face opposite ways so a
    bundle is illegal). The other pads are unwired landing metal. Routed
    inside this recipe, so every die shares the one wired cell.
    """
    pad = pdk.cells["bondpad_for_test_top"]()
    pad_w = pad.bbox.dy  # rotated width (native height, 200)
    pad_h = pad.bbox.dx  # rotated height (native width, 200)
    pitch = pad_w + _p.dc_test_pad_spacing.value  # the AEPONYX 250 um probe pitch
    x0 = -(_NUM_BONDPADS - 1) / 2.0 * pitch  # pad_1 centre; row centred on x=0
    c = fw.Component()
    for i in range(_NUM_BONDPADS):
        c.add_placed(
            pdk.cells["bondpad_for_test_top"](), name=f"pad_{i + 1}",
            x=x0 + i * pitch, y=0.0, rotation=90.0,
        )
    # heater_cr centred between the third and fourth pads, below the row and
    # raised toward it.
    heater = pdk.cells["heater_cr"]()
    hb = heater.bbox
    heater_cx = x0 + 2.5 * pitch  # midpoint of pads 3 and 4
    top_y = -pad_h / 2.0 - _BONDPAD_ARRAY_GAP + _HEATER_RAISE  # heater bbox top edge
    c.add_placed(heater, name="heater", x=heater_cx - hb.center_x, y=top_y - hb.ymax)
    # Heater bias: each terminal up to its own pad's south face (the pads are
    # rotated 90 deg, so that face is the port named "w"). e1 (west terminal)
    # takes pad_3 and e2 takes pad_4, so the two lines don't cross. The
    # heater sits low enough (_HEATER_RAISE) that the default planner turns
    # the small terminal-to-face jog cleanly -- forced start/end straights
    # overshoot the few-um x-offset in this geometry and fold the centreline,
    # so the calls stay bare.
    for term, pad_name in (("e1", "pad_3"), ("e2", "pad_4")):
        c.autoroute(
            ports_a=[("heater", term)],
            ports_b=[(pad_name, "w")],
            spec="routing_top_metal",
            avoid_port_owners=False,
            name=f"heater_bias_{term}",
        )
    return c


def add_pcm_block(cell: fw.Component, x_right: float, y_top: float) -> None:
    """Place the PCM/calibration cells directly into ``cell`` (docs/pcm_cells.md).

    The (recipe) cells are packed left to right by bbox so the block's **right
    edge** lands at ``x_right`` (the rightmost cell, the DC bond-pad array, sits
    there -- e.g. next to the thermistance pad), with their top edges aligned at
    ``y_top``. Each entry carries its own leading gap (gap from the previous
    cell) so the GSG pair can sit tighter than the rest. A plain function -- it
    stamps the cached recipe cells straight into the die, so nothing new is
    created that could clash at reticle assembly.
    """
    # (cell, instance name, leading gap from previous cell in um).
    entries = [
        (_open_gsg(), "pcm_open_gsg", 0.0),
        (_shorted_gsg(), "pcm_shorted_gsg", _CELL_GAP - _GSG_CLOSER),
        (_ring_stack(), "pcm_ring_stack", _CELL_GAP - _GC_TOWARD_GSG),
        (_bondpad_row(), "pcm_bondpad_row", _CELL_GAP - _BONDPAD_TOWARD_RING),
    ]
    total_w = sum(sub.bbox.dx + gap for sub, _, gap in entries)
    cursor = x_right - total_w
    for sub, iname, gap in entries:
        cursor += gap
        sb = sub.bbox
        cell.add_placed(sub, name=iname, x=cursor - sb.xmin, y=y_top - sb.ymax)
        cursor += sb.dx
