"""Die holder R1·A — top-left of the reticle.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): loss spirals
SM+ULL (GC, 4 lengths) · racetrack (Ls x gap). Frame only for now.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ..gc_test_array import add_open_gc_array
from ..gsg_termination_sweep import add_gsg_termination_sweep
from ..reflectometry import add_reflectometry_cell
from ._frame import die_scaffold
from ._head_coupler_block import add_head_and_couplers, add_top_head_and_coupler


def die_r1a() -> fw.Component:
    """Build and return the R1·A die."""
    params = DieParameters()
    cell = die_scaffold("die_R1A", params, bondpad_rotation=0.0)
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
    # Row 1 uses a 1250 um shift (rows 2-4 use the 2 mm
    # gsg_modulator_vertical_shift default): the full 2 mm shift would collide
    # R1A's two mirror pairs, which the four-electrode stack has no room for.
    _mod_shift = 1250.0
    bot_y = -half_h + _mod_shift - mb.ymin
    top_y = bot_y + _p.gsg_modulator_spacing.value
    mod_bot = cell.add_placed(modulator, name="gsg_modulator_bot", x=x0, y=bot_y)
    mod_top = cell.add_placed(modulator, name="gsg_modulator_top", x=x0, y=top_y)
    # One more electrode descending from the top edge: same vertical shift
    # (top-edge inset) as the bottom pair takes from the bottom. Its former
    # mirror-pair partner now lives on R1B -- the two top modulators are split
    # one per die.
    top2_y = half_h - _mod_shift - mb.ymax
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
    # Open grating-coupler array (4 couplers) + left alignment loop, top-right --
    # unrouted fibre I/O for the extra top modulator (gsg_modulator_top_2).
    add_open_gc_array(cell, num=4, prefix="mod_top2_gc")
    # modulator_head (left) + output directional coupler (right) for the extra top
    # modulator, rotated 180 deg vs the standard block, in the band above it.
    add_top_head_and_coupler(cell, "gsg_modulator_top_2")
    # GSG termination-resistance sweep (7 probeable lumped-terminator DUTs,
    # 25-75 ohm + nominal 50 ohm) in a single row along the top-left edge.
    add_gsg_termination_sweep(cell)
    # Reflectometry cell -- first pass: 4 grating couplers (left alignment loop +
    # 2 open) below the terminators. Reflector/delay path added later.
    add_reflectometry_cell(cell)
    # (The SM waveguide-loss cutback test cell moved to R3A -- see die_r3a. The
    # ULL twin recipe, test_waveguide_cutback_ull, is still available if wanted.)
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    return cell
