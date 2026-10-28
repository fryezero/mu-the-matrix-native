# Loren Market and Uruk Mountain primary handlers

RENDER-WORLDS-I, 2026-10-28, issue #209. The three primary methods for worlds 79 and 100 are implemented
in `reconstructed/objects/loren_market.c` and `uruk.c`. The [inventory](world-handler-coverage.md) has
31/144 verified primary families across 11/48 classes, zero static-only entries and 113 missing methods.
The factory, constructors and all 288 slot addresses still agree with the 48-class, 57-registration inventory.
Custom-render, after-render and invisible-sector slots remain separate.

## Selection and provenance

Loren Market is a recurring hub and Uruk Mountain is a progression map. Selecting them ahead of the larger
remaining event classes is an implementation judgment; no player visit-frequency data was collected.
The retained fourteen-view tour has no uncovered concrete class outside the A-H exclusions. Neither new
class has saved live objects or an image. Synthetic objects therefore establish method behavior, while
DATA-ACQ-002 remains necessary for their populated scenes. No excluded world implementation changed.

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Capture09 text at `0x00401000`, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
Run10 data at `0x01a7c000`, SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
The validator checks both whole-file pins and records each method range and digest. This is restored
Linux/Wine x86 evidence, not a new live observation or native Windows evidence.

| Family | Original half-open range | Cases |
|---|---|---:|
| Market create | `0x00e6c0ec..0x00e6c1bf` | 1,000 |
| Market move | `0x00e6c1bf..0x00e6c678` | 1,000 |
| Market visual | `0x00e6c678..0x00e6ce2d` | 1,000 |
| Uruk create | `0x00e6f0a2..0x00e6f1ca` | 1,000 |
| Uruk move | `0x00e6f1ca..0x00e6f3d5` | 1,000 |
| Uruk visual | `0x00e6f3d5..0x00e702eb` | 1,000 |

## Verified behavior

Market create disables light on types 50/51/52/53/59, registers 67 with box maximum 100/100/160 and hidden
mesh -2, and sets type 68's after-character byte. It always returns false. Move requires world 79, performs
its own alpha step and model gate, sets type 8's velocity to 0.2, hides 54..58 and emits bone-based terrain
light for types 30/35. The class alpha step follows the existing generic alpha/tick path; omitting that
second step changes the original behavior. Move's successful type-8 branch sets velocity for later ticks.

Types 30/35 use the object's origin/scale and `Animation(..., 0, 1)`, then TransformPosition with a zero local
point at bone 1/2. The pulse is `(sin(time * rate) + 1) * 0.2 + 0.6`, rate 0.002/0.039, RGB factors 0.7/0.5/0.2,
range 3/1. The native deferred command resolves after the preceding tick, reposes this object and refuses
missing bones or failed poses. It never substitutes the object origin or a prior object's shared matrices.

Market visual requires world 79. Types 30/35 emit `0x7f78` sprites at bones 1..3/2, scale `1.5*object.scale`,
with separate 0.5/0.7 light factors. Type 54 requests particle `0x801e/0`, zero light and fixed scale 1.
Types 55/56 request `0x801c/8` and probabilistic `0x801b/4`. Type 57 emits an orange flare and one of three
fire particles. Type 58 emits a scale-20 flare with its own sine pulse. The native host poses hidden lamp
objects even though their geometry returns skipped. Missing models are silent; bone emitters also require
a valid current pose and sufficient bones, with refusals counted.

Uruk's predicate accepts 100 and 101; factory registration selects this class only at 100. Native dispatch
therefore changes 100 only. Create clears OBJECT +0x64 for every type, applies range -400 to its eleven
listed types, hides fifteen emitter types and returns true. Move scrolls the V coordinate for types
16/44/72/73/84/85/86 and emits a random warm range-3 light for type 27. It returns true for default types too.

Uruk visual handles fire/sound, waterfall/mist/smoke/cloud emissions, a signed-X sine-window burst, rotated
random offsets, a type-106 OBJECT light write, and weather-gated emissions on types 108/109. Type 92 uses
width 10 at start 90, otherwise 40, with inclusive endpoints. Type 108 consumes all angle draws in order;
its keyed effect uses `trunc32(cos(float(rand)) + 0.5)` narrowed to a word. The instruction comparison rejected
the initial square-root reading of `0x009fa223`. It also rejected the initial U-coordinate scroll reading.

## Comparison and native evidence

All six production-C families pass 1,000 cases each: **6,000 equal, zero mismatches or stopped cases**.
They compare AL, all 984 OBJECT bytes, ordered expanded output calls, bone-query order and final MSVC RNG.
World predicates, vector accessors, alpha stepping, sine/cosine, AngleMatrix and VectorRotate execute as
original instructions. Model lookup, animation, bone-position transformation and emission services are
recording boundaries. The market move service asserts origin/scale writes, all eight Animation arguments,
zero local bone input and light position before normalizing to one deferred host command. Synthetic bone
positions are supplied; this family does not re-prove the bone engine. Native libm and existing record-math
are compared over these samples, not asserted for every float.

