# Client EffectManager: effect trees, owners, instancing, octree culling and callers (NATIVE-FX-002)

This finding maps the layer above the client's JSON particle system ([client-effects.md](client-effects.md),
NATIVE-FX-001): effect trees (`Children`), the owner object, creation by name, the EffectManager's octree and
frustum culling, the render pass around the effect draws, and the game code that creates effects. The rules are
reconstructed in C (`reconstructed/effects/effects_tree.c` and changes to the FX-001 sources), compared with the
client's own instructions in Unicorn (`scripts/validate_effect_tree.py`), and used by a native scene mode
(`native/core/mu_effect_scene.*`, `build/mu-effect scene`) that draws several effects over a loaded world.

"Compared" means the authored C ran against the actual client instructions in Unicorn and agreed byte for byte on
every compared value. "Static reading" means decoded instructions only. Names are ours; the RTTI type descriptors
lie in the uncaptured part of section 3.

## Identity and method

Same pinned inputs as FX-001: restored text `0x00401000` (capture09, SHA-256 `2bd5f2e9dfb68ae5…`), second section
`0x01a7c000` (run10, `c985e2e6dcd155a4…`), initialized part of the third section from x86-linux-capture-04
(`299d83842841fa2c…`). Routines read and compared (first 16 hex digits of the body digest):

| Routine | Bytes | SHA-256 |
|---|---:|---|
| base load `0x00a760b2` | 2022 | `62812b7c90603ad7…` |
| node update `0x00a75708` | 556 | `d7922aa49f12b315…` |
| clone `0x00a75934` | 483 | `06e25f2c28c7a4af…` |
| transform `0x00a76dfe` | 870 | `894325ef99237793…` |
| particle bounding box `0x00a88970` | 907 | `32535d03cfc91a4d…` |
| octree insert `0x00a8df54` | 1411 | `9d6c1869d67d74c3…` |
| octree query `0x00a8e59f` | 455 | `c07ec4fc6a29cc7c…` |
| frustum `0x00a8d821` | 1115 | `0faefa6571466bca…` |
| EffectManager render `0x00a7a30e` | 473 | `15e08793b726aa16…` |
| effect texture upload `0x00a90987` | 360 | `72cd5bc946f46505…` |
| factory `0x00a797a0` (static only) | 2580 | `9617f93b41c35790…` |

The harness is the FX-001 machine (`scripts/validate_effects.py`) plus recorded `glGetBooleanv`, `glGetIntegerv`,
`glDepthMask`, `glGenTextures`, `glTexParameteri`, `glTexEnvi`, `glTexImage2D`, `glDeleteTextures` and the
statically linked `gluBuild2DMipmaps` `0x0191b3d1`. The EffectManager object is a stand-in block: the compared
routines only read its octree pointer (`+0xb0`), which points at an octree root built by the client's own
`0x00a8e766`/`0x00a8de79` over the manager's world box.

## 1. Effect node (base class, constructor `0x00a76b51`)

Offsets read by the compared routines (the node record the validator compares is in bold):

| Offset | Field |
|---|---|
| `+0x24` | parent node |
| `+0x28` | EffectManager (constructor argument; children inherit it) |
| `+0x2c` / `+0x44` / `+0x50` | position, rotation (radians, Z then Y then X), scale |
| **`+0x38` / `+0x54` / `+0x58`** | **world position, world scale, world matrix** |
| **`+0x98`** | **bounding box (min xyz, max xyz)** |
| `+0xb0` | octree node holding the effect |
| `+0xb4` | children: `std::list` of shared pointers, `push_back` order = JSON order |
| `+0xbc` | texture (shared pointer) |
| `+0xc4` | `std::vector<int>` of owner actions that gate playing |
| `+0xd0` | owner frame at which a gated effect starts |
| **`+0xd4`** | **playing** |
| `+0xd8` | owner object |
| `+0xdc` | owner-tint flag |
| `+0xdd` / `+0xde` / **`+0xdf`** | randomduration, parentduration, **looping** |
| **`+0xe8` / `+0xec`** | **duration, time left** |

