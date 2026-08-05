"""Grating-coupler DOE test block — the 62 variants of ``GC_TFLN_795nm_DOE_v6``.

One **loopback pair** per DOE variant: two identical focusing grating couplers
(``gratingcoupler_rib_sm_800nm_ext``, facets north / waveguide port south) on the
``grating_coupling_pitch_for_tests`` 127 um fibre pitch, joined below by a
``cbend_rib_sm_800nm_127um`` U-turn. Fibre into one grating, out the other, so a
single transmission measurement gives 2x the per-coupler efficiency of that
variant. Each pair carries its DOE ID as a drawn label south of the U-turn.

The DOE sweeps, all through the (now parametric) PDK cell:

- **GC01-GC15** Design D pitch x duty cycle grid (562-586 nm x 36/40/44 %)
- **GC16-GC19** Design D tooth-count sweep (N = 26/33/48/55)
- **GC20-GC34** Design E pitch x duty cycle grid (542-566 nm x 42/46/50 %)
- **GC35-GC38** Design E tooth-count sweep (N = 27/34/49/56)
- **GC39-GC44** on-target 795 nm variants (D @ 559 nm, E @ 532 nm)
- **GC45-GC49** fan-aperture sweep (20/35/45/55/65 deg)
- **GC50-GC56** waveguide-width sweep (0.8/1.2/1.5 um), some crossed with aperture
- **GC57-GC62** replicas of the D nominal (fibre-position / repeatability)

None of the 62 are apodised — the DOE is a uniform-grating sweep, and the
picasso leaf draws one constant duty cycle per coupler.

**Waveguide-width variants**: the PDK coupler is built directly on a rib of the
DOE width, so its ``o1`` is *not* ``rib_sm_800nm`` for GC50-GC56. Those pairs get
a short linear width taper (:data:`_WIDTH_TAPER_LENGTH`) between the coupler and
the U-turn, added **here** rather than in the PDK cell, so the PDK coupler stays
exactly the DOE device and the taper stays a test-harness concern.

Block geometry: :func:`gc_doe_block` packs the variants into rows of
:data:`_VARIANTS_PER_ROW` on a 2-pitch (254 um) centre spacing, stacked
:data:`_ROW_PITCH` apart, sized to land inside a 400 um x 8 mm envelope.
"""

from __future__ import annotations

from dataclasses import dataclass

import picasso as fw
from luqia_ln200.cells.bends import cbend_rib_sm_800nm_127um
from luqia_ln200.cells.couplers import (
    gc_focusing_cross_section,
    gratingcoupler_rib_sm_800nm_ext,
)
from luqia_ln200.cells.labels import label_moat_labels
from picasso.leaves import make_taper_from_xs
from picasso.recipe import recipe
from picasso.resolve import to_cross_section

from ..parameters import parameters as _p

# Length (um) of the linear width taper between a non-SM DOE coupler and the
# SM U-turn. Short by design (the DOE measures the grating, not the taper);
# 30 um holds a <= 1 deg half-angle for the widest variant (0.5 -> 1.5 um).
_WIDTH_TAPER_LENGTH = 30.0

# Glyph height (um) for the per-variant DOE ID label, and the gap from the
# U-turn's south edge to the label's north moat edge.
_LABEL_HEIGHT = 15.0
_LABEL_GAP = 8.0

# Variants per block. A loopback pair spans two fibre pitches, so 31 pairs at a
# 254 um centre spacing reach 7.94 mm wide — inside the 8 mm budget — and the
# 62 variants split into exactly two blocks. A single row per block is forced by
# the 400 um height budget: the tallest unit (GC52, a 1.5 um-core variant whose
# taper adds 30 um) is 246 um, so a second row would need a <= 154 um row pitch
# and the two rows would overlap.
_VARIANTS_PER_BLOCK = 31
NUM_BLOCKS = 2

# Nominal SM rib width (um) — a variant at this width needs no taper.
_SM_WIDTH = 0.5


