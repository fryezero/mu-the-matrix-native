# RENDER-WORLDS-AFTER2

The world-class slots beyond the primary create/move/visual: the custom render (slot 0x38) and after render (slot 0x3c)
of twelve classes, bitmaps on model meshes, and the pre-move slot 0x74.
[Addresses, provenance, fidelity and limits](../research/client-worlds-after2.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-after2`, branch `claude/render-worlds-after2`,
  from origin/main `34081544`, merged with `61d5bb49` (#265..#267, clean). Input links `tools/python` and `evidence` from
  the main checkout, never committed.
- **Slots 0x38/0x3c (verified):** Acheron 91, Nixies Lake 113, Scorched Canyon 131, Red Smoke Icarus 132, Gray Aida 134,
  Old/Burning Kethotum 135/136, Kanturu Underground 137, Ignis 138, 139, Bloody Tarkan 140, Twisted Karutan 142
  (`reconstructed/objects/world_slots_visual.c`). Natively the first pass draws a slot's Body/Mesh calls (all of them,
  through `mu_objects_first_meshes`), the flagged objects leave it, and the second pass draws slot 0x3c.
- **Bitmap meshes (verified registrations):** a per-world LoadBitmap table and a (world, type) use table; the bitmaps
  load as model texture extras and bind through RenderMesh's texture argument. Abyss 0x82de/0x82df are no longer
  refused; Abyss's second custom mesh is now drawn.
- **Pre-move slot 0x74 (verified, synthetic state only):** 69, 70, 71, 72, 79, 80, 81, 122. Worlds 69..72 and 80/81
  have no capture. Arca 92's slot is not bounded (run-time registry) and is left.
- Shared lines: `mu_objects_runtime.c` (class custom callback, slot draws, after slot call, bitmap extras, pre-move
  call, texture check replacing the Abyss refusal), `mu_objects.h` (runtime fields, two constants), the first-mesh
  capacity in `native/world/parts/objects.c`, one line of `world_after.c` (`mu_world_after_native`), `world_visual.h`,
  one validator row. No per-world dispatch file changed.

## Checks

- `validate_worlds_after2`: 33 families, **32,216 cases equal, 0 mismatches/stops, 33/33 compiled mutants**. Registered.
- Portable `reconstructed/objects/test_worlds_after2.py`: 7 tests + 1 private.
- Fidelity, base origin/main `61d5bb49` vs lane, DATA-ACQ-002 32 captures: 22 byte-identical (PNG, OBJECT, light);
  Acheron after-character 58 → 6; Kanturu Underground hidden-mesh 24 → 0 and after-character 20 → 0; Twisted Karutan
  image 13.48 → 7.15; Burning Kethotum 8.66 → 6.53; Red Smoke Icarus 26.37 → 23.02; Old Kethotum 2.39 → 1.94; Ignis
  4.14 → 3.83; Nixies 7.00 → 6.91; Scorched Canyon 8.07 → 8.01; Gray Aida 13.07 → 13.05; **Kanturu Underground image
  5.79 → 6.36 (worse: its crystals now take the move slot's blend light, still 0.9 against live 0.1)**.

## Coordination (RENDER-WORLDS-G3)

The Abyss 2 dark objects do not depend on these slots: Abyss 1-3's slots were AFTER's and are unchanged in what they
draw except type 0x34's second (0x82df) mesh, and the Abyss captures stay byte-identical here.

## Remaining

Slots of 141, 143, 145 (about 2,300 instructions each), 133, 144 and the classes outside the second-pass list;
Acheron `0x00d73cd7`; Arca 92 pre-move; the Imperial Guardian handler state; a native StreamMesh (+0x94) consumer;
per-action PlaySpeed outside 135/136; Kanturu Underground type 0xa blend light (move slot).

No original client or launcher was started. The DATA-ACQ-002 inputs were only read. Local renders were reduced to four
side-by-side images (`native/renders/render-worlds-after2`) and are deleted at handoff with the scratch folder and
the base worktree `worktrees/rwa2-base`; no new local input needs retention.

## PR-ready gate

On the merge of origin/main `61d5bb49`: `nice -n 10 bash scripts/local-macos-ci.sh` passes: **1,770 tests across 38
suites, 1,538 passed, 232 skipped, zero failures; fixtures, native viewer, live readers; audit 1,752 files, zero
rejected**. Private validators (`run_validators.py --private --jobs 2`, `MU_GAME_ROOT` set): **12 pass, 0 fail**
(`validate_worlds_after2`, `validate_worlds_after`, `validate_render_worlds_a`, `validate_world_order`,
`validate_object_render`, `validate_worlds_n/o/p/p2/q/r/r2`); `validate_objects` skipped (pinned section-3 input absent).
Only the docs changed after the gate.
