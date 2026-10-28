# Recorded world particle consumers

RENDER-WORLDS-L, 2026-10-28, issue #231. Adds the downstream consumers requested by
Karutan and Raklion's verified primary methods, plus three small recorded Loren
Market consumers. Primary-world method coverage does not change.

## Provenance and evidence boundary

Target main.exe SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Pinned capture09 text at `0x00401000` has SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`;
run10 data at `0x01a7c000` has SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
The validator verifies both full inputs and reports engine/body hashes. These are
restored Linux/Wine instructions. No original client, launcher or new capture was used.

Verified means comparison with original instructions under Unicorn. Native host
checks and saved-render regressions are separate evidence. No original Karutan PNG
exists at the retained input path, so no original-image fidelity score is claimed.

## Verified consumers

All seven kinds use the existing common create initialization, owner refresh,
MovePosition, lifetime/time tail, mode/live filters and generic RenderSprite path.
The generic particle engines are create `0x015ae7b0`, move `0x01616c80` and render
`0x0159123f`. The new branches live in `reconstructed/particles/worlds_l.inc`;
`particles.c` adds only admission and create/move dispatch.

| Kind/subtype | Create branch | Move branch | Behavior after the shared operations |
|---|---|---|---|
| Karutan `0x801c/16` | `0x015f3a6a` | `0x0166a8ca` | Life 30, rotation r%360, scale 0.6 + argument, upward speed r%3+5. Shrinks 0.005, vertical speed minus 0.1, fades below life 8 and brightens above 20. Skips the common WATERFALL3 tail. |
| Raklion `0x8086/2` | `0x015d4350` | `0x01646965` | Life r%5+27, random scale/rotation/gravity and diagonal velocity; saved RGB with alpha ramp, shrink r%3+7, extra position advance and rotation +3. |
| Raklion `0x8087/6` | `0x015b911e` | `0x0162616c` | Life r%5+24, distinct y drift and shrink r%3+6; remaining structure matches the Raklion fire branch. |
| Raklion `0x8089/2` | `0x015d9243` | `0x0164bb15` | Life r%5+17, y drift as mono02, shrink as mono01. |
| Market `0x801e/0` | `0x015f1bf7` | `0x01667fae`, `0x0166886e` | Fixed scale 1.6 and RGB 0.2, falling speed r%5+7, shrink and vertical deceleration, life 8/20 light gates. |
| Market `0x801c/8` | `0x015f4466`, `0x015f48d5` | `0x01669dfc` | Initial RNG scale overwritten by another random scale; no argument-scale multiply, three-axis position jitter. Grows 0.05, speed minus 0.6, fades, skips common tail. |
| Market `0x801b/4` | `0x015f27cb`, `0x015f3084` | `0x01668de1`, `0x016691b4` | Keeps overwritten scale RNG and scene-5 tint, three-axis jitter, life 70 and final random size plus argument scale. Grows/drifts/fades and rotation minus 1.1. |

Raklion's creation scale is `(float(r%72+72) * 0.01f) * argument` in that order.
Its movement adds velocity again after the common rotated MovePosition. The
shared ramp fades below life 10, clamps alpha on the next high-alpha step and
kills below alpha 0.1 or nonpositive scale. No terrain, weather, keyed effect or
colored-joint state is invented.

### Bitmap loader mappings

Five original LoadBitmap sequences execute under Unicorn and verify the path,
index, LINEAR `0x2601`, CLAMP `0x2900` and flags `1,0`.

| Original call | Bitmap | Original filename | Native registration |
|---|---|---|---|
| `0x018220c5` | `0x7f6b` | `Effect\Shiny04.jpg` | New sprite registration |
| `0x01821b79` | `0x8086` | `Effect\firehik_mono01.jpg` | Existing registration retained |
| `0x01821b99` | `0x8087` | `Effect\firehik_mono02.jpg` | New registration |
| `0x01821bd9` | `0x8089` | `Effect\firehik_mono03.jpg` | New registration |
| `0x01822ac5` | `0x801e` | `Effect\WATERFALL5.jpg` | New registration |

Native Data uses the corresponding OZJ files. Existing slots remain stable;
the four new slots precede the two rain slots. Textures allocate at open time;
the consumers use existing fixed pools and add no per-frame allocation.

## Checks

`validate_worlds_l.py --mutations` passes **21,000 checks**: 7,000 create,
7,000 move and 7,000 render, with **zero mismatches/stops**. This is **19,390
original-instruction comparisons plus 1,610 native loop-head removal checks**.
Each kind has 1,000 inputs in every family. Directed lifetimes include -1, 0,
1, 7, 8, 9, 10, 11, 20, 21, 30 and 70, plus dead records; random fields cover
owner/no-owner, motion, signed-zero and finite scales/angles, scene flags,
bitmap component counts and mode/height filters. The comparison checks all
represented defined record fields, ordered service calls/RNG draws, GL state
and sprite arguments. Float comparison retains the existing particle oracle's
tolerance; this is not a new bitwise floating-point guarantee.

**13/13 separately compiled production-C mutants are caught**, covering scale,
lifetime, drift, fade thresholds, shrink rate, saved color, Market lifetime,
Market rotation and generic render rotation. Original instructions are never
mutated. Each family/mutant uses a fresh machine. Directed boundaries were added
after an initial random sample failed to exercise one threshold; a separate
mutation-site correction ensured the fade mutant changed the Raklion branch.

The native synthetic host passes seven consumers, four registrations, eight
rendered quads, 400 producer preparations, eight absent/unloaded-model checks,
seven particle-full checks and one sprite-full check, absent-asset drawing and
six unsupported-neighbor admission checks. It runs the real Karutan lamp/type-114
and Raklion type-70/80 producer callbacks into the particle module. Pool-full
behavior is a native bounded-pool policy; the original particle list is unbounded.
The existing J host separately retains its 3,600 preparations and missing-bone
refusal checks. Portable particle and prior effects tests remain green.

## Saved population regression

The saved fourteen-view tour uses installed assets, the existing October 22
object/light/camera inputs, 25 steps and frames 0/24 at 1722x1048. It streams
hashes and deletes unaffected images immediately. Against main `037a889`, all
**14 OBJECT and 14 light hashes** remain unchanged. All **26 PNG hashes across
13 unaffected views** remain unchanged, including Raklion. Karutan changes only
377 pixels at frame 0 and 692 at frame 24, in left-edge bounds respectively
`(16,223)..(90,275)` and `(0,91)..(41,182)`. These are intended new lamp/spray
pixels. The before/after Karutan and final Raklion frames were visually inspected;
pre-existing cyan spheres remain unchanged. Karutan accepts six previously
unsupported requests, created particles rise from 16 to 22, and final live
particles rise from zero to two. These counters describe the saved run only.

The saved Raklion view emits no particles. Its unchanged PNG proves regression
stability, not populated-emitter visibility. The synthetic native host exercises
both Raklion emitter types and all three consumed kinds. Karutan's saved camera
is also not complete coverage of every emitter. Original-to-native image error,
synchronized full pools and live temporal fidelity remain unmeasured.

## Remaining work and reproduction

Uruk weather/keyed/color consumers `0x806e/12` and `0x7f7d/13` are excluded.
Karutan `0x7f5a/69` and `/13`, other recorded nested consumers, the uncaptured
world populations, full historical RNG/pool phase and remaining primary methods
stay open. No new input needs retention.

Run `scripts/run_validators.py --private --only validate_worlds_l`, the
`native/tests/test_native_worlds_l.py` host/private tests and the full
`bash scripts/local-macos-ci.sh` gate. [Release and cleanup handoff](../handoffs/RENDER-WORLDS-L.md).