The constructor sets time left = duration, playing = 1, owner none, and runs the transform once.

## 2. Trees (compared)

* **Loading.** The base load reads the node's own keys, runs the type load and the restart, then walks `Children`:
  a child of `Type` 0 or 1 is constructed with the parent's manager and the factory defaults, loaded by the same
  routine (so trees nest; installed depth reaches 3) and appended (`0x00a75542` sets `+0x24`). Children of other
  types are skipped without error. 149 of the 370 installed files have children (730 nodes in total).
* **Transform `0x00a76dfe(external)`.** `M = R(z, y, x) * scale`, translation = position, world scale = scale. If
  an external matrix is given and is not the identity (`0x00cee51c`: diagonal within 1e-6 of 1, the other twelve
  entries within 1e-6 of 0), `M = external * M` and the world scale stays the node's own. Otherwise, if the parent's
  matrix is not the identity, `M = parent.M * M` and world scale = parent's world scale times the node's. Products
  use `0x00cf0db8` (column-major, sums in index order).
* **Node update `0x00a75708(dt, external, owner)`.** Transform, owner action gate (section 3), type update,
  bounding box (vtable `+0x0c`), octree maintenance (section 5), then every child with `(dt, NULL, owner)`.
* **Bounding boxes.** Particles `0x00a88970`: start at the world position (local space: the zero vector), grow by
  each particle's position ± `size * 0.5 * sqrt(2)` (directional billboarding: times `|velocity| * SpeedScale +
  LengthScale`); in local space the box is then transformed per row (`0x00cf2417`). Billboard `0x00a6ed9b`: world
  position ± `sqrt(w² + h²) * 0.5 * world scale`.
* **parentduration** (installed only on children, 96 nodes). When the node expires: a **billboard** loops if it or
  its parent loops and reloads from the parent's **duration** (`+0xe8`) and looping; a **particle system** (only
  when looping) reloads from the parent's **time left** (`+0xec`) and looping. FX-001 treated the flag as off; a
  top-level node with the flag would dereference a null parent in the client.

## 3. Owner (compared)

The owner is the client's world object (the record of [native-character.md](native-character.md)): action `+0x2a`,
visible byte `+0x38`, frame `+0xd0`, flags `+5`/`+6`, colour `+0x1e8`. `0x00a76a30` sets it on a node and all its
children.

* **Visibility.** Both draws return before any GL call (and without setting the drawn flag) when `owner+0x38` is 0.
* **Action gate** (node update). With a non-empty action list: an owner action not in the list clears playing;
  a listed action sets playing once the owner's frame reaches the start frame (start ≥ 0: `frame >= start`;
  negative start: `-start >= frame`). Playing is never cleared otherwise. Matching is `int == (uint16)action`.
* **Tint.** With the tint flag and both owner flags set, the fills replace the colour by `(owner colour rgb, own
  alpha)` while filling the vertices and restore it afterwards (particles `0x00a8b246`, billboard `0x00a707b0`). The
  FX-001 statement that the fill "writes the tint back" is corrected: it is a temporary replacement.

## 4. Creation by name and instancing

* **Factory `0x00a797a0`** (static reading). `EffectManager::Create(out, name, position*, rotation*, scale,
  useTemplateTransform, unused word*, tintFlag, actions (vector by value), startFrame)`, `ret 0x30`. The manager keeps
  a template cache (`std::map<std::string, shared_ptr>` at `+0xf4`); on a miss it opens the file with an `ifstream`,
  parses the JSON, constructs the root by `Type` with the manager, runs the base load and caches it. Every call
  returns a **clone** of the template; the template itself is never updated. The factory does not add the instance
  to any list: the caller keeps the shared pointer.
* **Clone `0x00a75934`** (compared, 400 cases): the type clone (vtable `+0x18`, particles `0x00a8986a`, billboard
  `0x00a6fb0a`) constructs a new node with the template's parameters and the given position, rotation and scale
  (constructor state: time left = duration, not drawn, no particles), copies the texture, clones every component,
  then sets the action list, start frame and tint flag and clones the children with their own transforms.
* **The emitter constructor `0x00a81787` replaces `Frequency` 0 by 1**, and the emitter clone `0x00a80633`
  constructs anew. Instances therefore never reach the `rand() % 0` divide fault of FX-001; only a tree that is
  loaded and updated directly does, which the game's factory path never does.

## 5. EffectManager, octree and culling (compared)

* The EffectManager is itself an effect node (0xfc bytes, base constructor with the name "EffectManager", vtable
  `0x01a80ec8`, render at slot 1 `0x00a7a30e`, second vtable at `+0xf0`), a magic static at `0x01d22c54` returned by
  `0x00aee554` (21 callers). Its init `0x00a79534` checks `GL_ARB_vertex_buffer_object`, creates the particle and
  billboard vertex buffers and the octree root over (-12750, -12750, -25500)..(38250, 38250, 25500) (static reading
  of the constants; the box is used by the harness).
* **Octree node** (0x44 bytes): box, depth, eight children, `std::list` of effects. **Insert `0x00a8df54`**: refuse
  when the node's box does not contain the effect's; below depth 6 pick the octant from the effect box centre
  (bit 0: x above the node centre, bit 1: z above, bit 2: y **below**), recurse into an existing child, or create
  it with centre `node centre ± size/8` and half size `size/4` (all axes from the x size) when it contains the
  effect; otherwise store here (removing it from its previous node). **Node update:** a managed effect whose box
  left its node is removed (`0x00a8e4d7`, order kept) and reinserted from the root. An effect outside the world box
  is never in the tree and never drawn.
* **Frustum `0x00a8d821(eye, forward, up, fov, aspect, near, far)`** fills the camera record `0x0bdc5ae8` (eye,
  forward, right = forward × up, up, then six planes): near `(forward, -forward·eye - near)` and far `(-forward,
  forward·eye + far)`, both scaled by `1/|n|` (`0x00cf65af`), and four side planes through the eye and the far
  corners (`0x00cf66a4`: edges normalised, normal normalised, `d = -n·eye`), with half height `tan(fov/2) * far`.
* **Query `0x00a8e59f`**: a node or an effect is rejected when its box centre is behind a plane by more than the
  half diagonal (`d < 0 && d² > |half extents|²`); visible effects are listed per node in list order, then the eight
  children recursively.
* **Render pass `0x00a7a30e(frustum)`**: with no visible effect, no GL call. Otherwise `glGetBooleanv`
  GL_ALPHA_TEST, GL_TEXTURE_2D, GL_BLEND, `glGetIntegerv` GL_BLEND_SRC, GL_BLEND_DST, `glGetBooleanv`
  GL_DEPTH_WRITEMASK; `glDepthMask(0)` if writes were on; `glDisable(GL_ALPHA_TEST)` if it was on; each visible
  effect's draw with the frustum record as its camera; `glBindTexture(GL_TEXTURE_2D, 0)`; restore texture enable,
  blend factors, blend enable, depth mask and alpha test. **Depth test and depth function are not touched**: the
  effects use whatever the preceding pass left (FX-001's "depth test on" is not set here).
* **Texture parameters** (`0x00a90987`, compared for 35 argument sets): nothing without pixels or with a zero size;
  otherwise a new name, `GL_TEXTURE_WRAP_S/T = wrap`, `GL_TEXTURE_ENV_MODE = GL_MODULATE`, then min/mag filter and
  `glTexImage2D` (level 0, RGBA type `GL_UNSIGNED_BYTE`), or with mipmaps `GL_LINEAR_MIPMAP_NEAREST` /
  `GL_NEAREST_MIPMAP_NEAREST` and `gluBuild2DMipmaps`. The effect base load requests `GL_LINEAR`, `GL_REPEAT`, no
  mipmaps (`0x00a7620a`); the texture manager `0x00a8fb55` forwards them through its per-format loaders (static).

## 6. Frame loop and callers (static reading)

* **Main render `0x0185916b`**: `EffectManager` node update with `dt = [0x01cf103c]` (0.1), no external matrix and
  no owner (`0x01859941`), then `render(0x0bdc5ae8)` (`0x01859962`). Instances are updated by their owners, not by
  the manager.
* **World objects** keep effects in a list at object `+0x3d0`. Attach `0x0129f9c6(effect, bone, followBone, timed,
  lifetime)` (15 callers) sets the owner on the tree and stores the record {effect, template scale, bone, flags,
  lifetime}. Per frame `0x0129f671` (4 callers: `0x009a9ae2`, `0x01363260`, `0x016d5020` ×2) removes expired timed
  records, sets the effect scale to template scale × object scale (`+0xa0`) and calls the node update with the
  object's matrix as external matrix: the object's world matrix (bone -1, `0x0129faee`), a bone matrix
  (`0x0129fd4f`), or without bone following a uniform scale by `+0xa0` with the object's position `+0x158`.
  `0x0129f4cb` does the same once with `dt = 0` right after map objects are set up.
* **Factory call sites** (15):

| Site | Effects (scale, position) | Attachment |
|---|---|---|
| `0x00d93599` (from `0x00d99dd9`) | `fire09-red01` (35), `Sparkle21-red01` (50), `smoke17-red01` (50), `twinkle10-red02` (200), all at (0, 0, -20) | bone 20, follow bone |
| `0x0137fbac` monster type 873 | `leaf_particle_F2e` (9, (0, 0, 70)) | bone 1, follow |
| `0x0137fbac` types 750–753 | `twister02-cyan01` (90), `twister03-cyan01` (230) | bone 1, follow |
| `0x0137fbac` type 758 | `twister02-magenta01` (90), `twister03-magenta01` (230) | bone 1, follow |
| `0x0137fbac` type 838 | `sparkle20-cyan01`, `fire10-cyan01` (scale and bone from a per-monster list) | listed bones |
| `0x0137fbac` type 925 | `sparkle20-red01`, `fire10-red01` (as above) | listed bones |
| `0x0183067e` (from the world loaders `0x00e21f75`, `0x0182876e`, after the manager clear `0x00a7a1b4`) | per map and object type table entries: name, position, rotation, scale, flags, start frame, actions | table bone and flags |
| `0x0114203d` (from `0x009af699`) | entries of a per-object table at `this+0x38`; its callers sit next to the Muun (pet) code (`0x00c0747e`, "SetOwningHeroMuun") | table bone and flags |

  The monster types are the `case` values of the creation switch in `0x0137fbac` (tables `0x0138d070`/`0x0138ce1c`
  and `0x0138d430`/`0x0138d20c`). No item-glow, item-level or skill code calls the factory: those effects use the
  client's older effect code, not this system. The sources of the two tables were not found in plain installed
  files (the names do not occur outside `Data/Effect`).

## 7. Verification numbers

Private run of `scripts/validate_effect_tree.py` (`--mutations 600 --clones 400 --scenes 300 --frames 30`, report
`~/Documents/mu-mac-tools/native/scratch/fx2/reports/full-02.json`, library SHA-256 `65fffcc447d9d698…`):

| Measure | Value |
|---|---:|
| Cases (370 installed trees, 600 mutated trees, 400 clones, 300 scenes) | 1,670 |
| Tree nodes | 5,966 |
| Frames compared | 43,621 |
| Node records compared | 134,261 |
| Draws compared (direct and inside render passes) | 119,973 |
| VBO vertices compared (36 bytes each) | 1,307,044 |
| Particle records compared (136 bytes each) | 303,472 |
| Octree placements compared (depth and box) | 31,759 |
| Render passes compared (visible order and GL calls) | 3,912 |
| Visible effects drawn inside the passes | 17,471 |
| Frustum records compared (0x90 bytes) | 300 |
| Texture uploads compared (`0x00a90987`) | 35 |
| `rand()` calls matched | 303,071 |
| Client divide faults matched (loaded trees without `Frequency`) | 91 |
| Mismatches | **0** |
| Distinct effect-code basic blocks executed | 4,974 |

Per frame and per node the run compares the node record (world matrix, world position, world scale, duration,
time left, bounding box, playing, looping, drawn), the particle records (136 bytes), each draw's VBO bytes and draw
state, and the `rand()` count; for scenes also the frustum record (0x90 bytes), the octree node of every effect
(depth and box), the visible effects in render order, the render pass's GL calls around the draws and each draw
inside the pass. Mutations vary every node's parameters (FX-001 mutator), child transforms, parentduration,
looping and durations, external matrices, owner tint flags and colour, action gates and start frames, owner
action/frame changes and visibility per frame. Scenes place 2–6 effects (installed or mutated; half factory
clones, half owner-attached with an object matrix) around random points of the world box, some outside it, and
view them through random frusta.

The client's `sqrt` of a NaN takes the UCRT error path, whose state the harness does not initialise; a case that
reaches it is stopped and listed under `skipped_crt_nan` (none in the full run; one clone case of a smaller
development run, a mutated directional particle system with a NaN velocity). 2,995 NaN words were canonicalised as
in FX-001 (x86 "real indefinite" against the AArch64 default NaN).

The FX-001 comparison (`scripts/validate_effects.py --mutations 1500 --frames 60`) was rerun on the changed
sources: 1,870 cases, 109,774 frames, 44 matched faults, 0 mismatches, the same counts as before.

Portable CI checks: `reconstructed/effects/test_effect_tree.py` (children and skipped types, parent and external
transforms, both parentduration rules, clone without `Frequency`, action gate, tint and visibility, frustum,
octree placement and culling, render-pass calls) and the scene and tree tests in `native/tests/test_native_effect.py`.
Private: a 110-case instruction comparison and the demo scene over Lorencia.

## 8. Native module

* `mu_effect` now loads and runs the whole tree (node update, per-node textures, draw of every node).
* `mu_effect_scene` follows the client: a template cache keyed by the client path, clones per request,
  owner-attached instances with an object matrix (`mu_effect_object_matrix`: uniform scale then translation, the
  no-bone case of `0x0129f671`), node updates that maintain the octree, and a render pass that builds the frustum,
  queries the octree and draws the visible effects in octree order with depth writes and alpha test off.
* `build/mu-effect scene ROOT --world N --demo` places the effects of the call sites above over the loaded world
  (merged `native/core/mu_terrain.*`, used read-only) and renders them after the terrain into the same depth buffer.
  Renders stay local: `~/Documents/mu-mac-tools/native/renders/effects2/`.
* Viewer choices (not client code): the collider's ground is `mu_world_height_at` and the world's normal grid, not
  the client's `0x016cc9e2` (bilinear with attribute and scene special cases) and `0x016ccbb6`; the demo anchors
  stand on the terrain without models or bones.

## 9. Limits and next steps

* Not compared: the factory's file and cache path, the texture manager's forwarding, the main-loop calls and the
  world-object attach and per-frame update (`0x0129f9c6`, `0x0129f671`, `0x0129f4cb`); bone matrices
  `0x0129faee`/`0x0129fd4f`; the client terrain height/normal routines.
* The map-object and Muun effect tables are not decoded; finding their files would let the native world place the
  same effects as the client.
* Next: decode the effect tables, attach effects to native characters and monsters (bones from the character
  module), and port the scene pass into the frame loop and the OpenGL viewer.
