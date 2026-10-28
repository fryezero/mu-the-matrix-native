# Santa Village and Vulcanus primary handlers

RENDER-WORLDS-G, 2026-10-28. The [coverage inventory](world-handler-coverage.md) accounts for 48 concrete
factory classes, 57 registered worlds and 288 method-slot addresses. The three primary slots have
19 verified families and 125 missing methods across 144 entries; seven classes have at least one verified
primary method. The inherited BaseMap registration for world 146 is outside these counts.

## Provenance and boundaries

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Instructions use capture09 text at `0x00401000`, SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`.
Constants and vtables use run10 data at `0x01a7c000`, SHA-256
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
Both whole-file pins are checked before comparisons; reports also identify each method range and digest.
This is captured x86 Linux/Wine evidence, not native Windows observation. No live client was used.

| Class / world | CreateObject +2c | MoveObject +30 | RenderObjectVisual +34 |
|---|---|---|---|
| Santa Village / 62 | `0x00e4231c..0x00e4236e` | `0x00e42370..0x00e423d6` | `0x00e423d8..0x00e426cf` |
| Vulcanus / 63 | `0x00e8ec09..0x00e8ec80` | `0x00e8ec80..0x00e8ece1` | `0x00e8ece1..0x00e8f515` |

Each half-open range contains the complete method entry and return. The original world predicates
`0x00e42f6d` / `0x00e94004`, vector accessors and sine execute under Unicorn. Allocation/render services
CreateSprite, CreateParticle and CreateJoint are recording stubs. The comparison checks AL, all 984 OBJECT
bytes, ordered expanded call arguments, fixed tail arguments and final MSVC rand state. Only initialized
memory is readable; unhandled access, stack or execution failures are reported as stops.

## Verified behavior

- Santa create sets range -300 for types 12, 13, 18, 19, 21 and 25. This method has no world predicate.
  Move checks world 62, sets type 16's animation velocity to 0.06 and hides types 26, 27 and 28.
  Visual checks the model pointer, with no world predicate. Types 26/27/28 emit a sprite at the object position,
  scale `8 * object.scale`, with three colored variants of the clock pulse
  `(sin(time * 0.005) + 1) * 0.1 + 0.9`.
- Vulcanus create checks world 63. Types 0..6 get range -300; type 70 gets the after-character byte; type 74
  gets hidden mesh -2. Move hides types 0..6. Visual requires world 63 and a model, then hides types 0..6.
  Type 0 emits 20 particles during its signed-X-dependent sine window. Types 1/2/3 choose smoke/colored
  particles through rand gates. Type 4 consumes the X and Z angle draws in order, creates a joint followed
  by a particle. Type 5 writes object light 0.3 before its particle. Type 6 emits an orange sprite and
  one of three randomly selected particles.
- The type-0 window is `[start, start + width]`, with `start = (trunc32(x) % 3 + 1) * 30` and
  width **10 when start is 90, otherwise 40**. The original `lahf/test/jnp` sequence reverses a tempting
  reading of the equality branch. An early comparison rejected that reversed interpretation.
- The native host calls these visuals after RenderObject even when geometry is hidden. The model-presence
  gate is independent of pose success because these methods do not read bones. Existing sprite/particle/joint
  hooks consume the expanded records; generic particle-world dispatch is bypassed for these two classes.

All six families pass **1,000 cases each, 6,000 total, zero mismatches and zero stops**. Tests include handled
and default types, signed type extremes, sibling worlds, null model gates, signed coordinates, invalid
float-to-int range values, zero/negative clocks and sampled finite clocks within +/-1,000,000. Native libm sine
matches the original binary32 outputs on these samples; extreme or nonfinite clocks are not established.
**13/13 separately compiled planted mistakes are caught**, covering create/move type bounds, range-case
selection, after-character flag, world/model gates, sprite scale, burst size, RNG gate, joint subtype,
object light and particle bitmap. Mutations leave the original instructions untouched.

## Runtime and regression checks

Synthetic public create/move dispatch tests pass. A production `mu_objects_prepare_index` host runs all seven
Vulcanus emitter types and all three Santa glow types with loaded synthetic model metadata and hidden geometry.
It checks particle/sprite/joint callbacks, ownership, subtype and scale, missing-model silence/RNG stability,
and sibling-world dispatch. It needs no game assets and would fail if either new visual dispatch were removed.
The private validator is registered in `scripts/validators.toml` and has an opt-in unittest.

Fourteen saved-snapshot tour renders at the existing 25-frame endpoint retain **28/28 first/final PNG hashes,
14/14 object dumps and 14/14 light dumps**. None is world 62/63, so these are unaffected-world regressions,
not Santa/Vulcanus image-fidelity evidence. The full local Mac gate passes with 1,466 tests, 179 explicit skips and seven fixture scenarios.
The reviewed publication audit rejects zero of 1,367 files. Details are recorded in
[the handoff](../handoffs/RENDER-WORLDS-G.md).

## Remaining work and DATA-ACQ-002

The other 125 primary methods and the inventory's separately marked custom/after/invisible slots remain open.
The integrated A lane adds bounded Karutan visual coverage and Raklion/Karutan custom/after slot annotations;
the seven-class count is unchanged. E's inherited event helpers are outside the three primary slots.
Santa/Vulcanus custom-render and after-render slots are missing; setting Vulcanus type 70's byte does not
claim its second-pass drawing is implemented. This lane does not change the excluded A/E handlers or prior
Icarus/Devias/Tarkan/Raklion work. The interrupted checkpoint's nonexistent Duel Arena references were removed;
Duel Arena remains missing in the inventory.

DATA-ACQ-002 needs world 62 and 63 object lists with complete raw OBJECT fields, loaded model/type inventory,
terrain light, simultaneous world clock `0x06fce370`, world `0x01cf15fc`, sprite/particle/joint pools and a PNG
at a known camera. For type-0 Vulcanus, capture both sides of an emission-window transition; for Santa, capture
all three glow types at the same clock. No such capture exists in the fourteen-view tour. New live reads are
outside this run. Until separately authorized acquisition provides them, real object population, world images,
captured RNG phase and exact nested-pool rendering remain unverified. Call selection does not prove every
nested particle/joint subtype or texture in the native renderer.

## Reproduce

```sh
tools/python/bin/python scripts/world_handler_coverage.py
MU_RECOVERY_INTEGRATION=1 tools/python/bin/python scripts/run_validators.py --private \
  --only validate_worlds_g --report "$G_SCRATCH/registered"
tools/python/bin/python -m unittest discover -s reconstructed/objects -p test_worlds_g.py -v
tools/python/bin/python -m unittest discover -s native/tests -p test_native_worlds_g.py -v
bash scripts/local-macos-ci.sh
```

`G_SCRATCH=~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-g`; reports and manifests stay there.
Renders stay under `~/Documents/MTM/mu-mac-tools/native/renders/render-worlds-g/{before,after}`.
No client bytes, decoded assets, object snapshots or PNGs are committed.
