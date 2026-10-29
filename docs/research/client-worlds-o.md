# Abyss of Atlans 1-3: primary handlers and the shared tile folder

RENDER-WORLDS-O, 2026-10-28. Worlds 128, 129 and 130 (three factory classes). The lane adds their primary
create/move/visual methods, and the terrain-texture folder rule that left Abyss of Atlans 2 and 3 without
terrain in the native world. Coverage goes from **33/144 to 42/144 primary methods** and from **11/48 to
14/48 classes** (counted on main `38d08a9`; lanes merged later add their own). Labels: **verified** =
compared with the original instructions under Unicorn; **static** = read from disassembly or files;
**inference** = not checked by a read or by execution.

## Provenance

Target `main.exe` SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Capture09 text
at `0x00401000` (SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`) and run10 data at
`0x01a7c000` (SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`) are pin-checked by both
validators. Their reports also hash each body. No original client or launcher was used. The live inputs
are DATA-ACQ-002's arrival captures `128-abyss-atlans-1`, `129-abyss-atlans-2` and `130-abyss-atlans-3`
([captures 2](client-world-captures-2.md)).

## Shared shape

All three classes have the same create, move and visual bodies. The only difference is the compared world
constant (`0x80`/`0x81`/`0x82` against the world global `0x01cf15fc`). Their custom-render slots
(`0x00d5d2f6`, `0x00d5ef96`, `0x00d606da`) differ slightly: class 129's has no world test, and its type-7 gate
orders its RNG and frame tests differently, with thresholds 19.97/`%10 ≥ 7` instead of 19/`%10 ≥ 8`. Those
slots are not primary methods and are not implemented here. Native code is one file,
`reconstructed/objects/abyss_atlans.c`, with the class world as an explicit argument, so each class rejects the
other two worlds exactly as the original does.

| Family | Original half-open range | Cases |
|---|---|---:|
| Abyss 1 create / move / visual | `0x00d5cf32..0x00d5d014` / `0x00d5d04a..0x00d5d2f6` / `0x00d5d564..0x00d5d5ad` | 3 × 1,000 |
| Abyss 2 create / move / visual | `0x00d5ebd2..0x00d5ecb4` / `0x00d5ecea..0x00d5ef96` / `0x00d5f1f1..0x00d5f23a` | 3 × 1,000 |
| Abyss 3 create / move / visual | `0x00d60316..0x00d603f8` / `0x00d6042e..0x00d606da` / `0x00d60948..0x00d60991` | 3 × 1,000 |

Each create body ends with a 13-entry jump table (`0x00d5d016`, `0x00d5ecb6`, `0x00d603fa`), which is hashed as data.

## Verified methods

- **Create** (`ret 4`): returns false if the world differs or the object is null. Otherwise it returns true. Types
  23/38/40/41/44/50 set the after-character flag `+0x0a = 1`. Types 161..180, except 173 and 174 (default
  entries of the jump table), set hidden mesh `-2`.
- **Move** (`ret 4`): same gates, always true otherwise. Type 22: hidden `-2`; timer `+0xb4 += 0.1`,
  reset to 0 above 10; while it is above 5, `CreateParticle(0x7fcd, position, angle, light +0xec, 0, 1.0, no
  owner, 0)`. That is the Atlans `drop01` sheet, an existing native consumer. Type 23: blend mesh 0,
  blend light `sin(T·0.002)·0.3+0.5`. Types 32/34/66..70: blend mesh 1, `sin(T·0.004)·0.5+0.5`. Type 38:
  blend mesh 0. Type 40: blend mesh 0, `sin(T·0.004)·0.3+0.5`, velocity 0.05. T is WorldTime `0x06fce370`. The
  sine goes through `0x009681bd` (float → double CRT sine → float), followed by float multiply/add, as in the C.
- **Visual** (`ret 8`, object and model): false for another world, a null object or a null model. Otherwise it
  is true, and type 39 sets hidden `-2`. It makes no request.

