# APP-REFRESH-010

Progress checkpoint, 2026-11-08. Branch `codex/app-refresh-010`, worktree `worktrees/app-refresh-010`.
GPT-6.1 Sol. This checkpoint is not PR-ready; final proofs, checks and status lines follow.

## Installation and Native Data

Installed Native Preview from detached main `a55200e2`, including #344 and #346 through #350.
The bundle has real Ruffle, passes strict deep signature verification and `--check-bundle`, and records
`MUNativeCommit=a55200e2`. Installation waited for a running Preview process to exit; none was terminated.

Kept `~/Library/Application Support/MuTheMatrixNative/APP-REFRESH-006/Native Data`.
The export recipe, exporters, manifest code, pins, native data, GFx and app paths have no changes in
`a7f7b247..a55200e2`. Manifest check passes and the owner's settings match the saved copy.

Rollback is `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-010/`.
The APP-REFRESH-009 zip contains 66 entries, 11,788,703 bytes, SHA-256
`3dc834612794049e125c012bbf4c3a2e6c8711687006ee41ae800a72a505ccd4`, plus `settings.json.before`.
Older rollbacks are retained.

## Checks so far

- Root build: 30.06 s. World/client incremental build: 0.23 s. Real-Ruffle bundle: 2.02 s.
- Full private `native/tests`, from the root with private-env.sh and two jobs, once: 149 modules,
  1,001 tests, 981 passed, 18 skipped, two errors, 1,212.66 s.
- Both errors were ambiguous bow mutant anchors exposed by #350's exact-one-anchor assertion.
  Narrowed four anchors in `validate_render_effects12.py` and `validate_render_effects13.py` to their intended
  branches. Both affected modules now pass, 7 tests, 38.61 s, including 22/22 and 16/16 compiled mutants.
  No production code changed. Selection names exactly `validate_render_effects12`, `validate_render_effects13`
  and `validate_render_effects14`; final no-mutant runs remain.
- Installed no-Python smoke without/with audio: pass, 17.15/17.94 s, zero network attempts.
- Field cast/kill/drop/Space pickup: pass, 10.69 s. Audio peak 31,656, -0.300 dBFS, no samples above the ceiling.
- Headless travel and Hound/HUD: pass, 13.16/12.56 s; zero stale plates and zero HUD/session mismatches.
- Windowed travel: pass on Retina 3200x2000, 899 frames in 45.02 s, 35 matching HUD samples,
  zero network attempts. Window-only capture shows OFFLINE PREVIEW and 25.0 fps.
- Cape and wing 0x22ec comparisons with the rollback: visible changes confined to the fixture wearer.
- Windleaf fixture cast: pass, 121 effects and consistent 1119/778 vitals. Windowed proof remains.

## Visual findings to carry into the final handoff

The counter's command stream changes UVs: `0x0f2a` mesh 4 has u=0 at counter 0 and u=0.75 at counter 7.
Its native draw also has blend mesh 4 and blend light 0. Fixed-pose/time renders at different counters are
pixel-identical, including several other counter types. Ordinary pose animation is not a proof of counter-driven
atlas animation. The visual counter proof remains unverified; do not label it passed.

Raklion's type-0x14 object 1259 is at tile 196,215. Its particles project off screen at the old arrival 224,211.
At 198,211 they project into the window. The installed client shows the statue and its spray in early frames;
later samples do not retain that view. A private control removes only record 1259 from a scratch copy of
EncTerrain58.plain. Canonical Native Data is unchanged. Final particle-only control and proof crops remain.

## Scope and pending work

Offline only. No original client, launcher, owner Wine app, staged Wine app, network service, protection module,
password or memory write was used. Fixture changes are private diagnostic inputs and are not installed.

Finish windowed Windleaf, the Raklion particle-only control, retained small proof PNGs, final validator and
rule-6c checks, research/status documentation, PR and ready line. Cleanup follows the ready line; keep the worktree
until the steward merges.
