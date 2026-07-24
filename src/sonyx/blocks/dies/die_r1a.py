"""Die holder R1·A — top-left of the reticle.

Planned test content (``tapeout_plan_reticle_v1.md`` §4.0): loss spirals
SM+ULL (GC, 4 lengths) · racetrack (Ls x gap). Frame only for now.
"""

from __future__ import annotations

import picasso as fw
from luqia_ln200 import pdk

from ...parameters import DieParameters
from ...parameters import parameters as _p
from ._frame import die_scaffold
from ._head_coupler_block import add_head_and_couplers
from .test_cells_die_r1a import test_waveguide_cutback_sm, test_waveguide_cutback_ull

# Horizontal gap between the SM and ULL cutback test cells (um).
_CUTBACK_GAP = 200.0


def die_r1a() -> fw.Component:
    """Build and return the R1·A die."""
    params = DieParameters()
    cell = die_scaffold("die_R1A", params, bondpad_rotation=0.0)
    # Two GSG phase-modulator electrodes (SM on column A) stacked vertically:
    # bottom one gsg_modulator_vertical_shift above the die bottom edge, top one
    # gsg_modulator_spacing (centre-to-centre) above it. Placed directly so their
    # ports (o1-o4 optical, e1/e2 electrode) are reachable for per-die routing.
    half_w = _p.die_width.value / 2.0
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
    mod_bot = cell.add_placed(modulator, "gsg_modulator_bot", x=x0, y=bot_y)
    mod_top = cell.add_placed(modulator, "gsg_modulator_top", x=x0, y=top_y)
    # One more electrode descending from the top edge: same vertical shift
    # (top-edge inset) as the bottom pair takes from the bottom. Its former
    # mirror-pair partner now lives on R1B -- the two top modulators are split
    # one per die.
    top2_y = half_h - _mod_shift - mb.ymax
    mod_top_2 = cell.add_placed(modulator, "gsg_modulator_top_2", x=x0, y=top2_y)
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
    # # Test-cell section, top-left corner: SM waveguide-loss (cutback) structure.
    # # Sits flush inside the top-left keep-out corner (top region is otherwise
    # # free -- label is bottom-left, modulators / RF are lower-centre).
    # top_inner = half_h - _p.keepout_width.value
    # cutback = test_waveguide_cutback_sm()
    # cb_bb = cutback.bbox
    # sm_x = -half_w + _p.keepout_width.value - cb_bb.xmin
    # cell.add_placed(cutback, "test_waveguide_cutback_sm", x=sm_x, y=top_inner - cb_bb.ymax)
    # # ULL-spiral twin just to the right of the SM cutback, tops aligned.
    # ull = test_waveguide_cutback_ull()
    # ull_bb = ull.bbox
    # sm_right = sm_x + cb_bb.xmax
    # cell.add_placed(
    #     ull,
    #     "test_waveguide_cutback_ull",
    #     x=(sm_right + _CUTBACK_GAP) - ull_bb.xmin,
    #     y=top_inner - ull_bb.ymax,
    # )
    # Wire via cell.instances["gsg_modulator_bot"/"gsg_modulator_top"],
    # "edge_couplers_circuit", "bondpads".
    return cell
