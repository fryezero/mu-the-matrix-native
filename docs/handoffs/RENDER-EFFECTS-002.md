# RENDER-EFFECTS-002

Adds player Poison smoke, target Ice with five debris pieces, and player Power
Wave to the fixture combat/skill visual path. Poison01's monster-only model
create/move cases are also compared, but their monster caller stays unwired.
No network, perf/mesh/scene or joint implementation changes. Fixed pools and
load-time model resources are reused; no per-frame allocations added.

The [coverage inventory](../research/client-skill-visual-coverage.md) records all
23 native cast routes, explicit partial/missing cases, levels/class exposure,
priority assumptions and sixteen classes' remaining candidate groups. Primary
coverage rises 12/23 to 15/23; weighted primary coverage 37/77 to 46/77. These are
bounded native-route counts, not coverage of all 973 snapshot skill records.

Checkpoint verification:

- 11,000 focused original-instruction comparisons, zero mismatches. Eight compiled
  production-C mutants detected, with individual disagreement counts in the finding.
- 33,000 existing skill/effect/voice comparisons, zero mismatches.
- Two native tests pass with private checks enabled. Three synthetic fixture casts
  check emitted types/counts, rendered pixels, no unsupported emissions and one
  unsent encrypted request each, with zero invented hits/kills. Existing combat
  library tests: 38 run, two skips; particles: 21 run, one skip.
- Registered focused validator: one pass, zero failures/errors/skips.
- Installed-data headless GL images: Poison ten particles; Ice six models and
  eight particles; Power Wave one model and 32 particles at the saved sample.
  Zero unsupported emissions in each. Three images visually inspected.
- Fire Ball software image before/after SHA-256 is identical:
  `e12fd7edf565caafc2e4f159e3a2d8b205d363e7436d3666ffae4160494c18dc`.
  No existing hash pin changed. New cast pixels/RNG/lights intentionally change.

Local inputs are the existing evidence/Python symlinks and existing `skill3/lang`
snapshot summaries. They are never staged. Scratch and the five representative
renders are lane-local and will be removed after merge, together with this
worktree, branch and build outputs. No new private input needs retention.

Remaining: Meteorite subtype 0, Aqua Beam, Rageful Blow, Inferno's burst,
buff auras, arrow/master/later-class variants and live image comparison. The
checked GFx bar shares the adapter, but this milestone's session test drives its
fixture combat route rather than replaying the bar UI. Original model rendering
and caller selection retain their explicit static evidence limits.

The unchanged particle regression corpus passes 30,495 cases, zero mismatches.
An exploratory insertion into its kind ordering exposed two pre-existing 1-ULP
Ghost Horse breath move differences. Compiling `a38ec75` particles.c and replaying
the same expanded inputs reproduces both at cases 1619/2339, 40/42 breath cases
equal. The original regression corpus is preserved; the new Poison kind has its
own focused corpus. Breath precision is a separate remaining issue, not fixed or
included in this milestone's zero-mismatch claim.
