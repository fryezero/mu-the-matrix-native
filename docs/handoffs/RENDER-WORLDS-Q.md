# RENDER-WORLDS-Q

Acheron (91), Ferea (112), Swamp of Darkness (122) and Kubera Mine (123..127): eleven primary create/move/visual
methods, and the elemental light file that was Kubera's terrain-light difference.
[Finding, addresses, fidelity numbers and limits](../research/client-worlds-q.md).

- Claude Opus 5.5 lane. Branch `claude/render-worlds-q`, worktree `~/Documents/MTM/worktrees/render-worlds-q`, from
  origin/main `77c304a`. Ignored `tools/python` and `evidence` are symlinks to the main checkout and are never staged.
- Owns `reconstructed/objects/{acheron,ferea,swamp_darkness,kubera,worlds_q}.c`, `worlds_q.h`, `worlds_q_internal.h`,
  `test_worlds_q.py`, `scripts/validate_worlds_q.py`, `scripts/validate_world_light_name.py`,
  `native/tests/{test_native_worlds_q.py,worlds_q_host.c}`. Minimal shared lines: `mu_terrain_light_name` in
  `reconstructed/terrain/terrain.{c,h}` and its use in `native/core/mu_terrain.c`; `rt.q_handler` and the include in
  `native/core/mu_objects.h`; create/move/visual hooks in `native/core/mu_objects_runtime.c`; Makefile and registry
  rows; the neighbour worlds of the N and O hosts (112 → 111, 127 → 121, now owned here); coverage for these
  four classes only.
- Coverage: **61 → 72/144 primary methods, 21 → 25/48 classes**. Ferea's visual `0x00de6405` remains missing.

## Checks

- `validate_worlds_q`: 11 families × 1,000 = **11,000 cases equal, 0 mismatches/stops, 45/45 compiled mutants**.
- `validate_world_light_name`: **304 worlds equal, 0 stops, 4/4 mutants**; worlds 30/0x22 reported apart; the
  old rule fails exactly worlds 123..127.
- Both registered and passing through `run_validators.py --private`.
- `reconstructed/objects/test_worlds_q.py`: 5 portable tests + 2 private (both pass with
  `MU_RECOVERY_INTEGRATION=1`).
- `native/tests/test_native_worlds_q.py`: production host (worlds 91/112/122/123/127 and sibling 111: creation,
  handler members, Kubera PlaySpeed writes into the native model, one generic tick per object per step, lights,
  Ferea fade, primary visual vs generic hook); synthetic World124 elemental-light selection; private installed
  check (all five Kubera worlds load their light, passes).
- Fidelity at the arrival tiles, base → branch: Kubera image **12.609 → 4.321**, primary light 0.035 → 0, frame
  light near hero 0.105 → 0; static field differences Ferea 944 → 0, Swamp 2,508 → 0, Kubera 572 → 0, Acheron
  85 → 58 (after-character, custom-render slot). The other 28 captures: 56/56 PNG, 28/28 OBJECT, 28/28 light
  dumps identical.

## Remaining

Ferea visual `0x00de6405`; keyed owned CreateEffect `0x59a`/`0x199`/`0x195` and StopBuffer consumers (refused and
counted); Ferea's state machine and Swamp's variant writer; custom/after render slots (Acheron's after-character
flags); Acheron's bone sprites do not show in the captured frames (inference: inside the meshes). No live game
was used.

## Cleanup

After merge, remove `native/{scratch,renders}/render-worlds-q`, the worktree (with its builds and input links) and
the local branch. No new local input needs retention. DATA-ACQ-002's inputs were only read.
