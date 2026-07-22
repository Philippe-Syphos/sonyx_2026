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

# --- Reticle die array (dimensionless counts) -------------------------------
# Kept as plain ints (not ParameterFields) so they index ``range()`` directly.
# 2 columns x 4 rows = 8 dies (tapeout plan v1 §2).
DIE_COLUMNS = 2
DIE_ROWS = 4


class Parameters(ParametersBase):
    """Flat namespace of sonyx's layout-side parameters.

    Reticle / die / dicing geometry for the full-reticle 2x4 shuttle
    (``docs/tapeout_plan_reticle_v1.md`` §2, in the luqia_ln200 PDK repo).
    Dies + dicing lanes tile the reticle exactly; :func:`_check_tiling`
    enforces that at import so an inconsistent edit fails fast.
    """

    reticle_size = ParameterField(
        22000.0,
        units="um",
        description="Full reticle edge — square, 22 mm (the complete top cell).",
    )
    dicing_lane = ParameterField(
        150.0,
        units="um",
        description=(
            "Width of the deep-etch dicing street between adjacent dies and "
            "around the reticle perimeter. Equals luqia's deep_trench_width — "
            "the DEEP_ETCH trench fills the full lane (checked in blocks/reticle.py)."
        ),
    )
    die_width = ParameterField(
        10775.0,
        units="um",
        description=(
            "Per-die width = (reticle_size - (DIE_COLUMNS+1)·dicing_lane) / DIE_COLUMNS "
            "= (22000 - 3·150) / 2. Pinned; validated by _check_tiling()."
        ),
    )
    die_height = ParameterField(
        5312.5,
        units="um",
        description=(
            "Per-die height = (reticle_size - (DIE_ROWS+1)·dicing_lane) / DIE_ROWS "
            "= (22000 - 5·150) / 4. Pinned; validated by _check_tiling()."
        ),
    )
    keepout_width = ParameterField(
        50.0,
        units="um",
        description=(
            "Width of the keepout zone around the die perimeter. "
            "Keep this zone clear of any mask."
        ),
    )
    edge_coupling_pitch_for_circuits = ParameterField(
        127.0,
        units="um",
        description=(
            "Pitch of the edge-coupling test structures (for circuits) "
            "on the die perimeter. Keep this zone clear of any mask."
        ),
    )
    edge_coupling_pitch_for_tests = ParameterField(
        127.0,
        units="um",
        description=(
            "Pitch of the edge-coupling test structures (for tests) "
            "on the die perimeter. Keep this zone clear of any mask."
        ),
    )
    grating_coupling_pitch_for_circuits = ParameterField(
        254.0,
        units="um",
        description=(
            "Pitch of the grating-coupling test structures (for circuits) "
            "on the die perimeter. Keep this zone clear of any mask."
        ),
    )
    grating_coupling_pitch_for_tests = ParameterField(
        254.0,
        units="um",
        description=(
            "Pitch of the grating-coupling test structures (for tests) "
            "on the die perimeter. Keep this zone clear of any mask."
        ),
    )
    edge_coupler_extension_length = ParameterField(
        10.0,
        units="um",
        description=(
            "Length of the straight facet-side (o1) lead appended to each edge "
            "coupler, running toward the die edge on the ec_tip_800nm facet "
            "cross-section. PLACEHOLDER."
        ),
    )
    edge_coupler_protrusion = ParameterField(
        5.0,
        units="um",
        description=(
            "Extent of the edge-coupler facet lead (extension) that overlaps into "
            "the deep-trench zone — i.e. how far the facet tip sits past the die "
            "edge, so the facet is exposed after singulation. Must be <= "
            "edge_coupler_extension_length. PLACEHOLDER."
        ),
    )
    edge_coupler_horizontal_shift = ParameterField(
        300.0,
        units="um",
        description=(
            "Extra horizontal offset of the edge-coupler array away from the die's "
            "left edge, on top of the keepout clearance. PLACEHOLDER."
        ),
    )
    bondpad_horizontal_shift = ParameterField(
        300.0,
        units="um",
        description=(
            "Extra horizontal offset of the bond-pad array away from the die's "
            "right edge, on top of the keepout clearance. PLACEHOLDER."
        ),
    )
    bondpad_vertical_shift = ParameterField(
        50.0,
        units="um",
        description=(
            "Extra vertical offset of the bond-pad array up from the die's bottom "
            "edge, on top of the keepout clearance — keeps wirebonded pads clear "
            "of the die edge. PLACEHOLDER."
        ),
    )
    gsg_modulator_spacing = ParameterField(
        300.0,
        units="um",
        description=(
            "Vertical centre-to-centre spacing between stacked GSG modulators on a "
            "die. Reserved — consumed once a die hosts more than one modulator. "
            "PLACEHOLDER."
        ),
    )
    gsg_modulator_vertical_shift = ParameterField(
        0.0,
        units="um",
        description=(
            "Vertical offset of the GSG modulator centre from the die centre. "
            "PLACEHOLDER."
        ),
    )


parameters = Parameters()


class DieParameters(ParametersBase):
    """Per-die parameter set — one instance per die (values may differ per die).

    Distinct from the layout-wide :data:`parameters`: these are knobs a single
    die owns. Each die module (``blocks/dies/die_r*.py``) instantiates its own
    :class:`DieParameters` and passes it to ``die_frame``.
    """

    num_edge_couplers_circuit = ParameterField(
        8,
        units="",
        description=(
            "Number of edge couplers in this die's circuit-side edge-coupler "
            "array (lower-left corner, pitch = edge_coupling_pitch_for_circuits). "
            "PLACEHOLDER default; override per die."
        ),
    )
    num_bondpads = ParameterField(
        9,
        units="",
        description=(
            "Number of TOP_METAL bond pads in this die's bond-pad array "
            "(lower-right corner, pitch = luqia bondpad_pitch). "
            "PLACEHOLDER default; override per die."
        ),
    )
    gsg_modulator_cell = ParameterField(
        "straight_gsg_modulator_800nm",
        units="",
        description=(
            "Registered luqia cell name of this die's GSG phase-modulator "
            "electrode (phase only, no couplers), resolved via pdk.cells. Base "
            "default is the SM straight_gsg_modulator_800nm; the multimode variant "
            "is straight_gsg_modulator_mm_800nm. Change per die/config as needed."
        ),
    )


class DieParametersMultimode(DieParameters):
    """Column-B die config — multimode GSG modulator electrode.

    Per-die values differ from the base only by redeclaring the field
    (``ParameterField`` is read-only and class-shared, so a subclass is the way
    to vary a value). Add further variant subclasses as the configuration
    evolves.
    """

    gsg_modulator_cell = ParameterField(
        "straight_gsg_modulator_mm_800nm",
        units="",
        description="Multimode GSG phase-modulator electrode (column B).",
    )


def _check_tiling() -> None:
    """Fail fast (at import) if dies + dicing lanes don't exactly fill the reticle."""
    p = parameters
    tol = 1e-6
    width = DIE_COLUMNS * p.die_width.value + (DIE_COLUMNS + 1) * p.dicing_lane.value
    height = DIE_ROWS * p.die_height.value + (DIE_ROWS + 1) * p.dicing_lane.value
    if abs(width - p.reticle_size.value) > tol:
        raise ValueError(
            f"columns do not fill reticle width: {width} != {p.reticle_size.value} µm"
        )
    if abs(height - p.reticle_size.value) > tol:
        raise ValueError(
            f"rows do not fill reticle height: {height} != {p.reticle_size.value} µm"
        )


_check_tiling()
