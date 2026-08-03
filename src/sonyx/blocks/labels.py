"""Visible port labels for sonyx dies, drawn through the PDK's moated label cell.

Every optical / electrical I/O a probe station or fibre array lands on gets a
human-readable name drawn **as polygons** next to it, so the name is visible in
any GDS viewer regardless of text-display settings — and on the finished die.

Geometry comes from one PDK cell, :func:`luqia_ln200.cells.labels.label_moat_labels`
(never ``picasso.leaves.make_label`` directly): glyphs on ``WG_RIB.drawing``
(GDS 10/0 — full-thickness LN kept, so the names survive fabrication as real rib
material) wrapped in a single ``WG_RIB.field`` partial-etch **moat**. Because the
moat is part of that cell, a placed label's ``bbox`` is its outer (moat) extent —
which is what the clearances below are measured against.

Naming is ``DEVICE-POSITION-FUNCTION``, upper case, hyphen separated (e.g.
``MZM-TOP-IN``): the device the port belongs to, which of several identical
devices it is, and what the port does.

Labels are placed **beside** the port they name, never on it: the circuit
edge-coupler labels run vertically (south to north) in the free corridor between
neighbouring couplers, alongside the coupler body they belong to, so they stay
inside the array footprint and clear of the routing channel north of it. The
pad labels do the same in whichever direction each pad family leaves free —
west of the DC bond-pad stack (:func:`..dc_routing.add_dc_pad_labels`), north of
the RF GSG launch triplets and west of the thermistance pad (below).
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200.cells.labels import label_moat_labels

# Port-label glyph height (um). Big enough to read at die zoom, small enough to
# fit sideways (moat included) in the 127 um edge-coupler pitch.
PORT_LABEL_HEIGHT = 17.0

# Gap (um) between the waveguide axis a vertical label names and the label's
# near (west) **moat** edge. Must clear the edge coupler's own footprint
# (~20 um half-width, its moat included).
_VERTICAL_LABEL_GAP = 30.0

# DC bond-pad labels run smaller than the optical ones: the pads sit on a 170 um
# pitch and the strip beside them is 50 um, so a 17 um glyph (37 um across, up to
# ~163 um long) would leave single-digit clearance on both axes. At 12 um a label
# is 32 um across and the longest text ~157 um, which fits with room to spare.
DC_PAD_LABEL_HEIGHT = 12.0

# The RF GSG launches and the thermistance pad both keep the full
# PORT_LABEL_HEIGHT: unlike the DC stack they stand in open die, with a >= 275 um
# band north of every launch triplet and ~400 um of clear strip west of the
# thermistance pad, so the longest text (RF-TOP2-OUT, 178 x 37 um at 17 um
# glyphs) fits with hundreds of um to spare.

# Gap (um) between an RF GSG pad triplet's **north** edge and its label's south
# moat edge. North because the triplet's outward (die-edge) face is the probe
# landing and its inward face carries the launch taper -- the band above it is the
# only free side. 20 um keeps the moat visibly off the pad metal.
_RF_PAD_LABEL_GAP = 20.0

# Gap (um) between the thermistance bonding pad's west edge and its label's east
# moat edge. Mirrors _DC_PAD_LABEL_GAP -- both pad families read from the west.
_THERM_PAD_LABEL_GAP = 9.0

# RF launch instance-name suffix -> label text. Each die names its GSG launches
# ``rf_pads_<suffix>`` (explicit via/taper/pads chain) or ``rf_launch_<suffix>``
# (R1A's wrapped single-cell launch), so the suffix is what identifies the port:
# which modulator (``bot`` / ``top`` / R1A+R1B's third, top-edge ``top2``) and
# which electrode end (``in`` = the driven east end, ``out`` = the west end a
# terminator lands on). ``RF-`` rather than ``MZM-`` so an electrode launch is
# never read as one of the modulator's optical ports (``MZM-TOP-IN`` et al.).
_RF_PAD_LABEL_TEXTS = {
    "bot_in": "RF-BOT-IN",
    "bot_out": "RF-BOT-OUT",
    "top_in": "RF-TOP-IN",
    "top_out": "RF-TOP-OUT",
    "top2_in": "RF-TOP2-IN",
    "top2_out": "RF-TOP2-OUT",
}
_RF_PAD_PREFIXES = ("rf_pads_", "rf_launch_")

# Label text on the thermistance bonding pad (the one wirebond pad that is not
# part of the DC array, so it carries its own name rather than an array index).
_THERM_PAD_LABEL_TEXT = "THERM-PAD"


def add_vertical_label(
    cell: fw.Component,
    text: str,
    *,
    wg_x: float,
    y_top: float,
    name: str,
    height: float = PORT_LABEL_HEIGHT,
    gap: float = _VERTICAL_LABEL_GAP,
) -> None:
    """Draw ``text`` bottom-to-top just east of the waveguide axis ``wg_x``.

    The PDK label cell anchors its glyphs at the origin — text centred on
    ``x = 0`` with (``valign="bottom"``) its bottom edge at ``y = 0``, the moat
    overhanging that on all four sides. A 90 deg (CCW) rotation maps local
    ``(x, y)`` to ``(px - y, py + x)``, so the placement below solves for
    ``(px, py)`` from the cell's own bbox: the label's west **moat** edge lands
    ``gap`` east of ``wg_x``, and its **north** moat edge on ``y_top``.

    Anchoring the north edge (rather than the south) is what lets a row of
    labels share one top line despite their differing text lengths — they hang
    from it and run south by however long each one is.

    Args:
        cell: Component to place the label on.
        text: Label string (``DEVICE-POSITION-FUNCTION``, upper case).
        wg_x: x of the waveguide / port axis the label names.
        y_top: y the label's northern moat edge lands on.
        name: Instance name for the placed label.
        height: Glyph height (um).
        gap: Clearance (um) between ``wg_x`` and the label's west moat edge.
    """
    label = label_moat_labels(text=text, height=height, valign="bottom")
    bb = label.bbox
    cell.add_placed(
        label,
        name=name,
        x=wg_x + gap + bb.ymax,
        y=y_top - bb.xmax,
        rotation=90.0,
    )


def add_horizontal_label(
    cell: fw.Component,
    text: str,
    *,
    x_ref: float,
    y_bottom: float,
    name: str,
    side: str = "west",
    height: float = PORT_LABEL_HEIGHT,
    gap: float = 0.0,
) -> None:
    """Draw ``text`` left-to-right beside ``x_ref``, standing on ``y_bottom``.

    The unrotated counterpart of :func:`add_vertical_label`, for naming something
    with room to its side rather than above or below it — a bond pad in a
    vertical stack, say. The PDK cell already anchors the text centred on
    ``x = 0`` with its bottom edge at ``y = 0``, so this only offsets that: the
    label's near **moat** edge lands ``gap`` from ``x_ref`` on ``side``, and its
    southern moat edge on ``y_bottom``.

    Args:
        cell: Component to place the label on.
        text: Label string (``DEVICE-POSITION-FUNCTION``, upper case).
        x_ref: x of the edge the label stands beside.
        y_bottom: y the label's southern moat edge lands on.
        name: Instance name for the placed label.
        side: which side of ``x_ref`` the label sits on — ``"west"`` (default)
            puts its **east** edge ``gap`` west of ``x_ref``, ``"east"`` the
            mirror.
        height: Glyph height (um).
        gap: Clearance (um) between ``x_ref`` and the label's near moat edge.

    Raises:
        ValueError: if ``side`` is not ``"east"`` / ``"west"``.
    """
    if side not in ("east", "west"):
        raise ValueError(f"side must be 'east' or 'west', got {side!r}")
    label = label_moat_labels(text=text, height=height, valign="bottom")
    bb = label.bbox
    near_edge = x_ref + gap if side == "east" else x_ref - gap - bb.dx
    cell.add_placed(
        label,
        name=name,
        x=near_edge - bb.xmin,
        y=y_bottom - bb.ymin,
    )


def circuit_edge_coupler_label_texts(num_couplers: int) -> dict[int, str]:
    """Label text per circuit edge-coupler index, from the shared allocation.

    The allocation is identical on all eight dies — it is set by
    :func:`.dies._frame.die_scaffold` (loopback + spiral feed) and
    :mod:`.dies._head_coupler_block` (input block + output directional
    couplers), with ``num_couplers = 10``:

    ==========  ==============  ==================================================
    Index       Label           Fed by / feeds
    ==========  ==============  ==================================================
    ``c0``      ALIGN-LOOP-A    the two facets of the ``ec_loopback_circuit``
    ``c1``      ALIGN-LOOP-B    C-bend U-turn (fibre-array alignment loop)
    ``c2``      MZM-TOP-OUT2    ``test_dc_out_top`` open ports (``o4`` / ``o3``),
    ``c3``      MZM-TOP-OUT1    i.e. the top MZM's two outputs
    ``c4``      MZM-BOT-OUT2    ``test_dc_out_bot`` open ports (``o4`` / ``o3``),
    ``c5``      MZM-BOT-OUT1    i.e. the bottom MZM's two outputs
    ``c6``      MZM-BOT-IN      input block's lower device -> bottom MZM
    ``c7``      MZM-TOP-IN      ``test_modulator_head`` -> top MZM
    ``c8``      SPIRAL-B        the SM loss/delay spiral's two ports
    ``c9``      SPIRAL-A        (``test_spiral_sm`` ``o2`` / ``o1``)
    ==========  ==============  ==================================================

    Indices are expressed relative to ``num_couplers`` exactly as the routing
    helpers express them, so the map follows if the count changes; entries that
    would fall outside ``0 .. num_couplers - 1`` are dropped.
    """
    n = num_couplers
    texts = {
        0: "ALIGN-LOOP-A",
        1: "ALIGN-LOOP-B",
        n - 8: "MZM-TOP-OUT2",
        n - 7: "MZM-TOP-OUT1",
        n - 6: "MZM-BOT-OUT2",
        n - 5: "MZM-BOT-OUT1",
        n - 4: "MZM-BOT-IN",
        n - 3: "MZM-TOP-IN",
        n - 2: "SPIRAL-B",
        n - 1: "SPIRAL-A",
    }
    return {i: t for i, t in texts.items() if 0 <= i < n}


def add_circuit_edge_coupler_labels(cell: fw.Component, num_couplers: int) -> None:
    """Label every circuit edge coupler of a die (plus the extra reference facet).

    Reads the placed array's own port positions (``edge_couplers_circuit``,
    ports ``o2_r0_cN``) for each label's x, and hangs every label from the same
    y — the array's own top edge — so the row reads as one band alongside the
    coupler bodies, flush with them at the north end. Texts come from
    :func:`circuit_edge_coupler_label_texts`; the lone open facet west of the
    alignment loop (``edge_coupler_extra``) is labelled ``EC-REF``.

    Labels differ in length, so a shared top line means their southern ends do
    not align; the longest still clears the bottom keep-out ring, since the
    array top stands well above it.

    A no-op on a die with no circuit edge-coupler array.
    """
    if "edge_couplers_circuit" not in cell.instances:
        return
    arr = cell.instances["edge_couplers_circuit"]
    y_top = arr.bbox.ymax
    for i, text in circuit_edge_coupler_label_texts(num_couplers).items():
        add_vertical_label(
            cell,
            text,
            wg_x=arr.ports[f"o2_r0_c{i}"].position[0],
            y_top=y_top,
            name=f"label_ec_c{i}",
        )
    # The extra reference facet sits one pitch west of the alignment loop, as its
    # own 1-coupler array (port o2_r0_c0) -- same coupler unit, so same top edge.
    if "edge_coupler_extra" in cell.instances:
        add_vertical_label(
            cell,
            "EC-REF",
            wg_x=cell.instances["edge_coupler_extra"].ports.o2_r0_c0.position[0],
            y_top=y_top,
            name="label_ec_ref",
        )


def add_rf_pad_labels(cell: fw.Component) -> None:
    """Name every RF GSG launch pad triplet of a die, reading north of the pads.

    One horizontal label per launch, sitting in the free band
    ``_RF_PAD_LABEL_GAP`` above the launch's north edge with its **outer** moat
    edge flush with the launch's outer edge — east-flush for an ``_in`` launch
    (those sit on the die's east edge), west-flush for an ``_out`` one — so the
    text hangs off the die-edge end of the pad column and runs back inward.

    North of the triplet is the one side that is free: the outward face is the
    GSG probe / wirebond landing, the inward face carries the launch taper, and
    the 27 um signal-to-ground gaps are far too narrow for a glyph. The bands
    between (and above) the stacked launches are 275 um tall or more, and clear
    for ~400 um inward from the die edge on every die, so a 180 x 37 um label
    lands in open field.

    Which launches exist differs per die: every die names them
    ``rf_pads_<suffix>`` except R1A, whose wrapped single-cell launch is
    ``rf_launch_<suffix>``; R1A/R1B add the third, top-edge modulator's
    ``top2`` pair. Whatever is present is labelled from
    :data:`_RF_PAD_LABEL_TEXTS` and anything else is left alone, so this is a
    no-op on a die with no RF launch.

    Instances are named ``label_<launch instance name>``.
    """
    for prefix in _RF_PAD_PREFIXES:
        for suffix, text in _RF_PAD_LABEL_TEXTS.items():
            iname = f"{prefix}{suffix}"
            if iname not in cell.instances:
                continue
            bb = cell.instances[iname].bbox
            assert bb is not None  # placed instances always have geometry
            # ``_in`` launches run east from the modulator, ``_out`` ones west
            # (see the per-die RF chains), so each label hangs from the launch
            # edge that faces the die edge.
            east = suffix.endswith("_in")
            add_horizontal_label(
                cell,
                text,
                x_ref=bb.xmax if east else bb.xmin,
                y_bottom=bb.ymax + _RF_PAD_LABEL_GAP,
                side="west" if east else "east",
                name=f"label_{iname}",
            )


def add_thermistance_pad_label(cell: fw.Component) -> None:
    """Name the thermistance bonding pad, reading horizontally west of it.

    One horizontal label, its east moat edge ``_THERM_PAD_LABEL_GAP`` west of the
    pad's west edge and standing on the pad's bottom edge — the same relation the
    DC bond-pad labels have to their pads
    (:func:`..dc_routing.add_dc_pad_labels`), so both pad families read from the
    west. The strip west of the pad is clear on every die, whether the pad sits
    on the shared ``_THERMISTANCE_CENTER`` (six dies) or beside R1A/R1B's
    top-right grating-coupler array.

    Reads the pad's **placed** bbox, so it must run after any
    :func:`..dies._frame.place_thermistance_pad` /
    ``place_thermistance_pad_west_of`` move — i.e. at the end of a die builder.

    A no-op on a die with no thermistance pad (one with no bond-pad array).
    """
    if "thermistance_bonding_pad" not in cell.instances:
        return
    bb = cell.instances["thermistance_bonding_pad"].bbox
    assert bb is not None  # placed instances always have geometry
    add_horizontal_label(
        cell,
        _THERM_PAD_LABEL_TEXT,
        x_ref=bb.xmin,
        y_bottom=bb.ymin,
        side="west",
        gap=_THERM_PAD_LABEL_GAP,
        name="label_thermistance_pad",
    )
