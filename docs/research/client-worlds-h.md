# Duel Arena and world-82 primary handlers

RENDER-WORLDS-H, 2026-10-28, issue #203. Six primary methods are implemented in
`reconstructed/objects/duel_arena.c` and `world82.c`, with shared dispatch only in the existing object host.
The [inventory](world-handler-coverage.md) now has **25/144 verified primary families across 9/48 classes**,
zero static-only entries and 119 missing primary methods. All 48 classes, 57 registrations and 288 method
addresses still agree with the pinned factory/vtables. Custom, after-render and invisible methods remain separate.

## Selection and provenance

The retained October 22 tour contains no missing concrete class outside the task's A-G exclusions.
Duel Arena and the world-82 class provide another complete primary group using existing particle/sprite/effect
hosts. Neither has captured live objects. This priority is an implementation judgment, not measured visit-frequency
or a claim of a captured visual defect. Built-in Lorencia/Dungeon/Lost Tower/Atlans hooks are outside the 48-class
count; their remaining visuals and excluded classes' remaining methods stay open.

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Text capture09 at `0x00401000`, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
Run10 data at `0x01a7c000`, SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
`scripts/pins.py` checks both complete captures. The validator records each half-open method range and digest.
These are restored Linux/Wine x86 instructions, not native Windows or new live observations.

| Family | Original method range | Cases |
|---|---|---:|
| Duel create | `0x00dc6643..0x00dc6685` | 1,000 |
| Duel move | `0x00dc6685..0x00dc6790` | 1,000 |
| Duel visual | `0x00dc6790..0x00dc6a2e` | 1,000 |
| World-82 create | `0x00e2bf57..0x00e2bf8d` | 1,000 |
| World-82 move | `0x00e2bf8d..0x00e2c002` | 1,000 |
| World-82 visual | `0x00e2c002..0x00e2caaf` | 1,000 |

## Verified behavior

Duel create gives types 0/1/32 range -300. Move checks world 64, hides 34/35/36 and gives 34 a random
range-3 terrain light. Move returns false even after writing fields or logging light. Visual has only a model
gate, no world predicate. Type 35 probabilistically emits smoke subtype 22 with its object owner; 36 emits an
orange flare and one of three fire particles. Visual also always returns false.

World-82 create gives types 0..6 range -300. Move/visual use predicate `0x00e3068f`, accepting worlds 82..90,
although factory `0x00ea488e` registers this class only at 82. Public native dispatch therefore selects 82 only.
Move hides 0..6/47/48; visual requires a model and hides 0..6. Its cases include the signed-X sine-window burst,
smoke/cloud RNG gates, red cloud strength, timed 4..7 effect bursts, object-light writes, orange flare/fire,
blue particle pairs and scale-dependent XY scatter. The burst window is width 10 for start 90, otherwise 40.
The initial opposite reading was rejected by the comparison. Type 48 consumes X then Y random draws.

All **6,000 production-C versus Unicorn comparisons pass, zero mismatches and zero stopped cases**.
They compare AL, all 984 OBJECT bytes, ordered expanded engine arguments and final MSVC RNG state.
Vector accessors, world predicates and sine run as original instructions. AddTerrainLight, CreateParticle,
CreateSprite and CreateEffect are recording service boundaries. Fixed sprite descriptors and effect tail words
are asserted by the stubs; variable effect scale is retained in its expanded event and forwarded through the
existing `effect_scaled` native callback. No new shared callback ABI is introduced.

**19/19 separately compiled C planted mistakes are detected**, with zero mutant execution stops. They cover
create bounds, world/model gates, hidden types, light strength, sprite scale, RNG divisor, burst width/count,
timer boundary, effect subtype, object light, blue particle kind and scatter scale/axis. Successful-domain
samples include signed type extremes, off-world/model-null gates, signed and invalid float-to-int coordinates,
negative scales, finite clocks within +/-1,000,000 and timer boundaries. Nonfinite/extreme clock equivalence
and captured RNG phase are not established.

