# RENDER-WORLDS-N

Nixies Lake (113) and Deep Dungeon 1–5 (116–120) primary create/move/visual methods.
[Addresses, provenance, fidelity numbers and limits](../research/client-worlds-n.md).

- Claude Opus 5.5 lane. Worktree `~/Documents/MTM/worktrees/render-worlds-n`, branch `claude/render-worlds-n`, from
  origin/main `d4b6a11`. Input links `tools/python` and `evidence` from the main checkout, never committed.
- New per-world C `reconstructed/objects/nixies_lake.c`, `deep_dungeon.c`, `worlds_n.h`; dispatch lines in
  `object_render.c`; one refusal line in `native/core/mu_objects_runtime.c`; build lines in both Makefiles.
- Coverage **33 → 52/144 primary methods; 11 → 18/48 classes**; zero static-only, 92 missing. World 115 counts
  only through the shared visual entry.
- `scripts/validate_worlds_n.py`: thirteen families, **13,000 cases equal, zero mismatches/stops,
  29/29 compiled mutants detected**. Registered as `validate_worlds_n`.
- Portable `reconstructed/objects/test_worlds_n.py` (3 tests + 1 private) and production host
  `native/tests/worlds_n_host.c` via `test_native_worlds_n.py` (6 worlds + sibling 112, 200 steps each).
- Saved-population regression at the six DATA-ACQ-002 arrival tiles: all **13,690 range and 436 after-character
  differences → 0** (28,687 objects, zero missing/extra), primary light still exact. Image mean |Δ|:
  113 7.001 → 7.001, 116 5.745 → 5.570, 117 4.453 → 4.081, 118 14.168 → 13.475, 119 10.017 → 9.440,
  120 6.353 → 6.665 (worse: new class lights on blocks the native world draws untextured; inspected).
- October 22 fourteen-view tour, base vs lane binary: **28/28 PNG, 14/14 OBJECT, 14/14 light hashes identical**.
- Keyed CreateEffect 0x43a (Deep Dungeon type 52) is refused and counted, left for the effects lane.

No original client or launcher was started; no live read was needed. No service, wire, protection-module,
shared particle/effect hook, item or session change. Only authored C/Python, synthetic fixtures and reviewed
summaries are committed.

Remaining: the keyed-effect consumer; world 115 create/move (static `xor al, al; ret 4`, no capture); the default
hook chain after false returns; custom/after/invisible slots; textures and brazier visuals that dominate the
Deep Dungeon image error; 92 other primary methods (RENDER-WORLDS-O takes Abyss of Atlans 128–130).

During the lane, reports and the six-capture renders were under `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-n`
and `renders/render-worlds-n`; both are deleted after merge with the worktree and branch. The DATA-ACQ-002 inputs
were only read. No new local input needs retention.

## Checks

Merge lock taken at 18:38 CDT (queue empty). Latest main `f5a3199` (including RENDER-WORLDS-M and NATIVE-PERF-004)
merged as `a326169`; conflicts in `native/Makefile`, `scripts/validators.toml` and the three status docs keep
both sides. On the merged tree:

- `bash scripts/local-macos-ci.sh` passes: **1,650 tests across 38 discovery runs, 211 explicit skips, zero
  failures/errors; 11/11 fixture scenarios; native viewer and reader builds; publication audit 1,616 files,
  zero rejected**. Readers built only. No hosted workflow dispatched.
- Registered private G/H/I/J/N: **5/5 pass, no errors/skips** (N: 13,000 cases, 29/29 mutants).
- `world_handler_coverage.py`: 48 classes, 57 registrations, 288 addresses; 52/144, 18/48.
- N portable tests 3 pass + 1 private skip; native N host passes.

Only this checks section changed after the gate.
