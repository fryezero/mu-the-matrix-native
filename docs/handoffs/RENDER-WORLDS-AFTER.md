# RENDER-WORLDS-AFTER

The shared world-object machinery the per-world lanes left open: the after-character second pass, the
CreateObject/MoveObject world-group chains, the frame-time global, and Abyss of Atlans' custom/after slots.
[Addresses, provenance, fidelity and limits](../research/client-worlds-after.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-after`, branch `claude/render-worlds-after`,
  from origin/main `eb4b53a`, merged with `f7a1e33` (RENDER-EFFECTS-005). Input links `tools/python` and `evidence`
  from the main checkout, never committed.
- **Scope 1 (second pass):** the first pass never reads `+0xa`; the skip is the current class's custom render
  (slot 0x38, end of `0x017f76ec`). `0x016d6949` is now reconstructed for every world (world list + class byte +5,
  set only by the classes of 134..145; tower and world-2 branches; selector `0x017fe909` with all its world cases
  and the class slot 0x14 overrides). Native draws the second pass for the A worlds and Abyss 1-3
  (`mu_world_after_native`), whose slots 0x38/0x3c are new (`world_abyss_visual.c`).
- **Scope 2 (chains):** the class method is *last* in both chains; every hook before it has its own world test,
  none of which passes in any of the 48 class worlds (verified). No dispatch change was needed; the post-create
  SetAction(0)/action registry `0x00ce4a17` and the pre-move slot 0x74 are recorded as remaining.
- **Scope 3 (frame time):** `0x012aeb2b` reconstructed (`native/core/mu_frame_time.{h,c}`); the five 0.1 stand-ins
  read `mu_frame_time_value()`, ticked only by the two window loops. Tour/tests keep 0.1, so no hash changes (why:
  the tour renders 2 of 25 steps; see the finding).
- **Scope 4:** Abyss 1-3 custom and after slots (above). Other classes' slots remain.
- Shared lines: `world_after.c` (WORLDS-A's file, generalised), `world_visual.h`, `mu_objects_runtime.c` (Abyss custom
  callback, after pass/render gating, refused bitmap meshes), five stand-in lines, the two window loops, one
  CORE_SRC entry, one validator row; WORLDS-A's validator mutant string. Nothing in the per-world dispatch changed.

## Checks

- `validate_worlds_after`: 7 families, **13,424 cases equal, 0 mismatches/stops, 21/21 compiled mutants**.
  Registered; with `validate_render_worlds_a` (9,000, 13 mutants) and `validate_world_order`: 3/3 pass.
- Portable `reconstructed/objects/test_worlds_after.py`: 5 tests + 1 private.
- Fidelity, base `f7a1e33` vs lane: 29/32 DATA-ACQ-002 captures and 14/14 October 22 views identical (PNG, OBJECT,
  light). Abyss 1/2 frames identical (13 / 38 objects moved to the second pass), Abyss 3 10,841 px in the top band
  (type-7 action phase); image error 5.386 / 4.412 / 2.230 unchanged; near-hero fields unchanged.

## Remaining

Custom/after slots of the other classes (Kanturu Underground, Ignis, Nixies, Kethotum, Bloody Tarkan, …) so their
flagged objects leave the first pass natively; a bitmap texture path for model meshes (0x82de/0x82df); the action
registry `0x01ec7d5c`; slot 0x74 of classes 69-72, 79, 80/81, 92, 122; invisible-move slot 0x1c; the shadow block.

No original client or launcher was started. The DATA-ACQ-002 inputs were only read. Renders and reports under
`~/Documents/MTM/mu-mac-tools/native/{renders,scratch}/render-worlds-after` and the base worktree
`worktrees/rwa-base` are deleted at handoff; no new local input needs retention.
