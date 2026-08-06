"""Die holder R1·A — top-left of the reticle.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): loss spirals
SM+ULL (GC, 4 lengths) · racetrack (Ls x gap). Frame only for now.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ..gc_test_array import open_gc_array_block
from ..labels import add_rf_pad_labels, add_thermistance_pad_label
from ..reflectometry import reflectometry_block
from ._frame import die_scaffold, place_thermistance_pad_west_of
from ._head_coupler_block import (
    add_dc_output_to_ec_routes,
    add_head_and_couplers,
    add_head_input_routes,
    add_input_beam_dumps,
    add_mzm_input_routes,
    add_mzm_output_routes,
    add_top2_dc_pad_routes,
    add_top2_dc_pads,
    add_top2_gc_routes,
    add_top2_routes,
    add_top_head_and_coupler,
)

# Top-edge inset (um) of row 1's third electrode, the one descending from the
# top edge. Row-1 specific -- the other dies carry only the bottom pair. Moved
# 150 um north (1250 -> 1100) to open up the band below it.
_TOP2_EDGE_INSET = 1100.0

# Die-level anchor of the open GC-array block (its local origin is the loop's
# west edge / GC tops line), top-right corner: margins off the right / top
# inner edges (clear of the top-right corner alignment loop).
_OPEN_GC_RIGHT_MARGIN = 250.0
_OPEN_GC_TOP_MARGIN = 40.0

# Reflectometry block: its west edge off the left inner edge (vertically it is
# centred in the band between the two lower modulators -- see the placement).
_REFLECTO_LEFT_MARGIN = 1000.0


def die_r1a() -> fw.Component:
    """Build and return the R1·A die."""
    params = DieParameters()
    # R1A keeps its original horizontal row of 7 bond pads (NOT the shared
    # 2-columns-of-4 corner block the other dies use): 7 single-pad columns laid
    # out as one horizontal row (1 pad tall, un-staggered).
    cell = die_scaffold("die_R1A", params, num_bondpads=7, num_bondpad_cols=7)
    # Two GSG phase-modulator electrodes (SM on column A) stacked vertically:
    # bottom one gsg_modulator_vertical_shift above the die bottom edge, top one
    # gsg_modulator_spacing (centre-to-centre) above it. Placed directly so their
    # ports (o1-o4 optical, e1/e2 electrode) are reachable for per-die routing.
    half_h = _p.die_height.value / 2.0
    modulator = pdk.cells[params.gsg_modulator_cell.value](
        length=_p.gsg_modulator_electrode_length.value,
    )
    mb = modulator.bbox
    x0 = -mb.center_x  # centre the electrode in x
    # The bottom pair sits on the shared gsg_modulator_vertical_shift (2 mm), the
    # same as rows 2-4, so row 1's two lower modulators line up with every other
    # die. (They previously used a local 1250 um shift, from when row 1 carried
    # two full mirror pairs; the top pair is now split one modulator per die.)
    bot_y = -half_h + _p.gsg_modulator_vertical_shift.value - mb.ymin
    top_y = bot_y + _p.gsg_modulator_spacing.value
    mod_bot = cell.add_placed(modulator, name="gsg_modulator_bot", x=x0, y=bot_y)
    mod_top = cell.add_placed(modulator, name="gsg_modulator_top", x=x0, y=top_y)
    # One more electrode descending from the top edge, on row 1's own 1250 um
    # top-edge inset (it has no counterpart on the other dies). Its former
    # mirror-pair partner now lives on R1B -- the two top modulators are split
    # one per die.
    top2_y = half_h - _TOP2_EDGE_INSET - mb.ymax
    mod_top_2 = cell.add_placed(modulator, name="gsg_modulator_top_2", x=x0, y=top2_y)
    # RF launch (via -> electrode-to-pads taper -> GSG bondpad triplet, wrapped in
    # one PDK cell) on both electrode ends of every modulator. put() auto-rotates,
    # so the "_in" launch on e2 runs east and the "_out" launch on e1 mirrors and
    # runs west -- no per-side port bookkeeping needed.
    for m, tag in (
        (mod_bot, "bot"),
        (mod_top, "top"),
        (mod_top_2, "top2"),
    ):
        cell.put(
            pdk.cells["gsg_launch_electrode_to_pads_top_metal_50ohms"](),
            m.ports.e2,
            port_to="e1",
            name=f"rf_launch_{tag}_in",
        )
        cell.put(
            pdk.cells["gsg_launch_electrode_to_pads_top_metal_50ohms"](),
            m.ports.e1,
            port_to="e1",
            name=f"rf_launch_{tag}_out",
        )
    # --- R1·A per-die content (see module docstring for planned DUTs) ---
    # Input modulator_head + directional coupler (east) and one output DC above
    # each of the lower two modulators (west) -- the shared head+coupler block.
    # R1A uses the wrapped RF launch (no rf_pads_bot_in), so hand the helper the
    # bottom input launch's east edge as the anchor: mod_bot's east port plus the
    # launch's e1-to-east extent (port-based / Component.bbox, ty-clean).
    launch = pdk.cells["gsg_launch_electrode_to_pads_top_metal_50ohms"]()
    launch_east_from_e1 = launch.bbox.xmax - launch.ports["e1"].position[0]
    pad_east_x = mod_bot.ports.e2.position[0] + launch_east_from_e1
    add_head_and_couplers(cell, input_anchor=(pad_east_x, mod_bot.ports.e1.position[1]))
    # Feed the input block's head + directional coupler from the two next-rightmost
    # circuit edge couplers (default, non-tight SM routing).
    add_head_input_routes(cell, int(params.num_edge_couplers_circuit.value))
    # Terminate the input stage's spare (unfed) west inputs -- one per input
    # device -- with a PDK beam dump, mirrored away from the fed neighbour.
    add_input_beam_dumps(cell)
    # Route the input-block outputs to the two MZMs (head -> top, coupler -> bottom).
    # The third modulator (gsg_modulator_top_2) has its own head and is not fed here.
    add_mzm_input_routes(cell)
    # Route each MZM's outputs (o1/o2) into its output directional coupler (two calls).
    dc_ec_obs = add_mzm_output_routes(cell)
    # Output DCs -> open circuit edge couplers (bottom drop + top drop via a
    # west-facing U-turn stub). Shared helper.
    add_dc_output_to_ec_routes(cell, int(params.num_edge_couplers_circuit.value), dc_ec_obs)
    # Open grating-coupler array block (4 couplers + left alignment loop),
    # top-right (right edge / GC tops at the standard margins) -- fibre I/O for
    # the extra top modulator (gsg_modulator_top_2), coupler ports exposed.
    half_w = _p.die_width.value / 2.0
    kw = _p.keepout_width.value
    gc_top2 = open_gc_array_block(4)
    cell.add_placed(
        gc_top2,
        name="mod_top2_gc",
        x=((half_w - kw) - _OPEN_GC_RIGHT_MARGIN) - gc_top2.bbox.xmax,
        y=(half_h - kw) - _OPEN_GC_TOP_MARGIN,
    )
    # R1A/R1B only: park the thermistance bonding pad just west of that array
    # instead of on the reticle-wide _THERMISTANCE_CENTER the other six dies use.
    # Must follow the array -- the pad is re-placed relative to it.
    place_thermistance_pad_west_of(cell, ("mod_top2_gc",))
    # modulator_head (left) + output directional coupler (right) for the extra top
    # modulator, rotated 180 deg vs the standard block, in the band above it.
    add_top_head_and_coupler(cell, "gsg_modulator_top_2")
    # Four DC bias pads for that head's heaters, north-west corner (placement only).
    add_top2_dc_pads(cell)
    # head -> MZM and MZM -> output DC for that modulator (the rotated twin of the
    # add_mzm_input_routes / add_mzm_output_routes pair above).
    top2_obs = add_top2_routes(cell, "gsg_modulator_top_2")
    # The 4 open grating couplers -> that head's inputs / that DC's open outputs.
    add_top2_gc_routes(cell, top2_obs)
    # That head's heater terminals -> the four north-west DC pads.
    add_top2_dc_pad_routes(cell)
    # (The GSG termination-resistance sweep moved to R2B -- see die_r2b.)
    # Reflectometry block (4 grating couplers, two GC-fed 8 mm waveguides --
    # one open-ended, one beam-dumped -- wired inside the block), centred
    # vertically in the clear band between the two lower modulators so it
    # tracks the modulators rather than the die edge. The centring uses the
    # block's declared depth (couplers to lower waveguide), not its bbox.
    reflecto = reflectometry_block()
    lo_bb = cell.instances["gsg_modulator_bot"].bbox
    hi_bb = cell.instances["gsg_modulator_top"].bbox
    assert lo_bb is not None and hi_bb is not None  # placed instances have geometry
    cell.add_placed(
        reflecto,
        name="reflectometry",
        x=(-half_w + kw) + _REFLECTO_LEFT_MARGIN,
        y=(lo_bb.ymax + hi_bb.ymin) / 2.0 + reflecto.parameters.centring_depth.value / 2.0,
    )
    # (The SM waveguide-loss cutback test cell moved to R3A -- see die_r3a. The
    # ULL twin recipe, test_waveguide_cutback_ull, is still available if wanted.)
    # Visible names on the RF GSG launch pads (north of each triplet) and on the
    # thermistance bonding pad (west of it). Last, so both read the pads' final
    # placed positions -- the thermistance pad is moved twice on this die.
    add_rf_pad_labels(cell)
    add_thermistance_pad_label(cell)
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads". (The rightmost-edge-couplers -> SM delay
    # spiral feed is now shared for every die in die_scaffold -- see _frame.py.)
    return cell
