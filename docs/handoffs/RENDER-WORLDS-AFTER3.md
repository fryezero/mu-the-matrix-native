# RENDER-WORLDS-AFTER3 (WIP: stopped at the owner's request, not PR-ready)

The remaining world-class custom (slot 0x38) and after (slot 0x3c) render slots. Claude Opus 5.5 lane. Worktree
`~/Documents/MTM/worktrees/render-worlds-after3` (kept), branch `claude/render-worlds-after3` from origin/main
`7f18bf05`, not yet merged with a newer main. Input links `tools/python` and `evidence` point at the main checkout and
are never committed. No PR and no ready-prs.txt line yet.

## Done (verified under Unicorn, committed)

- **Slots 0x38/0x3c of 133, 141, 143, 144, 145** (`reconstructed/objects/world_slots_visual.c`, section
  "RENDER-WORLDS-AFTER3"). These are scope items 1 and 2, complete.

  | World | Custom 0x38 | After 0x3c | Loader 0x24 | World test |
  |---|---|---|---|---|
  | 133 Temple of Arnil | `0x00d80cea` | `0x00d81c49` | `0x00d807f5` | `0x00d83ada` (0x85) |
  | 141 Tormenta Island | `0x00e4cbd7` (table `0x00e4eed3`, types 0x7d..0x9a) | `0x00e4f952` | `0x00e4c08c` | `0x00e54061` (0x8d) |
  | 143 Kardamahal | `0x00e0f4bc` | `0x00e118fd` | `0x00e0e5d6` | `0x00e136f3` (0x8f) |
  | 144 Swamp of Destruction | `0x00e46e94` | `0x00e48f1c` (needs the live byte) | `0x00e464be` | `0x00e4bb8d` (0x90) |
  | 145 | `0x00d76059` (no world test; alpha < 0.9 answers handled) | `0x00d77d18` | `0x00d75679` | `0x00d79e40` (0x91) |

  Types above 300 are never passed by the manager and are left out: 133's 0x199..0x19e and 141's 0x40e.
  - Each class has a 32-bitmap water range, `Object<world+1>\wt%02d_R.jpg`, selected by
    `(int)(WorldTime·0.015) % 32`: 133 0x8320, 141 0x848e, 143 0x8589, 144 0x8348, 145 0x838a.
  - The other loader bitmaps are in the table.
  - 145 type 0x99 fades object +0x188 (clamped to [0, 1]) and plays 0x5b4 on action 2 once model +0xb4 > 1.
    Model +0xb4 is Animation's `(short)(int)frame`.
  - 141 type 0x2c is drawn only while 1 ≤ frame < the action's key count (action record +8; inferred to be the
    BMD key count).
  - 143's after slot, type 0x71, makes a rand-based AddTerrainLight request.
- **Interface:** `mu_slot_model` gains `action_frames`, `rand_fn` and `rand_context`. `MU_WORLD_SLOT_BITMAPS` is 36.
- **Runtime** (`native/core/mu_objects_runtime.c`, small edits that stay out of RENDER-JOINTS-001's `slot_meshes`
  lines):
  - bitmap list capacity;
  - `slot_model` fills the new fields;
  - `slot_fields` writes +0xb4;
  - first-pass slot sounds go to the sound hook;
  - after-pass ADD_LIGHT events are counted in `draw_unsupported` (no render-time light consumer).
- **Checks:**
  - `scripts/validate_worlds_after3.py --cases 1000 --mutations`: 11 families, **10,212 cases equal, 0
    mismatches/stops, 51/51 compiled mutants detected** (lowest count 1: two loader mutants; 145 0x77 caught 3
    times, Tormenta 0x2c 3 times).
  - The `loaders` family runs each class loader as client code and checks all 212 named bitmaps.
  - Registered in `scripts/validators.toml` as `validate_worlds_after3`.
  - Portable tests: `reconstructed/objects/test_worlds_after3.py` (7 tests + 1 private).
  - `test_worlds_after2.py`'s class list was updated (an intended change). `validate_worlds_after2.py`'s
    `SlotModel` now matches the struct. **`validate_worlds_after2` itself was not rerun after that change.**

## Fidelity (DATA-ACQ-002, default clock, base `7f18bf05` vs lane, all 32 captures)

- **29/32 side.png byte-identical.**
- 143 Kardamahal: 10.911 → **10.499**.
- 144 Swamp of Destruction: 12.395 → 12.394.
- 133 Temple of Arnil: 1.028 → 1.028 (the frame changed; the mean is equal to 3 decimals).
- There are no 141 or 145 captures.
- Velocity differences remain (144: 40).
- The OBJECT/light dumps were not yet compared. The `live_time` tours (manifests `tour-base-live.json` /
  `tour-lane-live.json` for 133/140/142/143/144) were written but not run, and have been deleted with the scratch.

## Not done (next steps, in order)

1. Merge the latest origin/main and resolve conflicts (likely `mu_objects_runtime.c` with RENDER-JOINTS-001; keep both
   sides). Rebuild, then rerun `validate_worlds_after3`, `validate_worlds_after2`, `validate_worlds_after`,
   `validate_worlds_q2` and `validate_object_render` (`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT` set). Then run the
   full gate `nice -n 10 bash scripts/local-macos-ci.sh`.
2. Fidelity: rerun the default and `live_time` tours (recreate the manifests from
   `native/scratch/data-acq-002/tour.json` with an absolute live path and `out_dir`; base = a detached origin/main
   worktree). Compare the OBJECT/light dumps for 133/143/144, not only the PNGs.
3. Scope 3 (not started): the own world cases of `0x017fcd18` (0, 2, 0x21, 0x25, 0x33, 0x38..0x3a, 0x49, 0x4a, 0x5b,
   0x5c, 0x64, 0x65, 0x6e..0x71, 0x7a, 0x83..0x85) and the true branches of its default chain (`0x009a645f`,
   `0x00e94004`, `0x00e3068f`, `0x016a887a`, `0x00e1e4b6`, `0x016a8325`). Extend Q2's `render_first` family.
4. Scope 4 (not started): the writer of the velocity (+0xbc) differences in 140 and 142..144.
5. Docs: `docs/research/client-worlds-after3.md`, the status/handoff/roadmap/plan lines, and the coverage inventory
   if it counts these slots. PR body with a `Steward validators: validate_worlds_after3,validate_worlds_after2,
   validate_worlds_after,validate_worlds_q2,validate_object_render` line (env `MU_RECOVERY_INTEGRATION=1`,
   `MU_GAME_ROOT`). Then the ready-prs.txt line.

No original client was started. The DATA-ACQ-002 inputs were only read. Renders, scratch and the base worktree
`worktrees/rwa3-base` were deleted; no local input needs keeping.
