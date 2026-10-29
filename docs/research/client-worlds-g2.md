# World object textures, brazier fires and the Vulcanus far plane (RENDER-WORLDS-G2)

RENDER-WORLDS-G2, 2026-10-28. Follows the DATA-ACQ-002 comparison ([captures 2](client-world-captures-2.md)), which
showed untextured white bone piles and no brazier fires in Vulcanus (63), untextured (later orange-lit) blocks and no
fires in Deep Dungeon 1–5 (116–120), and a Vulcanus far plane of 3257.8 against the live 3700. Labels as in the other
notes: **verified** = compared with the original instructions under Unicorn or with a live capture; **static** = read
from decoded instructions or files; **inference** = not checked by either. Target `main.exe` and pinned captures as in
[world fidelity](client-world-fidelity.md); text `3cf91f3c…` capture09, data run10, section 3 x86-linux-capture-04.

## 1. Root causes

**Object textures (verified).** The untextured meshes name files that are not in the model's folder:
Vulcanus `Object64/Object09.bmd`, `Object10.bmd` → `bons.jpg`; Deep Dungeon `Object117..121` → `bons.jpg` (9 meshes) and
`deep_wall01.jpg` (12 meshes). The installed copies are `Data/Skill/bons.OZJ` (byte-identical to the copies in Object2,
Object5, Object8 and Monster) and `Data/Object2/deep_wall01.OZJ` (static: folder listings and SHA-1). The native loader
only looked in the model's folder. The original OpenTexture does more:

- **OpenTexture `0x0181fbe9`** builds `"Data\" + subfolder + name` and calls the resolver `0x0181fead`. On the
  default answer `0x7530` it asks the bitmap-name map (`0x00c97e0c` on `0x0bdc5f00`, map at `+0x34`, key = the
  lowercased file name through `0x0120b45f`) and reuses that bitmap through `0x00c97730(index, path, GL_NEAREST,
  GL_CLAMP)`, which only counts a reference when that index is loaded under that path (`0x00c977a1..0x00c977e4`).
  Otherwise it retries `"Data\Item\" + name`, then `"Data\Item\Texture\" + name`, and finally shows text `0xeaa`.
- **Resolver `0x0181fead`**: `ski…` and `level_` (strncmp) → `0x7725`; `hid…` → `0x791a`; `hair` → `0x7776`;
  `face_` → `0x791c`; `_strnicmp` `HQskin3` → `0x7869`, `HQskin2` → `0x7818`, `HQskin`/`HQlevel_` → `0x77c7`,
  `HQhair_` → `0x78ba`; otherwise the letter after the extension's dot (`_splitpath`, tolower): `t` → LoadImage
  with GL_NEAREST, `j` → LoadImage with OpenTexture's filter; anything else → `0x7530`.
- **The name map** is filled by the loaders: the JPEG loader stores the lowercased `fname+ext` of the loaded path at
  bitmap `+0x104` (`0x00c98541..0x00c98562`) and inserts it with `std::map::insert` (`0x00c9a55f` at `0x00c98790`),
  so the first bitmap loaded under a name keeps it (static; the insert-not-assign reading is inference from the
  MSVC helper shape). A second map at `+0x14` is keyed by the full lowercased path (`0x00c97d69`).
- **What is in the map when a world's objects open (verified, recordings).** The startup opener `0x01832af3`
  (the routine right before the world pass `0x018392db`; no direct caller in the restored text) opens 418 models in
  1,269 OpenTexture calls, among them `Data\Skill\Skeleton01..03` with `"Skill\"` (mesh 0 = `bons.jpg`). The world
  pass opens its own extra models before every object type: 382 entries in 70 worlds, all before the first object
  texture call; worlds 116–120 open `Data\Object2\DungeonStone01` (mesh 0 = `deep_wall01.jpg`), Bat01, Rat01 and
  `Data\Monster\DarkSkeletonWarrior` first. The live model container (`lightread` MODL) of the Vulcanus and Deep
  Dungeon 1 captures holds keys `0x422..0x424` (Skeleton01..03) and `0x43a` (DungeonStone01) (**live**).