The validator `scripts/validate_worlds_o.py` compares AL, all 0x3d8 OBJECT bytes, ordered CreateParticle
arguments and final MSVC RNG. These bodies make no RNG call; the comparison confirms that. The sine helper and
CRT sine run as original instructions. Cases sample 50 directed types plus random ones, the class world and
worlds 0/127..131, null objects (27 per family) and absent models (143 per visual family). Move cases add
directed timers around 0, 5 and 10 (also NaN/±inf/−0), with a third of them on type 22. Times include
±0, ±1000, π/8-phase and random values within ±1,000,000.

**9 families, 9,000 cases: 9,000 equal, zero mismatches or stops. 24/24 separately compiled mutants caught**
(world gates, type lists, the 173/174 holes, timer step/reset/threshold, particle kind/light/scale, pulse
rate/offset/amplitude/order, velocity, blend mesh, hiding and the model gate). Original instructions are never
mutated. Particle requests in the move families: 68/61/60.

## The Abyss 2/3 terrain folder (verified)

OpenWorld `0x0182876e` computes the map folder `[ebp-0x10] = 0x018308d6(world)` (folder = world+1 for 128..130,
static). At `0x01828f4f` it calls the tile-bitmap loader **`0x01829457(folder)`**, unless `0x00deea76(world)`
holds. The loader's first branch, **`0x0182945d..0x0182946f`**, decides the folder. It calls
`0x016a8325(folder - 1)`, the predicate `128 ≤ x ≤ 130`, and when that is true it overwrites the folder with
**`0x81`** before `sprintf("World%d")` (`0x01aec5c4`). Every tile bitmap the loader opens uses that directory:
`0x7630..0x763e` (TileGrass/Ground/Water/Wood/Rock and the alpha tiles), the ExtTile `.jpg`/`.tga` loops and
`0x7694..0x76a1` (grass `.tga`). The one exception is the literal `Object64\song_lava1.jpg`.
So **Abyss of Atlans 2 and 3 draw Abyss 1's `Data\World129` tiles**.

The neighbouring loader `0x01829e21` (`leaf01.tga` etc.) formats `World%d` from the unmodified folder. Map,
attribute, height, light and object files also come from each world's own folder; the installed `World130`/`World131`
hold those files, and primary light already matched the live grid exactly. Other per-world paths that are already
shared stay as they were: object models of 128..130 come from `Object131` (`0x016a8325` in the model pass), Abyss 1
types 66..70 from `Object129`, and water frames `wt%02d` from `Object131`. The other callers of `0x016a8325`
(`0x016c98cc` RGB height, `0x016d6ad5`, `0x01856c8e`, `0x01538297`, `0x017fe62a`, `0x00c9f189`, `0x00ca08a3`,
`0x00ca1a51`) are world-group predicates for heights, rendering passes or attributes, not asset paths (static).

Native: `mu_terrain_tile_folder(folder)` in `reconstructed/terrain/terrain.c` mirrors the branch.
`load_bitmaps` (`native/core/mu_terrain.c`) builds its directory from it. The report and `mu-terrain info` show
`tile_folder`.

`scripts/validate_world_tile_folder.py` executes `0x01829457` and the predicate as original instructions for 19
world globals (those that select alternative names in the loader, plus 127..131) × folders 0..299.
**5,700 cases, all equal, zero stops, 1,077,300 recorded bitmap loads.** Every recorded path lies in
`World<mu_terrain_tile_folder(folder)>`; the only remapped folders are 130 → 129 and 131 → 129. Under the
previous native rule (own folder), 38 cases fail, all on folders 130/131. Boundaries: the bitmap loader
`0x0185baac` records; C-library `sprintf` `0x009619dd` is a Python stub over the client's format strings; the
singleton flag `0x00db747f`/`0x0095fba9` (AlphaTileGround03 vs TileGround03) is stubbed with both answers.
`0x018308d6` depends on runtime singletons and is not executed. Native `mu_world_folder` is unchanged.

## Native consumption

`mu_obj_create`/`mu_obj_move` dispatch worlds 128..130 to the shared functions after the generic part (one
generic tick, unchanged). The production object host treats them as primary-visual worlds and calls the
visual after RenderObject, with `m && m->loaded` as the model argument. The particle module's generic visual
hook had no case for these worlds; it falls back to the world-0 scroll part, which does nothing here. Type-22
`0x7fcd/0` move requests use the existing move-log particle path.

