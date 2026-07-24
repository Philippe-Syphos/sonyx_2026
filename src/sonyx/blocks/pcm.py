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

The DC bond-pad cells and the grating loopback have been removed pending a
rebuild. The rings follow the buddha ring-test pattern (2-up 127 um GC column,
ring on a folded bus) built from the ``ringresonator_allpass_rib_sm_800nm`` PDK
cell, and the whole element is rotated 90 deg.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk
from picasso.recipe import recipe

# Layout knobs.
_CELL_GAP = 300.0  # um, horizontal gap between adjacent PCM cells in the block
_GSG_CLOSER = 250.0  # um, extra tightening of the open<->short GSG gap
_RING_STACK_GAP = 25.0  # um, vertical gap between the two stacked rings
_BONDPAD_ARRAY_GAP = 100.0  # um, gap between pads in the bond-pad array
_HEATER_RAISE = 75.0  # um, raise of the heater_cr toward the bond-pad pair
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
    c.add_placed(pdk.cells["gsg_bondpads_top_metal_50ohms"](), "gsg")
    return c


@recipe(register_as="pcm_shorted_gsg")
def _shorted_gsg() -> fw.Component:
    """2. GSG pads shorted signal->ground by the low-R GSG short bar."""
    c = fw.Component()
    pads = c.add_placed(pdk.cells["gsg_bondpads_top_metal_50ohms"](), "gsg")
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
    gc_out = inner.add_placed(pdk.cells["gratingcoupler_rib_sm_800nm_ord"](), "gc_out", x=0.0, y=0.0)
    gc_in = inner.add_placed(
        pdk.cells["gratingcoupler_rib_sm_800nm_ord"](), "gc_in", x=0.0, y=_FIBER_PITCH
    )
    fold = pdk.cells["lbend_rib_sm_800nm_tight"]().ports["o2"].position[0]
    bus_len = _FIBER_PITCH - 2.0 * fold
    bend_in = inner.put(
        pdk.cells["lbend_rib_sm_800nm_tight"](), gc_in.ports.o1, port_to="o1", name="bend_in"
    )
    ring = inner.put(
        pdk.cells["ringresonator_allpass_rib_sm_800nm"](radius=_RING_RADIUS, gap=gap, bus_length=bus_len),
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
    c.add_placed(inner, "ring_elem", rotation=90.0)
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
    c.add_placed(top, "ring_g800", x=-tb.center_x, y=_RING_STACK_GAP / 2.0 - tb.ymin)
    c.add_placed(bot, "ring_g400", x=-bb.center_x, y=-_RING_STACK_GAP / 2.0 - bb.ymax)
    return c


@recipe(register_as="pcm_bondpad_1x2")
def _bondpad_1x2() -> fw.Component:
    """4. A 1x2 pair of DC test bond pads (long side N-S) with heater_cr below.

    Two pads side by side, each rotated 90 deg so its long (400 um) side runs
    N-S. A ``heater_cr`` sits below the pair, centred on it and raised
    _HEATER_RAISE um toward the pads (no routing) -- the heater-resistor DUT.
    """
    pad = pdk.cells["bondpad_for_test_top"]()
    pad_w = pad.bbox.dy  # rotated width (native height, 200)
    pad_h = pad.bbox.dx  # rotated height (native width, 400)
    pitch = pad_w + _BONDPAD_ARRAY_GAP
    xs = [-pitch / 2.0, pitch / 2.0]  # the pair, centred on x=0
    c = fw.Component()
    for i, x in enumerate(xs):
        c.add_placed(pdk.cells["bondpad_for_test_top"](), f"pad_{i}", x=x, y=0.0, rotation=90.0)
    # heater_cr centred between the pair, below them and raised toward them.
    heater = pdk.cells["heater_cr"]()
    hb = heater.bbox
    top_y = -pad_h / 2.0 - _BONDPAD_ARRAY_GAP + _HEATER_RAISE  # heater bbox top edge
    # Centre the heater's bbox on x=0 (its origin is not its bbox centre).
    c.add_placed(heater, "heater", x=-hb.center_x, y=top_y - hb.ymax)
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
        (_bondpad_1x2(), "pcm_bondpad_1x2", _CELL_GAP - _BONDPAD_TOWARD_RING),
    ]
    total_w = sum(sub.bbox.dx + gap for sub, _, gap in entries)
    cursor = x_right - total_w
    for sub, iname, gap in entries:
        cursor += gap
        sb = sub.bbox
        cell.add_placed(sub, iname, x=cursor - sb.xmin, y=y_top - sb.ymax)
        cursor += sb.dx