@dataclass(frozen=True)
class GcVariant:
    """One row of the DOE table.

    Attributes:
        gid: DOE ID (``"GC01"`` ... ``"GC62"``) — also the drawn label.
        design: Anchor design the variant perturbs (``"D"`` or ``"E"``).
        period_nm: Tooth pitch (nm).
        duty_cycle: Solid-tooth fraction of a period.
        num_periods: Tooth count N.
        aperture_deg: Full fan opening angle (degrees).
        wg_width: Waveguide core width (um) at the coupler port.
        peak_nm: Estimated peak wavelength (nm) — sets the tooth conic.
    """

    gid: str
    design: str
    period_nm: float
    duty_cycle: float
    num_periods: int
    aperture_deg: float
    wg_width: float
    peak_nm: float


def _d(gid: str, period_nm: float, dc: int, n: int, peak: float) -> GcVariant:
    """Design-D variant at the nominal 27 deg aperture / 0.5 um waveguide."""
    return GcVariant(gid, "D", period_nm, dc / 100.0, n, 27.0, _SM_WIDTH, peak)


def _e(gid: str, period_nm: float, dc: int, n: int, peak: float) -> GcVariant:
    """Design-E variant at the nominal 27 deg aperture / 0.5 um waveguide."""
    return GcVariant(gid, "E", period_nm, dc / 100.0, n, 27.0, _SM_WIDTH, peak)


def _d_nom(gid: str, aperture: float, width: float) -> GcVariant:
    """Design-D nominal (574 nm / 40 % / N=41 / 813 nm) at a given fan + width."""
    return GcVariant(gid, "D", 574.0, 0.40, 41, aperture, width, 813.0)


