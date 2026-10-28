# RENDER-EFFECTS-003

Implements Meteorite, Aqua Beam's ordinary-world primary chain and Inferno's
bursts in fixture session casts. Primary native routes rise **15/23 to 18/23**;
weighted primary coverage **46/77 to 56/77**. This is a subset milestone.
[Coverage inventory](../research/client-skill-visual-coverage.md),
[instruction evidence and limits](../research/client-render-effects-003.md).

Also supplies RENDER-WORLDS-K's five requested particle consumers and three
sprite assets. K owns the producer/world files. No live game, perf/mesh/scene,
item or audio-lane changes. Existing fixed pools and load-time textures are
reused; no per-frame allocations added. Checkpoints pushed at 01c0b39, 64e6f3d and 1b2be47.

## Verified checks before the merge lock

- New skills: 11,277 original-instruction comparisons plus 723 native removal
  checks; zero mismatches. 10/10 compiled production-C mutants caught.
- K consumers: 13,176 original-instruction comparisons plus 1,824 native removal
  checks; zero mismatches. 7/7 compiled production-C mutants caught.
- Four original LoadBitmap call sequences verified under Unicorn: 0x01821719
  Explotion01/0x7f54 plus the three K registrations at 0x01821599
  Magic_Ground2/0x7f84, 0x01822345 lightning3/0x7f38 and 0x01821f65
  Impack03/0x8021; exact paths, LINEAR/CLAMP and flags 1,0. The audit corrected
  the authored explosion asset path to the client spelling Explotion01.
- Existing skill/effect/voice corpus: 33,000 checks, zero mismatches. Historical
  particle corpus: 30,495 checks, zero mismatches. Its kind order remains fixed;
  the pre-existing mount-breath rounding difference remains unchanged.
- Reconstructed combat 38 tests and particles 23 tests pass with private checks.
  Native visual suite has five tests, including fixture casts and the native
  nine-quad consumer/registration host; private-enabled rerun passes.
- Fixture casts assert one unsent encrypted request each, unchanged target HP,
  zero invented hits/kills and zero unsupported emissions. Asset/pass removal
  changes rendered pixels. The three priority skills were also rendered with
  installed assets in headless OpenGL and visually inspected.
- Fire Ball software image at frame 21 is identical before/after, SHA-256
  `5b39b449dd20415a6981ad7c8071bec56e3e4dc9eec381eee71b8d81f77582a8`.
  Baseline cf81357 authored runtime sources were temporarily built in this owned
  worktree and restored before the after build. No main/other checkout was built.
  No existing hash pin changed. New skill and newly consumed world particles,
  sprites, RNG consumption and terrain lights intentionally change.

## Remaining work

Rageful Blow is still missing. Its lifetime-11/10 impacts at MoveEffect
0x01450a73 need 0x463..0x469, terrain rules and the owner-weapon renderer
0x01532bd2. No partial 0x461 port is retained. Buff auras, arrow/Death Stab trails,
master/later-class selectors and live original-image comparison remain.
Aqua Beam here is subtype 0 in ordinary worlds. Hero-only source-buffer
writeback/area requests and special-world wall cutoffs remain outside this
visual adapter. Model/caller selection retains the prior static evidence limit.
Particle sound is counted; actual delivery remains with AUDIO-002D.
K's producer placement is not certified by these consumer tests.

## Cleanup

Only existing ignored Python/evidence symlinks are used; none is staged. No new
private input needs retention. After merge, remove lane-local scratch/renders,
all worktree build outputs, this worktree and local branch. Durable evidence is
this handoff, finding and PR body. The final locked gate is recorded below; the final reply confirms post-merge cleanup.

Representative installed-data GL PNG hashes at frame 24, three images inspected
after correcting the explosion asset spelling. Meteorite and Inferno hashes
changed as intended because the explosion sheet now loads. GL checks draw every
frame while retaining only one PNG per skill (`--time-series-every 25`). This
avoids capture-only sprite accumulation: Aqua draws exactly twenty sprites on
frame 24. Its refreshed evidence hash reflects that render-check setting, not a
source change:

- Meteorite `bf321538a9a9bd09b11523be34ed318617ed6dbdf94cd5d07d0f2dfe6f2e82b4`.
- Aqua Beam `c52e2828443e2e006a46c40ceac936e1682789cb4e01640447759225920e8326`.
- Inferno `92963b3899acb731796bd115dba74c7d1ca36471de39f698cf8f05fd1084dffb`.

Five native tests pass with private checks enabled, including the nine-quad
registration host. Both new registered validators pass, zero failures/errors/skips.
The repeated-frame Aqua adapter test also passes: terrain-light buffers remain
equal without an intervening logic step and the beam disappears when its effect
ends. A separate compiled retained-frame-light mutant is caught (18 compiled
mutants total, seventeen against original instructions).
Own Standards and Spec diff review retains the explicit subset limits above and
finds no blocking issue in the implemented paths. Shared status edits are limited
to this milestone's additions. No delegated review or hosted workflow was run.

## Locked release gate

Acquired the queued merge lock at 12:43 CDT after SESSION-MAP-001a and removed
only this lane's queue entry. Integrated origin/main 4b21583. Resolved shared
documentation and appended Makefile/validator conflicts by retaining both lanes;
no incoming behavior was removed. The merge commit follows these checks.

`bash scripts/local-macos-ci.sh` passes: 38 unittest suites, 1,582 tests,
200 explicit optional/private skips, zero failures; 10/10 fixture scenarios;
native viewer and read-only reader builds; 1,530 audited files, zero rejected.
No hosted workflow or live game was run.

On that merged tree, all five native visual tests pass with private checks
enabled (zero skips), and both new registered validators pass with zero
failures/errors/skips. Fire Ball and all three representative PNG hashes above
remain identical after integrating main. The final diff is confined to the
implemented lane, its minimal hooks, tests, registry entries and documentation.
No new private input requires retention. All lane outputs are disposable under
the cleanup rule above.
