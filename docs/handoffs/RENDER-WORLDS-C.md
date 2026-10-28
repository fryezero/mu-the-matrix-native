# RENDER-WORLDS-C: Icarus sky and dragons

Implemented the named Icarus instruction paths on branch `codex/render-worlds-c`. No original client or launcher
was started, stopped or read. Only the pinned instructions, installed assets and existing 2026-10-22 captures
were used. No changes in `native/world` or the sibling world-handler cases.

## Implementation and proof boundary

- `reconstructed/objects/icarus.c`: sky `0x018016b0..0x01802168`, and the world-10 slice
  `0x0180249e..0x01802692`. Expanded light/effect/sprite/joint events preserve argument values and MSVC random
  call order. The previous MoveObjects ordinal feeds the sky selector. The runtime runs sky before puff creation,
  then the object calls in their existing sector-list order.
- `reconstructed/joints/icarus_joints.inc` and two small cases in `joints.c`: `0x7f7c/6` swirls and
  `0x7f7d/0` lightning, including tail construction, target motion, the last-four-step swirl build, bolt fade and
  per-segment colour. The earlier finding's "subtype 10" was incorrect; the sky's actual argument is zero.
- `reconstructed/environment/env_icarus.c`: `0x00ca2154` in world 10, three dragons `0x7c4`, plus the accompanying
  ten `0x472` emitter records and their `0x00ca3189` mover. Shared flight/steering/animation remains in the existing
  environment module. The emitter joint requests remain counted by the existing native host; their `0x472/1`
  joint family is outside this port. World `0x84` is unchanged.
- `native/core/mu_objects_icarus.*`: consumes the events into native light/effect/sprite/joint hosts, with bounded
  event storage. The particle host loads `Object11/cloud.bmd` and `Effect/cloudLight.OZJ`; the environment loads
  `Monster32.bmd`, the file requested by OpenMonster(31). Existing texture and effect-model slots are preserved.
- The character-select object rule now depends on the actual core header list. Its former undefined `CORE_HDR`
  dependency kept stale objects after these structure additions; the character-select lifecycle checks pass after
  the corrected incremental rebuild.

The Unicorn families compare compiled production C with the actual pinned instructions. Engine calls are
recording stubs. Vector accessors, AngleMatrix, VectorRotate, tail shift and humming execute as client code;
CRT trig follows the earlier joint/environment validators. MSVC random return values and call counts are
compared, not guessed from a screenshot. These checks do not replay the captured client's random state.

## Checks

- Registered `validate_icarus`: sky 2,000, object 2,000, joint create/move/render 400 each, and 40 Icarus world
  sessions. Total 5,240 comparisons, zero mismatches or stopped cases; 8/8 compiled mutants caught. Each dragon
  session runs 20 ticks, alternates clean and fuzzed pools, and includes directed warps. The suite freezes its
  C sources before compiling so concurrent merges/builds cannot change a comparison halfway through it.
- Broad joint regression: 660 cases per create/move/render family, 1,980 equal, 9/9 existing negative controls.
- Existing effect create/move regression: 600 per family, 1,200 equal. The puff single-move mistake differs in 18
  cases. These are existing effect families, separately from the eight compiled Icarus controls.
- Native synthetic host: sky light/effect/joint events, cloudLight sprites, object ordinals, Monster32 mapping,
  and production sky-before-puff RNG order. The fixture explicitly marks its object runtime ready.
- Final local macOS gate: pending.

Reports are local under `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-c/`, with the final scoped
report and runner summary in `final-registered/`.

## Fidelity and remaining work

The same 2026-10-22 Icarus capture was compared at 1722 × 1048, tile 15,13, against baseline `fecdddd` and this
implementation. The original window PNG is the local audited README source copy
`renders/readme-sources/18--fidelity2_live_10-icarus.png`. Several other historical live PNGs are absent, so those
maps have render hashes and object/light comparisons without a new image-error number.

Initial results: 25-step mean absolute image difference 61.760 → 62.030; 400-step 54.673 → 60.935. These are
regressions, not fidelity improvements. Sky random calls change the puff distribution, and the native seeds are
not the captured client's state. The named cloud/lightning/sprite/swirl paths are implemented, but do not explain
or reproduce the persistent grey coverage of the live capture. Dragons and cloud lights are visible. All thirteen
other capture hashes are unchanged at both sampled frames of the 25-step tour.

The persistent grey layer remains an explicit gap. Do not increase cloud frequency, lifetime or opacity to match
one screenshot: that would contradict the verified code. A later bounded capture needs the full joint/sprite
pools and attached effect trees at the same frame as the screenshot, together with the effect pool and RNG state,
to identify the remaining producer and reproduce its phase. No new live capture was made in this milestone.

Local renders and scoreboards stay in `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-c/`.