Type 48's original divides by `trunc32(scale * 60)`. A zero divisor traps in x86; native C explicitly suppresses
that emission after the gate draw. This is a deliberate host guard outside successful instruction equivalence,
with a portable zero-scale regression. A directed original-instruction probe confirms UC_ERR_EXCEPTION.
This expected trap is not counted among the 6,000 passing original-method cases.

## Native and regression evidence

The production preparation host runs 200 draws for each of eleven emitter types, 2,200 draws total, with
synthetic loaded model metadata and hidden geometry. Particle/sprite/effect callbacks check positions, kinds,
subtypes, owners and scale. Each type also checks missing and unloaded models for silence and unchanged RNG.
The sibling world calls the generic host. G's sibling-silence fixture now uses world 65, since 64 is implemented.
Public create/move tests exercise both worlds; bounded zero/one/full-capacity logs preserve OBJECT and RNG state.
Three separately linked native controls also fail the host assertions when either class dispatch is removed
or the effect scale is forced to zero. G/H registered validators pass together: **12,000 comparisons, zero mismatches/stops, 32/32 compiled mutants**.

Fourteen existing snapshot views retain **28/28 first/final PNG hashes, 14/14 object dumps and 14/14 light dumps**
against the owned-worktree baseline. Both builds use the same saved captures and installed assets, whose
executable matches the target pin. These are unaffected-world regressions. No world-64/world-82 image score
or full nested particle/effect-rendering equivalence is claimed. Existing downstream unsupported-kind counters
remain in use. Full Mac gate results are in [the handoff](../handoffs/RENDER-WORLDS-H.md).

### Downstream limits

Static consumer audit: existing A flame lifecycles support the three fire requests from Duel type 36 and
world-82 type 6; the sprite host consumes their flare. Existing smoke subtype 21 supports world-82 type 5.
The primary-method proof does not add the following nested lifecycles, which existing hosts reject/count:

| Emitter | Requested family still missing downstream |
|---|---|
| Duel type 35 | particle `0x7f5a/22` |
| World-82 type 0 | particle `0x801b/7` |
| World-82 type 1 | particle `0x7f5a/69` |
| World-82 types 2/3 | particles `0x7f89/16` and `/11` |
| World-82 type 4 | effect `0x7f42/7` |
| World-82 type 47 | particles `0x8086/2`, `0x8087/6`, `0x8089/2` |
| World-82 type 48 | particle `0x7ef7/15` |

This list is separate from the 119 missing class methods. The native callback regressions establish argument
plumbing; they do not establish that these rejected nested requests produce pixels.

## DATA-ACQ-002 and remaining work

For **world 64**, acquire complete raw OBJECT records including types 34/35/36, loaded model inventory,
terrain primary/frame light, camera/PNG, WorldTime `0x06fce370`, RNG phase and simultaneous particle/sprite pools.
For **world 82**, acquire all 0..6/47/48 emitter records with scale/position, loaded models, terrain light,
clock/RNG, particle/sprite/effect pools and camera/PNG. Sample type 0 across its window transition, type 4 across
clock remainder 5/6 and type 48 with its actual scale. No capture was taken in this task.
The two classes' custom/after/invisible slots, the other 119 primary entries, built-in visual hooks,
uncaptured population and synchronized nested-pool image replay remain open.

```sh
MU_RECOVERY_INTEGRATION=1 tools/python/bin/python scripts/run_validators.py --private \
  --only validate_worlds_h,validate_worlds_g --report "$H_SCRATCH/registered"
tools/python/bin/python scripts/world_handler_coverage.py
tools/python/bin/python -m unittest discover -s reconstructed/objects -p test_worlds_h.py -v
tools/python/bin/python -m unittest discover -s native/tests -p test_native_worlds_h.py -v
bash scripts/local-macos-ci.sh
```

`H_SCRATCH=~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-h` during execution. Reports, tour manifests,
renders and build outputs are deleted after merge under the owner's disk-space rule. Committed summaries and
PR retain counts and limits. No private bytes, snapshots, decoded assets, input symlinks or PNGs are committed.
