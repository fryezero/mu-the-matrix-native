# RENDER-WORLDS-AFTER5

The follow-up named in [AFTER4](RENDER-WORLDS-AFTER4.md) "Remaining": the velocity data source, the world 0x27
tower-state writers and a render-time light capture.
[Addresses, checks, fidelity and limits](../research/client-worlds-after5.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-after5`, branch
  `claude/render-worlds-after5`, from origin/main `5cb6fa6d`. Input links `tools/python`, `evidence` and `input`
  point at the main checkout and are never committed.
- **1. Velocity data source (static, then one live read; verified):**
  - The registry map `0x01ec7d5c`+0x10 is copied at world load (`0x00ea289c`) from the Lang table object
    `0x06fbc434`.
  - `0x0112cb08` fills that object from `MapObjectAnimationInfo\MapObjectAnimationInfo<world+1>`, which lives in
    the encrypted `Data\Lang.mpr`. Rows are parsed by `0x0112bc34`; the key is 1000 · action + type.
  - The table was read once from the client at its server list (no login, read-only `langread graph`): 10 worlds,
    143 entries.
  - The SetAction and tick handlers are ported in `reconstructed/objects/action_registry.c`, and native consumes the
    table from `MU_LANG_DIR/mapanim.tsv` (`native/core/mu_objects_anim.c`).
- **2. Tower state (static, not ported):** the only writer, `0x009a649a`, is reached from server-message sub-codes
  2/3 (`0x0128bb6f` → `0x0124eeda`/`0x0124ef61` → `0x00e8d845`). It is a packet handler, so it stops at naming.
- **3. Render-time light capture: not taken.** Kardamahal's only Warps destination has no type 0x71 in view; any
  other tile needs walking.
- **Shared lines:**
  - `mu_objects.h`: one include, the runtime's `anim` fields, three declarations;
  - `mu_objects_runtime.c`: three calls (load in start, SetAction(0) after create, the tick after the Animation
    tick);
  - `native/Makefile`: two source lines and the `anim-host` rule;
  - `reconstructed/objects/Makefile`: one source;
  - one validator row.

## Live session

One session, 2026-11-04:
- lock held 12:25:22–12:27:07; client up 12:25:26–12:26:50;
- the owner's free-runtime client was started to the server list only (no login, no world, no input beyond the
  launcher's GAME START click);
- the read was `langread` and `memread` (`mach_vm_read_overwrite`);
- the client and launcher were quit and the lock released;
- `LauncherOption.if`, `IGCLauncherOption.ini`, `config.ini` and `option.ini` were backed up and are byte-identical
  afterwards (DevModeIndex 2; no window-size change).

## Inputs for later lanes and the app (local, never commit)

- `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-after5/lang/mapanim.tsv` (145 lines, SHA-256
  `d7a2cc72e2854f1edb1738df34ab63dae60676887a3fb5d3fe330015a57de814`): the MapObjectAnimationInfo rows.
  - Point `MU_LANG_DIR` at a directory holding it (copy it next to the other lang tables in `scratch/lang` or
    `Native Data/lang` so the app uses it).
  - Without it, native keeps CreateObject's speeds.
  - Rebuild it from a new read with `langread <pid> out.bin graph:0x06fbc434=0x48,4,0` and
    `scripts/live_anim_table_to_plain.py out.bin <dir>`.
- The 6 MB langread snapshot was deleted after the conversion (its SHA-256 was
  `313b9085…dde7d295`).

## Checks

Under the 2026-11-04 test budget: no lane gate; the steward's batch gate is the full gate.

| Check | Result | Wall time |
|---|---|---|
| `validate_worlds_after5` (registered, with mutants, once) | set_action 3,000 + tick 3,000 equal, 0 stops, 29/29 mutants | 373 s |
| `validate_worlds_after5 --only live_rows --lang-dir` (private data) | 1,084 equal | 2 s |
| `validate_worlds_after4` (no mutants) | 9,181 equal | 23 s |
| `validate_worlds_after3` (no mutants) | 10,212 equal | 9 s |
| `validate_worlds_after2` (no mutants) | 32,216 equal | 24 s |
| `validate_worlds_after` (no mutants) | 13,424 equal | 15 s |
| `validate_worlds_q2` (no mutants) | 4,000 equal | 7 s |
| `validate_object_render` | pass | 4 s |
| Unit tests | `test_worlds_after5` 9 (1 private skipped), `test_anim_table_plain` 2, `test_native_anim` 1 | ~3 s |
| Fidelity tours (32 captures each: base, lane, lane without the table; default, live_time, draw_all) | see the finding §6 | 57–106 s each |

## Remaining

- Tick handlers 4, 6 and 8: the hero box collision `0x018500bf` (only world 145's handler 8 uses one, and 145 has
  no capture).
- A capture of a render-time light (143 type 0x71 in view) needs a tile that is not a Warps destination.
- World 0x27's tower state comes from server messages (out of scope).