Not consumed natively (record only, as in the original slot table): the after-character flag has no deferred
second pass in these worlds natively (`mu_world_defer` has no 128..130 branch), so those objects still draw
in the first pass. The custom-render and after-render slots remain missing.

## Fidelity at the captured arrival tiles

Method and readers of [captures 2](client-world-captures-2.md): `scripts/fidelity_tour.py` with the DATA-ACQ-002
manifest, installed data, 25 steps, 1722 × 1048, base `38d08a9` against this branch, both built in this worktree.

| Capture | Image mean \|Δ\| / share > 24 | Field differences, map (near hero) | Objects matched |
|---|---|---|---|
| Abyss 1, 128 at 130,127 | 7.946 / 0.0482 → **7.922 / 0.0476** | 276 (124) → 79 (64) | 3,908 / 0 / 0 |
| Abyss 2, 129 at 128,124 | 82.170 / 0.9278 → **4.412 / 0.0130** | 512 (125) → 134 (70) | 5,899 / 0 / 0 |
| Abyss 3, 130 at 128,124 | 47.984 / 0.8807 → **2.230 / 0.0019** | 455 (153) → 101 (90) | 5,238 / 0 / 0 |

- After-character differences go 160/393/329 → **0**. Near-hero velocity goes 2/2/1 → 0, near blend mesh
  56/53/63 → 4/12/18, and primary light stays exactly equal.
- What remains is blend light, which is time-dependent (the two WorldTimes differ, so it is not a fidelity
  measure). The rest are objects whose live blend mesh is still −1 or velocity 0.16, the creation defaults,
  where native has applied move. Inference: the live arrival frame had not yet moved them. The 14 map-wide
  type-40 velocity differences in Abyss 2 are of this kind (6 → 14).
- The native object image near the Abyss 2 hero equals the live one field for field, including type 66's blend
  mesh 1.
- 29 other DATA-ACQ-002 views (all except 128..130): **58/58 PNG, 29/29 OBJECT and 29/29 light hashes
  identical**. The three Abyss light dumps are also unchanged. The October 22 fourteen-view live snapshots are
  no longer at their manifest paths, so that tour could not be rerun. Those worlds (0..80) use neither these
  classes nor folders 130/131.
- Visual inspection: the Abyss 2/3 sea floor now matches the live shot. Pre-existing defects, now visible:
  in Abyss 2, near-hero objects of types 3/4/6/24 draw as opaque dark meshes where the live frame shows only
  sea floor (object fields equal live). Abyss 1's type-66 pillar draws bright cyan (also in the base).

## Limits and follow-ups

- Custom render (`0x00d5d2f6`/`0x00d5ef96`/`0x00d606da`: type-7 animated action and blend body, type-52 blend
  meshes, hidden draw for 23/38/40/44/50) and after render (`0x00d5d5ad`/`0x00d5f23a`/`0x00d60991`) remain missing.
  So do the after-character second pass for 128..130 and the invisible-sector move `0x00d5cbbc`.
- Abyss 2 dark meshes (types 3/4/6/24) and the Abyss 1 cyan pillar: model/texture path to investigate.
- The `0x7fcd/0` drop particle is an existing consumer; its nested lifecycle was not re-verified here.
- Arrival captures have no pool, RNG phase or time synchronisation, so pulses and particles are not compared live.

```sh
tools/python/bin/python scripts/validate_worlds_o.py --cases 1000 --mutations --output <json>
tools/python/bin/python scripts/validate_world_tile_folder.py --output <json>
MU_RECOVERY_INTEGRATION=1 tools/python/bin/python scripts/run_validators.py --private --only validate_worlds_o,validate_world_tile_folder
tools/python/bin/python -m unittest reconstructed/objects/test_worlds_o.py native/tests/test_native_worlds_o.py
```

[Handoff, gate and cleanup](../handoffs/RENDER-WORLDS-O.md).