**33/33 separately compiled planted mistakes are detected**, with zero mutant stops. They cover world/model
and alpha gates, defaults, boxes/flags, bone selection, lights, hidden types, sprite scales, particle kinds,
RNG gates, burst width/count, light mutation, weather, angle draws and keyed/colored request arguments.
The samples include signed type extremes, sibling worlds, absent models, ordinary signed coordinates/scales,
finite clocks within +/-1,000,000 and all primary emitter types. Nonfinite/extreme clocks and exact captured
random/animation phase remain unverified.

Portable checks exercise public create/move dispatch, the second alpha step, exactly one generic tick,
zero/one/full-capacity output logs and state/RNG independence from log capacity. The production native host
uses a small authored four-bone/two-key model. It checks 21 emitter types for 200 preparations each,
4,200 preparations, plus missing/unloaded-model silence and RNG stability. It also executes actual sector
movement, tick-before-lamp posing, light/sprite position agreement, a changed object origin and missing-bone
refusal. These checks prove callback plumbing and current poses, not complete nested particle rendering.

## Downstream limits

Weather `0x01cf15ec` is an explicit `mu_objects_runtime.uruk_weather` input, inactive by default. Its authoritative
feed and capture remain open. Two requests retain arguments the existing native callback ABI cannot represent:
type 108's keyed `0x806e/12` effect and type 109's colored `0x7f7d/13` joint. Their complete relevant values are
compared and kept in distinct commands, and the host increments `draw_unsupported` rather than dropping the
key/color into an approximate emission. No pixels are claimed for those requests.

Static consumer audit against `mu_pt_kind_supported` and `mu_pt_world_flame_kind`: these requested nested
particle families remain unsupported and counted by the existing particle host.

| Source | Missing particle family |
|---|---|
| Market 54/55/56 | `0x801e/0`, `0x801c/8`, `0x801b/4` |
| Uruk 89/93 | `0x7f5a/69` |
| Uruk 90/91 | `0x7f89/25` |
| Uruk 92 | `0x801b/7` |
| Uruk 105/106 | `0x7fdd/3`, `0x8184/2` |
| Uruk 108 | `0x7f5a/22`, `0x7fd5/0` |

The common fire lifecycles, `0x801a/2`, `0x801c/14`, `0x801b/2` and `0x7f5a/21` are reused from existing
consumers. This is a static availability audit, not a new proof of their nested rendering. Market type 68's
after-character flag does not establish its missing class after-render method. No custom-render,
after-render or invisible-sector method is promoted to verified by this change.

## Saved-capture regression and continuation

The two builds use the same saved October 22 object/light/global snapshots, installed assets, camera,
25-step endpoint and sparse first/final render cadence. The installed executable matches the target pin.
The fourteen views are unaffected worlds; their regression result and locked Mac gate counts are recorded
in [the handoff](../handoffs/RENDER-WORLDS-I.md). There is no new-world image-error score or visit-frequency claim.

DATA-ACQ-002 needs **world 79** complete raw OBJECT records, especially types 8/30/35/50..59/67/68, operable
registrations, loaded model/action/bone inventory, camera/PNG, primary/frame light, WorldTime, RNG state and
simultaneous particle/sprite pools. Capture lamp frames/prior frames/actions and all relevant posed bones.
For **world 100**, acquire complete records including 16/20/27/44/72/73/84..94/105/106/108/109, weather
`0x01cf15ec`, models, camera/PNG, terrain light, clock/RNG and simultaneous particle/effect/joint/sprite pools.
Sample type 92 across its window edges, type 106 before/after its light write and weather 0/1 transitions.
Market type 67 logs its original operable-registration request; the shared operable registry is an engine boundary,
not implemented by this class port. World 101 needs its separate registered class state; the Uruk predicate alone does not authorize dispatch there.
No capture was taken in this task. The other 113 primary methods and separately inventoried slots remain open.

```sh
MU_RECOVERY_INTEGRATION=1 tools/python/bin/python scripts/run_validators.py --private \
  --only validate_worlds_i,validate_worlds_h,validate_worlds_g --report "$I_SCRATCH/registered"
tools/python/bin/python scripts/world_handler_coverage.py
tools/python/bin/python -m unittest discover -s reconstructed/objects -p test_worlds_i.py -v
tools/python/bin/python -m unittest discover -s native/tests -p test_native_worlds_i.py -v
bash scripts/local-macos-ci.sh
```

During execution, `I_SCRATCH=~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-i`; renders use the sibling
`renders/render-worlds-i`. Both task folders, builds and the worktree are removed after merge. No new local
input needs retention. Only authored source, synthetic fixtures, provenance and reviewed summaries are committed.