# The DOE table (GC_TFLN_795nm_DOE_v6.xlsx, sheet "GC TFLN 795nm", rows 10-71).
# lambda_peak comes from the sheet's own estimate column (anchor lambda_pic
# shifted by its dlambda/dLambda slope), which is what the tooth conic is
# designed at.
GC_DOE: tuple[GcVariant, ...] = (
    # GC01-GC15 — Design D pitch x duty-cycle grid.
    _d("GC01", 562.0, 36, 41, 798.7),
    _d("GC02", 562.0, 40, 41, 798.7),
    _d("GC03", 562.0, 44, 41, 798.7),
    _d("GC04", 568.0, 36, 41, 805.8),
    _d("GC05", 568.0, 40, 41, 805.8),
    _d("GC06", 568.0, 44, 41, 805.8),
    _d("GC07", 574.0, 36, 41, 813.0),
    _d("GC08", 574.0, 40, 41, 813.0),
    _d("GC09", 574.0, 44, 41, 813.0),
    _d("GC10", 580.0, 36, 41, 820.2),
    _d("GC11", 580.0, 40, 41, 820.2),
    _d("GC12", 580.0, 44, 41, 820.2),
    _d("GC13", 586.0, 36, 41, 827.3),
    _d("GC14", 586.0, 40, 41, 827.3),
    _d("GC15", 586.0, 44, 41, 827.3),
    # GC16-GC19 — Design D tooth-count sweep at the nominal pitch / DC.
    _d("GC16", 574.0, 40, 26, 813.0),
    _d("GC17", 574.0, 40, 33, 813.0),
    _d("GC18", 574.0, 40, 48, 813.0),
    _d("GC19", 574.0, 40, 55, 813.0),
    # GC20-GC34 — Design E pitch x duty-cycle grid.
    _e("GC20", 542.0, 42, 42, 808.4),
    _e("GC21", 542.0, 46, 42, 808.4),
    _e("GC22", 542.0, 50, 42, 808.4),
    _e("GC23", 548.0, 42, 42, 815.8),
    _e("GC24", 548.0, 46, 42, 815.8),
    _e("GC25", 548.0, 50, 42, 815.8),
    _e("GC26", 554.0, 42, 42, 823.2),
    _e("GC27", 554.0, 46, 42, 823.2),
    _e("GC28", 554.0, 50, 42, 823.2),
    _e("GC29", 560.0, 42, 42, 830.7),
    _e("GC30", 560.0, 46, 42, 830.7),
    _e("GC31", 560.0, 50, 42, 830.7),
    _e("GC32", 566.0, 42, 42, 838.1),
    _e("GC33", 566.0, 46, 42, 838.1),
    _e("GC34", 566.0, 50, 42, 838.1),
    # GC35-GC38 — Design E tooth-count sweep (at the 553 nm anchor pitch).
    _e("GC35", 553.0, 46, 27, 822.0),
    _e("GC36", 553.0, 46, 34, 822.0),
    _e("GC37", 553.0, 46, 49, 822.0),
    _e("GC38", 553.0, 46, 56, 822.0),
    # GC39-GC44 — variants landing on 795 nm.
    _d("GC39", 559.0, 40, 41, 795.1),
    _d("GC40", 559.0, 44, 41, 795.1),
    _d("GC41", 559.0, 48, 41, 795.1),
    _e("GC42", 532.0, 46, 42, 796.0),
    _e("GC43", 532.0, 50, 42, 796.0),
    _e("GC44", 532.0, 54, 42, 796.0),
    # GC45-GC49 — fan-aperture sweep on the D nominal.
    _d_nom("GC45", 20.0, _SM_WIDTH),
    _d_nom("GC46", 35.0, _SM_WIDTH),
    _d_nom("GC47", 45.0, _SM_WIDTH),
    _d_nom("GC48", 55.0, _SM_WIDTH),
    _d_nom("GC49", 65.0, _SM_WIDTH),
    # GC50-GC56 — waveguide-width sweep, partly crossed with the aperture.
    _d_nom("GC50", 27.0, 0.8),
    _d_nom("GC51", 27.0, 1.2),
    _d_nom("GC52", 27.0, 1.5),
    _d_nom("GC53", 35.0, 1.2),
    _d_nom("GC54", 35.0, 1.5),
    _d_nom("GC55", 45.0, 1.5),
    _d_nom("GC56", 20.0, 1.2),
    # GC57-GC62 — replicas of the D nominal (fibre position / repeatability).
    _d_nom("GC57", 27.0, _SM_WIDTH),
    _d_nom("GC58", 27.0, _SM_WIDTH),
    _d_nom("GC59", 27.0, _SM_WIDTH),
    _d_nom("GC60", 27.0, _SM_WIDTH),
    _d_nom("GC61", 27.0, _SM_WIDTH),
    _d_nom("GC62", 27.0, _SM_WIDTH),
)


def _doe_coupler(variant: GcVariant) -> fw.Component:
    """The PDK focusing GC built at ``variant``'s design point."""
    return gratingcoupler_rib_sm_800nm_ext(
        period=variant.period_nm / 1000.0,
        fill_factor=variant.duty_cycle,
        num_periods=variant.num_periods,
        angle_subtended=variant.aperture_deg,
        design_wavelength=variant.peak_nm / 1000.0,
        wg_width=variant.wg_width,
    )


