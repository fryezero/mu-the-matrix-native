# RENDER-WORLDS-C2: persistent Icarus cover and emitter ribbons

Worktree `~/Documents/MTM/worktrees/render-worlds-c2`, branch `codex/render-worlds-c2`, based on #181.
No live client or launcher was started, stopped, driven or read. Only pinned instructions, installed assets
and the surviving 2026-10-22 snapshots/image were used. No changes in `native/world/**`.

## Changes and diagnosis

- RenderObjectVisual's world-10 types 0..5 create persistent owner-linked clouds in `reconstructed/objects/icarus.c`.
  The native visual hook consumes those events. The hidden-type snapshot sidecar no longer pre-hides those six
  source types before they can emit. The verified visual handler hides them after creation.
- `reconstructed/particles/icarus_clouds.inc` implements cloud subtypes 0..5. Source visibility refreshes lifetime;
  expiry resets HiddenMesh so re-entry recreates the cover. The shared renderer now receives WorldTime and the
  particle ordinal, and uses the correct direct light for these subtypes. Login mist subtype 20 is unchanged.
- `reconstructed/joints/icarus_joints.inc` implements `0x472/1`. The native environment routes all ten emitter
  requests into the existing joint pool, with distinct boid owner handles, position updates and owner death.
- The Icarus ambient clock now advances once per logic step. The original writer `0x01851f82` increments its
  integer counter once per 40 ms update. Feeding it milliseconds made the native ribbons jump rapidly. Initial
  native phase zero is a host choice; the original capture's counter value is unavailable.
- The rare sky cloud model, persistent cover, puffs and ribbons remain separate systems. No spawn, opacity,
  lifetime, colour or blend-factor tuning was used to fit the screenshot. Full findings and address boundaries
  are in `docs/research/client-world-fidelity.md`, section 6.

## Checks

- Registered C2 comparison: 7 families at 1,200 cases each, **8,400 equal, zero mismatches/stops, 8/8 compiled
  mutants caught**. Cover producer; all six cloud create/move/render paths; emitter create/move/render. Sources
  are frozen before compilation. Source visibility 0/1/2, hidden guards/reset, render parity, signed/wrapped
  clocks, target lifetime and the ordered host/GL calls are compared.
- Existing registered Icarus comparison: **5,240 equal, zero mismatches/stops, 8/8 compiled mutants caught**.
  Includes the earlier 40 dragon sessions. Its original stub and host-trig limits still apply.
- Broad shared regressions: particles create/move/render 1,200 each, **3,600 equal**; all 12 applicable negative
  controls detected, ten controls belong to unselected families. Joints create/move/render 660 each,
  **1,980 equal**, all 9 existing negative controls detected.
- Synthetic native host checks: sidecar initialization; create once; 80 visible ticks; source invisibility and
  expiry/re-entry; actual environment-to-joint route; distinct boid targets; owner death; logic clock independent
  of elapsed milliseconds. Tour mask test checks intersection with the HUD exclusions, area and empty/wrong-size
  masks. The registered tests retain explicit private-input skips in the portable gate.
- Final local gate: pending combined-main run. An earlier attempt exhausted disk while writing the consecutive
  full-resolution frame set. Its errors were file writes/temporary-directory allocation; owned renders were
  compressed/trimmed before retry. No external worktree or client data was removed.

Commands from the worktree:

```sh
MU_RECOVERY_INTEGRATION=1 tools/python/bin/python scripts/run_validators.py --private \
  --only validate_icarus_c2,validate_icarus --jobs 1 --report "$C2_SCRATCH/registered"
tools/python/bin/python scripts/validate_particles.py --cases 1200 \
  --only create --only move --only render --output "$C2_SCRATCH/particle-regression.json"
tools/python/bin/python scripts/validate_joints.py --cases 660 --output "$C2_SCRATCH/joints-final.json"
bash scripts/local-macos-ci.sh
```

`C2_SCRATCH=~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-c2`; renders are in the corresponding
`native/renders/render-worlds-c2` directory. `registered-final/` holds the final C2-only registered rerun after
portable suffix/report-counting cleanup. Local `ablate.py` builds diagnostic libraries and binaries outside
production build paths; it never edits production sources or objects. Draw-only variants suppress persistent
cover, emitter ribbons, dragons, puffs or swirls without changing the simulation or RNG stream.

## Fidelity

Same surviving full-resolution image, camera, tile 15,13, HUD/hero exclusions and raw tour metric throughout:

| Steps | Before #181 | #181 | C2 |
|---|---:|---:|---:|
| 25 | 61.760 | 62.030 | **26.897** |
| 400 | 54.673 | 60.935 | **27.663** |

At 25 steps the #181 changed-pixel mask covers only 0.957% of scored pixels; its error rises 29.802 to 58.026,
accounting for +0.270 overall, with the complement unchanged. At 400 steps that mask covers 46.860%, with error
59.271 to 72.617; the complement changes only 50.617 to 50.633. Added sky RNG changes the puff distribution,
and dragons and ribbons have uncaptured phases. This explains the score regression without treating the
previous instruction comparison as a visual match.

C2 without only the cover scores 61.798 / 60.919. Cover masks span 96.58% / 96.44% of scored pixels. Omitting
puffs at 400 steps improves error by 0.862, while omitting swirls worsens it by 0.125. Thus a still-image score
can reward removing correct moving elements. No such exclusion is used for C2's passing score. Optional
`element_masks` in the tour report pixel area and region scores alongside the unchanged whole-scene score.

The frame-by-frame study measured 307 consecutive full-resolution native frames, indices 0..306, against the
surviving still: min 26.481, max 32.609, mean 28.691. The 400-step endpoint is separate. The local report retains
all 307 score rows; selected images remain after storage cleanup. This is a native phase study against a still,
not an original-client time-series comparison. All thirteen other capture final-frame PNG hashes are unchanged
for C2 in isolation against #181. No renders, masks, snapshots, raw client bytes or decoded tables are committed.

Reproduce the local study with `scripts/icarus_fidelity.py --help`; use `tour25.json`, `tour400.json`, the local
ablations and the earlier `renders/render-worlds-c` baseline. Reports and per-element masks are local only.

## Limits and next work

- The capture lacks the complete particle/joint/sprite/boid pools, CRT RNG state and ambient counter at the shot.
  Native subsystem seeds and fresh-world phase are host choices. Exact animation phase remains unverified.
- The event-world joint predicate is false for world 10; the joint's separate character resolver answers absent
  in the comparison. Non-Icarus `0x472` subtypes are not ported. Host trig follows the prior joint boundary.
- World-10 object type 10's bone flare remains outside this slice. The tour's hero equipment is masked.
- This run makes no new live-game, gameplay or temporal-equivalence claim. Lanes A/D own sibling-world flames,
  after-character rendering and other-world fixes. A later separately authorized capture can settle the exact
  phase by acquiring those missing pools and clocks at the same frame as the screenshot.
