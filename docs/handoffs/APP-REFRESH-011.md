# APP-REFRESH-011

Implementation handoff, 2026-11-09. Branch `codex/app-refresh-011`, worktree `worktrees/app-refresh-011`.
GPT-6.1 Sol. Offline Native Preview refresh. The app is built detached at main; the documentation branch is separate.

## What the installed app now has

Native Preview is installed from latest main `54a53e1a`, #360. It includes #353's opaque captures,
CLI inventory overlay fix and opt-in accessory fixture; #354's counter-gated mace particles and rank-5
world callers; #355/#360's 1,404 admitted item bodies and visible `0x0f2a` blend-light input; #356's rebuilt
GFx clock library; #357/#359's mace particles, rings, sprites/textures and Ferea fire; and #358's NPC/monster cloths.

## Installation and rollback

Rollback folder: `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-011/`.
The prior APP-REFRESH-010 app and owner settings are preserved before building.
The zip passes `unzip -t`; SHA-256 `820e1d6967e507cdef73b65797702e64d3f96f35000477812856c15e7ab4c667`.
The app was built detached at `54a53e1a2d0001f37e4331d390043d5fc0dffe6e`, then installed with `ditto`.
No Preview or mu-client was running. The former app was moved into scratch with a restore-on-error path.
Strict deep signature and bundle checks pass. Owner settings remain byte-identical to `settings.json.before`.

Raw GFx artifact: `~/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx-frame0.dylib`, SHA-256
`eaf39b722e34e6d6f2eae34378bbac67d5004d2b4a9be8de005df3edd26a1645`, checked before bundling.
The installed `Contents/Frameworks/libmugfx.dylib` digest after rpath fixup/signing is
`8a20a369a93e211fe6e3431b54bc3d3fd74e3c1c8d1c5ba647c70fbe3d6ed70e`.

## Native Data kept

The export inputs are unchanged in `1e2a927a..54a53e1a`. Keep
`~/Library/Application Support/MuTheMatrixNative/APP-REFRESH-006/Native Data` after manifest verification.
The bundled manifest tool passes. The set has 179 GFx movies, 31 text tables, 47 object files and a sound table.
The diff is empty over the export recipe, its exporters/imports, `native/data` and `native/app`.
Only three `native/gfx` files changed: the window helper's Makefile adds mu_perf.c, the Cargo helper locks/caps
build jobs, and the window helper saves opaque captures. Neither gfxconvert, mugfx source nor Ruffle patches
changed. No new export or `--setup` was needed, and no canonical data was modified.

## Full private native/tests

One full run at `54a53e1a`, from the repository root with private-env.sh and `MU_GATE_JOBS=2`:
155 work items, 1,038 tests, 1,019 passed, 16 skipped, three failures, no errors; 1,354.85 s wall.
All three failures reproduce together in 5.01 s.

The cloth cadence fixture wore weapons with pre/owner programs whose random consumption depends on saved
draws. Removing weapons from this cloth-only fixture preserves its cloak assertions and makes the final PNGs
identical. The world pre-draw and armour-owner fixtures each contain a Dark Lord. CLOAK-003 adds a 6x5 energy
cloth flare pass on each of their two saved draws, exactly 60 extra sprites. A plain Dark Lord with no items
confirms 60 sprites, zero particles and no item programs. The exact totals are updated to 170 and 94;
request/refusal, random-call and particle assertions are unchanged. No production source changed.

The affected non-instruction classes pass 23/23 in 11.89 s. The three unchanged instruction/mutant tests
already passed in the full run and were not repeated. The full private suite was run only once.

## Standard journeys on the installed app

Pending.

## New proofs

Pending.

## Checks and wall times

Pending. No full lane gate. Rule 6c light checks and the APP-REFRESH full private exception apply.

Steward validators: none (docs, rule 6c).

## Follow-ups

Pending proof results. The 270 remaining item bodies, exact Hammer14 bone-name refusal, clouds/28,
unavailable placements and existing offline domain limits remain.

## Cleanup and delivery

Keep the rollback zip, settings copy and 3-6 small window-only proof PNGs. Delete lane scratch, raw frames,
WAVs, helpers and build outputs after the ready line. Keep the worktree until the steward merges.
No pushes after the ready line. The MERGE-STEWARD owns merging.