- **Texture folder of object types (verified).** All 60,000 OpenTexture calls of the world pass for types 0..299
  (worlds 0..199) use `"Object<mu_objects_folder(world)>\"`. Abyss of Atlans 1 (world 0x80) opens types 0x42..0x46
  from `Object129` but their textures from `Object131`; the native loader took them from Object129, where they are
  missing (the bright cyan pillar at the Abyss 1 arrival tile).

Chain result over the installed data at the 19 affected captures: every missing object mesh is found, by the name
map (`bons.jpg` → Skill, `deep_wall01.jpg` → Object2, `pannilleff02_R.jpg` → Effect, `skR.jpg` → Monster), by
`Data\Item\` (weapons, shields, medicine, books in 79, 91, 142, Elbeland, Karutan) or by `Data\Item\Texture\`.
`skin_special_01.jpg` (Arena, Object7) is the resolver's skin bitmap, not a file.

**Vulcanus far plane (verified).** MoveMainCamera's far plane is 3700 when `event_world` holds; the camera port
already models that branch, but no native host set the input. `event_world` = `0x00e94004()` (`world == 0x3f`) ||
`0x00e3068f()` (`0x52 <= world <= 0x5a`).

**Brazier fires.** Two different producers:

- *Vulcanus*: the braziers are type-24 models with a type-6 marker at the same spot. The type-6 visual (RENDER-WORLDS-G,
  verified there) emits an orange sprite and one of the flame particles `0x8084/0`, `0x806e/4`, `0x8085/0`
  (`reconstructed/particles/world_flames.c`, lifetimes 12–31). The native world creates them, but the headless
  fidelity run draws only the saved first and last of its 25 steps, and RenderObjectVisual's emitters run while
  drawing: 28 particles in 25 steps instead of 350 (**measured**). The interactive world draws every frame.
  `scripts/fidelity_tour.py` gains an opt-in `"draw_all": true` (draws every step through the existing
  `--time-series-every N`); with it the Vulcanus flames appear (25 steps reach about 80% of the 31-step lifetime).
- *Deep Dungeon*: the fires come out of the dragon heads, at type-67 markers (HiddenMesh −2, warm light
  0.8/0.3/0.04 from the N move method). The class's visual `0x00d5cc9b` and its custom/after slots `0x00d5cbbc`,
  `0x00d5cc60`, `0x00d5cc8e` are empty (static). Under Unicorn the RenderObjectVisual tail `0x017fcb5c..0x017fccc1`
  for world 118, types 39/52/67, executes the event hooks `0x009db8b1`, `0x00def747`, `0x00d8e640`, `0x00dfc095`,
  `0x00d622dd`, `0x00dac0a2`, `0x00e75089`, `0x00e7df87` and `0x00e84941` as client code with no request (verified,
  probe), then needs the `0x00d53c8f`/`0x00d5404b` singleton, the `0x00db747f` manager's `+0x34` slot and the
  `0x00e3116a`/`0x00e5f94b` hooks (they read the `0x01ec91b8` singleton), which were not traced. The producer is in
  one of those, or outside RenderObjectVisual (follow-up below). Type 52's keyed CreateEffect `0x43a`
  (DungeonStone01 as an effect model) is a falling-stone candidate, not the dragon fire (inference).

## 2. Native change

- `reconstructed/objects/texture_lookup.{h,c}`: `mu_tl_resolve` (0x0181fead) and `mu_tl_open` (one mesh of
  0x0181fbe9) against a host (LoadImage, name map, reuse, message); the startup and world-pass preload tables
  (`texture_preload.inc`, generated by `scripts/validate_worlds_g2.py --emit-table` from the two recordings).
- `native/core/mu_texture_names.{h,c}`: rebuilds the name map from the installed files, the startup models once per
  process and the world's extras per world (a world change drops the previous extras), and answers OpenTexture's
  later steps with an installed file. `mu_objects_load_models` takes object textures from `Data/Object<folder>`
  and runs the chain for every mesh the folder lacks (`mu_textures_set_file`); the object summary line reports
  `object_textures_retried` / `object_textures_unresolved`.
- `mu_world_camera_event_world` and `mu_walk_init` set `event_world`.
- `scripts/fidelity_tour.py`: `"draw_all"` manifest option.

## 3. Validation

`scripts/validate_worlds_g2.py` (registered `validate_worlds_g2`), default run:

| Family | Cases | Equal | Notes |
|---|---:|---:|---|
| open_texture | 3,000 | 3,000 | 0x0181fbe9 + 0x0181fead as client code on synthetic models (0–6 meshes, negative counts, no model; specials, case variants, odd extensions, folder/Item/Item\Texture files, name-map hits incl. index 0): 6,559 meshes, 999 specials, 129 without a model, 178 negative counts; 7,536 LoadImage, 4,287 name-map, 1,436 reuse and 2,042 message requests |
| startup_table | 448 | 448 | 447 (folder, name, number, subfolder) pairs of 0x01832af3 in OpenTexture order + count |
| world_preloads | 200 | 200 | worlds 0..199, 382 entries in 70 worlds, none after the first object texture |
| event_world | 309 | 309 | worlds −8..300 through 0x00e94004/0x00e3068f; 10 event worlds |
| object_texture_folder | 200 | 200 | 60,000 object OpenTexture calls |

Zero mismatches, zero stops. **17/17 compiled mutants detected** (name-map hit test, Item order, reuse wrap, TGA
filter, case-folded `level_`, missing `HQskin3`, `hair`→`hai`, extra `b` kind, first-dot extension, no message, one
retry, case-folded `ski`, a dropped startup entry, swapped world entries, folder group 128..130 → 129, event world
0x3e, 0x5a excluded). Service boundaries: bitmap services, string ctor/dtor and the 0xeaa text are recording stubs;
CRT `_splitpath` (`0x0198b9e3`) is a stub implementing MSVC's extension rule because its multibyte checks read
heap-held locale state not in the captures; strcpy/strcat/memset/strncmp/_strnicmp/tolower run as client code with
the capture-04 section-3 CRT state. The startup recording maps one zero page for a null-pointer store of a skipped
service's dummy result; 766 of its OpenTexture calls name models opened by other startup routines and are not in
the table.

Portable tests: `reconstructed/objects/test_worlds_g2.py` (lookup order, specials, tables, predicate; private
validator test opt-in) and `native/tests/test_native_worlds_g2.py` with the production host
`native/tests/worlds_g2_host.c` (synthetic game root: folder, name map from a startup and a world preload, Item,
Item\Texture, special, missing, world switch; far plane 3700 for 63/0x52/0x5a and 3257.8 for 62/64/0x5b through
`mu_walk_init`/`mu_walk_begin_render`).

## 4. Fidelity at the DATA-ACQ-002 arrival tiles

Method of [captures 2](client-world-captures-2.md) (1722 × 1048, 25 steps, the same captures and plaintexts).
"Before" is base `3735625` (Abyss rows: base `77c304a`, after RENDER-WORLDS-O); "after" is this lane. Texture
coverage = object mesh textures found by the later OpenTexture steps / left empty (before: every one of them empty).

| Capture | Image mean \|Δ\| / > 24 before → after | Textures retried / unresolved | Far |
|---|---|---|---|
| Vulcanus 63 | 2.665 / 0.0158 → **1.841 / 0.0089** (draw_all 1.828 / 0.0088) | 2 / 0 | 3257.8 → **3700** |
| Deep Dungeon 1 116 | 5.570 / 0.0709 → **2.815 / 0.0069** | 16 / 0 | 3257.8 |
| Deep Dungeon 2 117 | 4.081 / 0.0271 → **2.601 / 0.0051** | 17 / 0 | 3257.8 |
| Deep Dungeon 3 118 | 13.475 / 0.2093 → **3.233 / 0.0127** | 19 / 0 | 3257.8 |
| Deep Dungeon 4 119 | 9.440 / 0.1498 → **2.490 / 0.0090** | 19 / 0 | 3257.8 |
| Deep Dungeon 5 120 | 6.665 / 0.0582 → **2.777 / 0.0069** | 20 / 0 | 3257.8 |
| Abyss of Atlans 1 128 | 7.922 / 0.0476 → **5.386 / 0.0269** | 1 / 0 (10 empty before the folder rule) | 3257.8 |
| Abyss of Atlans 2 129 | 4.412 / 0.0130 → 4.412 / 0.0130 | 1 / 0 | 3257.8 |
| Abyss of Atlans 3 130 | 2.230 / 0.0019 → 2.230 / 0.0019 | 1 / 0 | 3257.8 |
| Scorched Canyon 131 | 7.624 / 0.0280 → **7.121 / 0.0215** | 4 / 0 | 3257.8 |
| Swamp of Calmness 56 | 7.310 / 0.0117 → **7.196 / 0.0096** | 2 / 0 | 3257.8 |
| Acheron 91 | 7.706 / 0.0424 → **6.905 / 0.0360** | 5 / 0 | 3000 |
| Burning Kethotum 136, Swamp of Destruction 144, Loren Market / Event Square 79 | unchanged at three decimals | 1, 3, 2, 2 / 0 | 3257.8 |
| Arena 6, Kanturu Relics 38, Twisted Karutan 142 | unchanged | 0 / 0 | 3257.8 |

Vulcanus' bone piles are now textured; Deep Dungeon's walls, blocks and skull piles are textured and no longer
turn orange under the type-62..67 lights; the Abyss 1 pillar is the dark teal stone of the live shot (visual
inspection). OBJECT fields and primary light are unchanged everywhere. Worlds whose drawn objects need no retried
texture (6, 38, 142, and 136/144/79 at three decimals) are unchanged.

**Existing scenes:** the October 22 fourteen-view tour, base `77c304a` vs lane: **14/14 OBJECT and light dumps
identical; 12/14 PNG pairs identical**. Elbeland (51) and Karutan (80) change as intended: their objects' weapon,
shield, medicine and bottle meshes now take `Data\Item\` textures (7 and 6 retried meshes).

## 5. Follow-ups and limits

| Item | Status |
|---|---|
| Deep Dungeon dragon fire at type-67 markers | Producer not found; untraced: `0x00d5404b` on `0x00d53c8f`, the `0x00db747f` manager's `+0x34`, `0x00e3116a`, `0x00e5f94b`, and paths outside RenderObjectVisual |
| Abyss 2 types 3/4/6/24 drawn as dark meshes (RENDER-WORLDS-O report) | Not texture lookup: all their textures resolve; live draws them translucent. The near-hero BlendMesh (53) and BlendMeshLight (48) differences point at the class methods' blend fields |
| The name map's history | Only the startup opener 0x01832af3 and the world pass are rebuilt; textures from the other startup routines (`0x0183220e`, `0x0182cd66`, `0x01830aa6`, `0x0182bb43`, the out-of-capture call at `0x0182830a`) and from earlier worlds the client has not released are not |
| Other model loaders (players, items, helpers, NPC/monster textures) | Unchanged; they keep their existing lookup rules |
| Headless tour emitters | `draw_all` is opt-in so concurrent lanes keep comparable numbers; 25 steps do not reach the flames' steady state |
| Vulcanus particle requests counted unsupported (11–13 per 25 drawn steps) | Not identified |
