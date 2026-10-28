# RENDER-WORLDS-M

Implements Uruk's nested particle consumers `0x7f5a/69`, `0x7f89/25`, `0x801b/7`, `0x8184/2`,
`0x7f5a/22` and `0x7fd5/0`, and registers `0x8184` as `Effect\flare_mono`. The Loren Market and
Raklion kinds listed in this lane's brief were already merged by RENDER-WORLDS-L (#238) and were
skipped. [Finding, provenance, checks and limits](../research/client-worlds-m.md).

Owns `reconstructed/particles/worlds_m.inc`, the validator, native host/test and minimal shared hooks:
admission, create/move dispatch and one render call in `particles.c`; one bitmap id/file plus the two
counts in `mu_particles.{c,h}`; the shifted slot indices in the L and consumer hosts and the installed
60-slot expectation. No world producer, weather feed, item, session or audio change. Worktree created from
origin/main `fa63719`; ignored Python/evidence links are never staged.

## Evidence before the lock

- 18,000 checks, zero mismatches/stops: 17,052 original-instruction comparisons and 948 native
  head removals; six kinds, 1,000 cases per kind and family.
- 17/17 compiled authored-C mutants caught; four original loader calls equal.
- Native host: six consumers, one registration, six quads, 800 real Uruk producer preparations, 16
  missing-model, six full-pool, six unsupported-neighbour checks, absent assets, weather 1 vs default 0
  with the keyed refusal still counted.
- Registered validators `validate_worlds_m`, `_l`, `_i`: 3 pass. Particle/world suites (particles,
  worlds H/I/J/K/L/M, render effects, reconstructed particles): 41 tests pass, one private skip.
- Saved tour against `fa63719`: 16 views (14 October 22 + 2 DATA-ACQ-002 world 79), all 32 PNG,
  16 OBJECT and 16 light hashes unchanged. Authored Uruk view: unsupported 47 → 0, created 3 → 50;
  three images inspected and kept under `native/renders/render-worlds-m/`.

## Remaining work

`0x7fdd/3` is RENDER-EFFECTS-004's. The Uruk weather feed, keyed `0x806e/12` and coloured `0x7f7d/13`
consumers, a world-100 capture/original image and phase evidence remain open. When DATA-ACQ-002 adds
a world-100 read (`*-mem-01cf15ec.bin`), a saved Uruk population regression can reuse the tour method.
World-handler-coverage counts do not change.

## Integration and cleanup

After merge remove `mu-mac-tools/native/{scratch,renders}/render-worlds-m`, the worktree builds
(`native/build-base`), the worktree and local branch. No new retained INPUT is required.
