# Uruk nested particle consumers

RENDER-WORLDS-M, 2026-10-28. Adds the six downstream particle lifecycles that Uruk's verified
visual handler `0x00e6f3d5` ([world I](client-worlds-i.md)) requests, plus one load-time bitmap
registration. The Loren Market `0x801e/0`, `0x801c/8`, `0x801b/4` and Raklion `0x8086/2`,
`0x8087/6`, `0x8089/2` consumers in this lane's original scope were already merged by
[RENDER-WORLDS-L](client-worlds-l.md) and were skipped. Primary-world method coverage does not change.

## Provenance and evidence boundary

Target main.exe SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Pinned capture09 text at `0x00401000` has SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`;
run10 data at `0x01a7c000` has SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
The validator verifies both inputs and reports per-body hashes. No original client, launcher or new
capture was used. Verified means comparison with original instructions under Unicorn. Native host checks,
saved-capture regressions and the authored Uruk view are separate evidence.

Branches were located by tracing the original create `0x015ae7b0`, move `0x01616c80` and render
`0x0159123f` engines under Unicorn per kind and disassembling the blocks that only that kind executes.

## Verified consumers

All six use the common create initialization, owner refresh, MovePosition, lifetime/time tail and the
generic RenderSprite path. Code lives in `reconstructed/particles/worlds_m.inc`; `particles.c` gains only
admission, create/move dispatch and one render hook.

| Requester | Kind | Create | Move | Behavior |
|---|---|---|---|---|
| Uruk 89/93 | `0x7f5a/69` | `0x015c92c4` | `0x0163a666` | Life 60, scale `(r%64+64)*scale*0.005`, gravity `(r%16+30)*0.1`. Copies the requested light into the angle; each step light = life/50 times that saved colour, gravity −0.04, x drifts by `sin(WorldTime)*gravity*0.05`, z rises by gravity, scale +0.04. |
| Uruk 108 | `0x7f5a/22` | `0x015c6af3` | `0x0163685b` | As subtype 21 with life 60; light `(0.9, 0.5, 0.5)·life/50`, gravity −0.1, same drift/rise/growth. |
| Uruk 90/91 | `0x7f89/25` | `0x015ed94f` | `0x01661b07` | Subtype-0x14 mist sheet with ±100 instead of ±250 x/y jitter; rises +2 while life > 150, then sinks −1 and fades. Render `0x01599629` draws light × alpha. |
| Uruk 92 | `0x801b/7` | `0x015f29c6` | `0x0166920a` | Life `r%50+20`, gravity `r%20+10`, scale × 0.2, start = position. Each step skips the life-10 fade, adds `r%5 + life/5·1.5` to gravity, pushes velocity x by `1 − 20/life·100`, spins +50, tints by (0.8, 0.77, 0.77), resets position to start, lifts start z by `r%5+10` and sets z = start z + gravity. The rotated velocity offset is computed and then overwritten, as in the original. |
| Uruk 106 | `0x8184/2` | `0x015f96f1` | `0x016725c5` | Ignores the scale argument: scale `r%100/300 + 0.2`, life `r%10+30`, white, rising speed `r%100/50`. Each step shrinks by /1.05 (double), speed +0.4 clamped at 8, fades /1.2 below life 15. |
| Uruk 108 | `0x7fd5/0` | `0x015faa34` | `0x01673f85` | Life `r%20+70` saved as initial life, rotation = raw rand, saved scale argument, scale `(|cos(r)|+1)·0.0075·scale` (double), saved colour. Each step traces a spiral: `(cos t·s·k, sin t·s·k, t·s)` with t = time·π, k = life/initial life, rotated by the record angle through `0x0185c113`, plus start; rotation += t·k·4, alpha = sin(k·π), light = alpha × saved colour. |

`0x0185c113` is an Euler rotation by degrees without a matrix (cos/sin of each angle, then `memcpy_s`);
it is reconstructed inline with the original multiply/add order. Float comparisons use the existing
particle oracle's tolerance; this is not a new bitwise floating-point guarantee.

### Bitmap loader mappings

| Original call | Bitmap | Original filename | Native |
|---|---|---|---|
| `0x0184119c` (world loader, with clouds and `0x7fdd`) | `0x8184` | `Effect\flare_mono.jpg` | New registration `Data/Effect/flare_mono.OZJ` |
| `0x01841323` (another world case) | `0x8184` | `Effect\flare_mono.jpg` | Same file |
| `0x01833b80` | `0x8184` | `Effect\flare_mono.jpg` | Same file |
| `0x01822385` | `0x7fd5` | `Effect\Spark01.jpg` | Existing joint slot retained |

All four calls execute under Unicorn and match path, index, LINEAR `0x2601`, CLAMP `0x2900` and flags
`1,0`. Because every `0x8184` site loads the same file, native registers it unconditionally. Existing
slots stay stable; the new slot precedes the two rain slots (60 bitmap slots, 58 effects).

## Checks

`validate_worlds_m.py --cases 1000 --mutations` passes **18,000 checks**, 6,000 per create/move/render
family and 1,000 per kind in each, **zero mismatches or stops**: **17,052 original-instruction
comparisons plus 948 native loop-head removals**. Directed lifetimes cover -1, 0, 1, 2, 9, 10, 11, 14,
15, 16, 149, 150, 151, 299, 300, 60, 70 and 89 plus dead records; the spiral additionally draws
initial lifetimes 70/80/89/life+1. Random fields cover owner/no-owner, scene 3/5/6, motion, signed-zero
and finite scales/angles, bitmap components and the mode/height filters.

**17/17 separately compiled production-C mutants are caught** (lifetime, gravity, saved colour, fall,
tint, mist spread/rise/alpha, burst life/push/tint, flare scale/cap/fade, spiral scale/Euler sign/spin).
Original instructions are never mutated. Each family and mutant uses a fresh machine.

The native synthetic host (`native/tests/worlds_m_host.c`) creates and draws all six kinds (six quads),
checks the `flare_mono` slot by distinct fixture dimensions and sampling, and runs the real Uruk
visual for types 89, 90, 91, 92, 93, 106 and 108 into the particle module: **800 producer
preparations**, zero unsupported particle requests, 16 missing/unloaded-model checks, six full-pool
checks, six unsupported-neighbour admissions and absent assets. Type 108 runs once with the explicit
weather input set to 1 and once at the default 0. With weather 1 the keyed `0x806e/12` request is still
counted as `draw_unsupported` (41 refusals in the run); with weather 0 it emits nothing.

## Saved population regression

No world-100 capture exists yet (DATA-ACQ-002 has world 79 but not 100), so no Uruk population or
original Uruk image is claimed. Baseline `fa63719` and this branch were built in this worktree and run
with the installed data, 25 steps, frames 0/24, 1722×1048:

- the fourteen October 22 views and the two DATA-ACQ-002 world-79 views (Loren Market, Event Square):
  **all 32 PNG, 16 OBJECT and 16 light hashes unchanged**, zero unsupported requests in both builds. The
  Market capture populates L's consumers (30 created, 23 drawn), unchanged by this lane;
- an **authored** world-100 plaintext (12 emitters of types 89–94/106 on a ring at the default hero
  tile, not client placement), 40 steps at 1280×720: unsupported requests fall **47 → 0**, created
  particles **3 → 50**, drawn **47**. Frames 13 and 39 were inspected: the red glow/bursts and the faint
  blue type-91 mist now appear; the pre-existing type-94 spray is unchanged.

## Limits and continuation

- `0x7fdd/3` (type 105) belongs to RENDER-EFFECTS-004 and stays unsupported here.
- Uruk weather `0x01cf15ec` remains an explicit input, default off. The keyed `0x806e/12` and coloured
  `0x7f7d/13` requests remain counted refusals; no key/colour is dropped. `0x7f5a/22` and `0x7fd5/0`
  only appear in a real session once a weather feed exists. A DATA-ACQ-002 world-100 read of
  `0x01cf15ec` was not available while this lane ran.
- Original-to-native image error, exact RNG/pool phase and live temporal fidelity remain unmeasured.

```sh
tools/python/bin/python scripts/validate_worlds_m.py --cases 1000 --mutations --output <local-json>
MU_RECOVERY_INTEGRATION=1 tools/python/bin/python scripts/run_validators.py --private --only validate_worlds_m
tools/python/bin/python -m unittest native/tests/test_native_worlds_m.py
```

[Release and cleanup handoff](../handoffs/RENDER-WORLDS-M.md).