@recipe
def gc_doe_loopback(gid: str) -> fw.Component:
    """Loopback pair for one DOE variant — two couplers + a U-turn + a label.

    Both couplers sit on the ``grating_coupling_pitch_for_tests`` fibre pitch
    with their gratings north and their waveguide ports south; the U-turn joins
    the two ports below. Variants whose waveguide width is not the SM rib get a
    :data:`_WIDTH_TAPER_LENGTH` linear taper on each arm first, so the U-turn
    always runs on ``rib_sm_800nm``. Port-less (the fibre facets are the I/O).

    Args:
        gid: DOE ID of the variant to build (keys :data:`GC_DOE`).

    Raises:
        KeyError: If ``gid`` is not a DOE ID.
    """
    variant = next((v for v in GC_DOE if v.gid == gid), None)
    if variant is None:
        raise KeyError(f"unknown DOE variant {gid!r}")

    pitch = _p.grating_coupling_pitch_for_tests.value
    cell = fw.Component()
    gc = _doe_coupler(variant)
    left = cell.add_placed(gc, name="gc_left", x=0.0, y=0.0)
    right = cell.add_placed(gc, name="gc_right", x=pitch, y=0.0)

    # Width taper (test-harness only): the DOE's wide-waveguide couplers present
    # a non-SM port, so bring each arm back to rib_sm_800nm before the U-turn.
    port_left, port_right = left.ports.o1, right.ports.o1
    if variant.wg_width != _SM_WIDTH:
        taper = make_taper_from_xs(
            length=_WIDTH_TAPER_LENGTH,
            from_xs=to_cross_section(gc_focusing_cross_section(variant.wg_width)),
            to_xs=to_cross_section("rib_sm_800nm"),
        )
        port_left = cell.put(taper, port_left, port_to="o1", name="taper_left").ports.o2
        port_right = cell.put(taper, port_right, port_to="o1", name="taper_right").ports.o2

    # 127 um U-turn: its two ports are exactly one fibre pitch apart, so it
    # lands on both arms; connect() asserts the second abutment.
    uturn = cell.put(cbend_rib_sm_800nm_127um(), port_left, port_to="o1", name="uturn")
    cell.connect(uturn.ports.o2, port_right)

    # DOE ID drawn south of the U-turn, centred on the pair.
    label = label_moat_labels(text=variant.gid, height=_LABEL_HEIGHT, valign="top")
    cell.add_placed(
        label,
        name="label",
        x=pitch / 2.0,
        y=cell.bbox.ymin - _LABEL_GAP,
    )
    cell.cell_type = "test_structure"
    cell.description = (
        f"GC DOE {variant.gid}: design {variant.design}, "
        f"{variant.period_nm:g} nm / {variant.duty_cycle * 100:g} % / N={variant.num_periods} / "
        f"{variant.aperture_deg:g} deg / {variant.wg_width:g} um core"
    )
    cell.calibration_status = "PLACEHOLDER"
    return cell


def block_variants(block: int) -> tuple[GcVariant, ...]:
    """The :data:`_VARIANTS_PER_BLOCK` variants carried by ``block``."""
    start = block * _VARIANTS_PER_BLOCK
    return GC_DOE[start : start + _VARIANTS_PER_BLOCK]


@recipe
def gc_doe_block(block: int) -> fw.Component:
    """One DOE block — :data:`_VARIANTS_PER_BLOCK` loopback pairs in a row.

    Pairs run west to east on a 2-fibre-pitch (254 um) centre spacing, all
    gratings on one line so a fibre array lands on the whole row. Block 0 is
    GC01-GC31, block 1 GC32-GC62. Instances are named ``{gid}`` so a
    measurement script can look a variant's placement straight up.

    Args:
        block: Block index, ``0`` to ``NUM_BLOCKS - 1``.

    Raises:
        IndexError: If ``block`` is out of range.
    """
    if not 0 <= block < NUM_BLOCKS:
        raise IndexError(f"block {block} out of range (0..{NUM_BLOCKS - 1})")
    pitch = _p.grating_coupling_pitch_for_tests.value
    cell = fw.Component()
    for col, variant in enumerate(block_variants(block)):
        cell.add_placed(
            gc_doe_loopback(variant.gid),
            name=variant.gid,
            x=col * 2.0 * pitch,
            y=0.0,
        )
    cell.cell_type = "test_structure"
    variants = block_variants(block)
    cell.description = (
        f"Grating-coupler DOE v6 block {block} — "
        f"{variants[0].gid}-{variants[-1].gid} loopback pairs"
    )
    cell.calibration_status = "PLACEHOLDER"
    return cell
