# Current status

## Repository split, 2026-10-21

This repository (renamed from `mu-the-matrix-recovery` to `mu-the-matrix-native`) is now the native track only.
The Wine track (Mu The Matrix.app, the disk image, the installer kit, the Wine runtime packaging, mugl, the CPU
hotpatches, the mscoree proxy, fast x87, their tests and `docs/research/mac-*.md`) moved with its history to
[mu-the-matrix-mac](https://github.com/fryezero/mu-the-matrix-mac). The live-state readers moved from
`mac-play/diagnostics/` to [`live-readers/`](../live-readers/README.md) and the app icon script to
`native/app/icon/`. The README was rewritten with screenshots in `docs/images/` (hash-pinned; `docs/media/` removed).

## README refresh, 2026-10-20

The main README now separates playable Wine support and its measured 25 FPS optimization
work from the native offline reconstruction. It reuses six existing comparison captures
in `docs/media/`, unchanged, with provenance and a hash-pinned audit exception. It records
the zoomed-out boss-fight and runtime-distribution limits rather than promising 25 FPS
in every situation. No game runtime or recovery behavior changed in this documentation task.

Updated 2026-10-17. The target is the exact installed Mu The Matrix client.
The later destination is native macOS gameplay. A playable source build does
not exist yet.

## Working components

- The startup decompressor is reconstructed in C. Four original compressed
  blocks match independent decoding, but the result is still protector code.
- The isolated QEMU x86 Linux/Wine guest restores a repeatable 23,572,480-byte
  code section. The selected second image section is also captured twice with
  matching digests. No Windows PC is required for this analysis route.
- Authored 64-byte copy/clear source matches captured instructions in 393/768
  synthetic cases. Controlled cofactor/inverse source matches 1,680/1,050 cases.
- The BMD filename call path reaches a version-dispatching model-read routine.
  Its v12 decoder now has authored C matching 4,048 synthetic cases and all 180
  installed v12 payloads, covering 3,176,971 encrypted bytes. Exact overlap and
  signed-length behavior are preserved. [Evidence](research/client-model-loader.md).
- The observed v15 key-setup target has authored C matching 1,320 synthetic
  instruction cases across 16/24/32-byte keys, alignments and no-op gates.
  [Key evidence](research/client-lea-key.md). The ECB decoder now matches 12,960
  actual-code guest cases and 1,152 scalar instruction cases. All 11,583 installed
  payloads match the independent reader, separately from original-code testing.
  [Decoder evidence](research/client-lea-decode.md).
- Images: 19,703 of 19,707 wrapper candidates decode. One remaining candidate is
  editable mesh text; the three inconsistent terrain images are valid height
  inputs, because the client reads them at a fixed offset without parsing the
  BMP header ([terrain finding](research/client-terrain.md)).
- Terrain (NATIVE-TERRAIN-001). `.map`/`.att` (Modulus or v12, attribute XOR),
  8/24-bit heights, light maps, normals, light, wave and the per-tile GL stream of
  RenderTerrainTile `0x016ccda5` have authored C (`reconstructed/terrain`) equal
  to the actual instructions. That covers every tile of installed Lorencia and
  Twisted Karutan in both passes and every installed height, light and attribute
  file. `mu-terrain` and `mu-viewer --terrain` render worlds natively. Static
  objects are blocked: the installed `.obj` files do not decode with the routine
  the captured loader calls. NATIVE-TERRAIN-002 adds dynamic lights, the per-world
  water/lava scrolls and animated layer, the frustum box and tests, decals and the
  resolved 24-bit height choice (handler table; worlds 134..145), all compared in
  Unicorn ([finding](research/client-terrain-frame.md)).
- Static objects (NATIVE-OBJECTS-001). The `.obj` loader `0x016d9ac5`, its record layout (versions 0..5) and
  the per-world object model table of `0x018392db` have authored C (`reconstructed/objects`) equal to the
  actual instructions (1,002 synthetic files, 60,000 world/type pairs). Run on the installed files, the client's
  own loader instructions make OpenWorld refuse all 84: the transformation that makes them readable lies past the
  protection boundary. `mu-terrain`/`mu-viewer --terrain --objects` draw objects from a decoded plaintext or a
  labelled model gallery. A live read of a running client's object list (owner-authorized, single run) gave the
  real placements of Lorencia, World94, World95 and World142 and character-select marker 1; `mu-world` and
  `mu-charsel` draw them from local files with `--objects-dir`. [Evidence](research/client-objects.md).
- World objects at runtime (NATIVE-OBJECTS-002). CreateObject (Lorencia cases, Tormenta handler), MoveObjects/MoveObject
  (alpha, animation tick, Lorencia lights and CreateFire, Tormenta sounds), RenderObjects culling, RenderObject and the
  object body light over RequestTerrainLight have authored C equal to the actual instructions (2,000 cases per
  family, 9 planted mistakes detected) and to live object lists (13,727/13,727 created objects; drawn body lights
  bit-identical or only brighter by light sources). `mu-world` and `mu-terrain --object-steps` light, animate, cull
  and draw objects with blend meshes; fire particles are a labelled stand-in. [Evidence](research/client-objects-render.md).
- Login scene 3D world (NATIVE-LOGIN-001). The login render's 3D part `0x01857ed9..0x0185810e` and tick head
  (`reconstructed/scene`, 1,000 + 1,000 cases) and the login world's handler `CGMLogInScene_Ex` (create, move, visual,
  custom render and after-character slots, RenderObjects_AfterCharacter; `reconstructed/objects/login_world.c`, 6 × 2,000
  cases, 9/9 planted mistakes) equal the actual instructions; the camera, far plane and object state match a live read
  of the server-select screen. `mu-client` and `mu-render ui login|servers --scene` draw World95 with its ship, sky and
  island behind the 2D layer; sprites and particles are stand-ins. [Evidence](research/client-login-scene.md).
- Character creation, deletion and the system menu (NATIVE-CHARCREATE-001). The CharacterSelect window's create
  panel, the character-created and character-deleted answers, the message-box results, the preview render, the
  class-name switch (codes 9 Slayer / 10 Gun Crusher included) and the winSystemMenu game side
  (`reconstructed/charsel/charcreate.c`; `validate_charcreate.py`: 4,368 Unicorn cases, 0 mismatches, 6/6 planted
  mistakes) equal the actual instructions. `mu-client --gfx` creates characters through the panel (the class's NewFace
  bust under the client's preview camera, the Filter/FilterName tables), deletes them through the client's three
  Caution boxes and opens the menu with Esc; OFFLINE DEMO: a local store answers. [Evidence](research/client-character-select.md).
- Character-select picking and GFx list (NATIVE-CHARSEL-003). The list movie's game side (`reconstructed/charsel/charsel_gfx.c`:
  init, list, show, SelectIndex, row click, reorder arrows, callbacks; 2,100 Unicorn cases, 0 mismatches, 5/5 planted
  mistakes) and the star dragon effects 0x5ac/0x5ad (CreateEffect/MoveEffect cases in `validate_skill_fx.py`) equal the
  actual instructions. `mu-client --gfx` plays CharacterSelect.swf over the scene (select by click, enter by double
  click or Enter, create = OFFLINE DEMO no-op), the 3D pick enters on a double click on the character, markers 0/2..4
  are shown unused. [Evidence](research/client-character-select.md).
- Character-select scene at runtime (NATIVE-CHARSEL-002). World94's handler `CGMCharacterScene_Ex` (create, move,
  visual, custom render and after-character slots; `reconstructed/objects/charsel_world.c`, 12,000 cases, 10/10
  planted mistakes) and the particle kinds WATERFALL2/3, fantaB and the selection light 0x8022 (30,494 particle
  cases) equal the actual instructions. `mu-charsel`, `mu-charsel-window` and `mu-client` run the objects through the
  client's lifecycle with sprites, particles and part shadows; CreateFrustrum2D now takes the camera record's
  distances. A live read of the character-select screen: 237/237 objects equal, the waterfalls' scroll advanced 103
  exact steps, and the native session marks the same 221 visible and 38 after-character objects.
  [Evidence](research/client-character-select.md) (section 9).
- Model lighting (NATIVE-LIGHT-001). A live read showed the client's light-override byte `0x01cf1048` = 1 (light
  vector (1.3, 0, 2)) and RenderObject poses static objects with the body scale in the bones, so normals scale the
  light. The native scenes now do both, and light monsters/NPCs with frame light + 0.2. The native object light equals
  the client's pose builder and transform under the live state on 171,902 normals (login and Lorencia, Unicorn).
  Login regions are within 5% of a live screenshot (sky 0.62 → 1.00, hull 1.48 → 0.99). Lorencia object regions
  are within 3%, except one region next to a player's glow. [Evidence](research/client-model-light.md).
- Models: 12,663 of 12,754 unique BMD-extension files parse. Versions 10/12/14 pass
  all 701/180/216 files; v15 passes 11,566 of 11,583. Seventeen v15 inputs remain
  rejected by the strict reader and 74 other/table envelopes are unsupported.
  The client loads all 17 unchecked (MODEL-EDGE, executed): the dummy-parent
  bones are unused IK Chain leaves, and the other fields read unowned memory at known
  addresses. The client-layout readers and the native viewer reproduce this
  ([finding](research/model-edge.md)).
- Selected bone/pose instructions show that dummy records leave output slots
  unwritten, while children compose from prior caller-buffer contents. Those
  contents are unknown. Raw call-search totals remain candidates.
- The hierarchy pose-composition source matches 5,176 controlled binary32
  instruction cases; 24 out-of-domain attempts are recorded separately.
  [Evidence](research/pose-concat.md). Actual prior pose state remains unknown.
- The rotation helper `0x00d00724` (ZYX Euler angles to x,y,z,w quaternion)
  has authored C matching 8,012 controlled cases bitwise. Its actual body and client
  SSE2 sine/cosine run with captured flag 1 and no stubs. The C substitutes host
  libm trig; binary32 trig results agree in all 48,072 calls, including
  host-midpoint candidates. [Evidence](research/client-rotation.md).
- The BMD bone-track loop `0x012b4225..0x012b4441` has authored C
  (`mu_bone_tracks_read`). The actual loop, memcpy, operator new/malloc and
  rotation/trig code run without client stubs; only the HeapAlloc import and
  two uncaptured globals are modelled. 342 synthetic comparisons and all 11,962
  installed v12/v14/v15 models accepted by the readers match, including
  4,759,146 per-key rotations. Output layouts and allocation behavior are recorded.
  [Evidence](research/client-bone-tracks.md).
- The pose builder `0x012b5064` has authored C (`mu_pose_build`) plus its
  quaternion compare, slerp, quaternion-to-matrix and angle-to-matrix helpers.
  It slerps q(prior action, prior frame) toward q(current action, integer frame)
  by the frame fraction, lerps positions, resets out-of-range frames to key 0
  and composes each bone with the root global or its parent's output slot.
  Seeded by the actual bone-track loop and run with no client stubs, it matches
  483 synthetic calls, 1,822 direct helper calls and 47,833 calls on all 11,962
  installed models the readers accept. Lerp and modulo-wrap controls fail.
  [Evidence](research/client-pose-builder.md).
- CPU skinning. The model transform `0x012b5bde` (`mu_model_transform`)
  multiplies each vertex by one bone matrix from the pose builder, applies
  body scale/origin, rotates normals and computes clamped per-normal light.
  The animation tick `0x012b4dd3` (`mu_animation_tick`) sets the prior
  frame/action when the integer frame changes. Against the actual
  instructions, with no client stubs, they match:
  * 226 synthetic transforms, 24 synthetic models chained through the actual
    builder and 481 synthetic ticks;
  * all 11,962 installed models the readers accept, run after the actual
    bone-track loop and builder (3,814,006 vertices), plus 35,871 installed
    ticks.

  Four negative controls fail. All 314 builder call candidates are classified.
  Keep-root calls follow a root setter used for attachments. The mesh draw
  `0x012b8d1d` emits one `glBegin(GL_TRIANGLES)` per mesh with per-corner
  glTexCoord2f, glColor and glVertex3fv straight from the transform output;
  this is a static reading against import slots named from the guest's Wine
  opengl32. [Evidence](research/client-skinning.md).
- All 370 effect JSON files parse and their 92 distinct texture references exist.
- Frame loop (static). The frame driver `0x01851d39` runs game logic in fixed
  40 ms steps from an accumulator. It caps rendering at 25 FPS with
  `Sleep(40 - elapsed)` after SwapBuffers, timed by GetTickCount. The 40 is a
  compiled-in immediate at `0x0185266b`, `0x0185266f` and `0x01852690`; no
  config, data or server value feeds it. Themida packs the code, so the bytes are
  not in `main.exe` and changing the cap needs an in-memory write after unpacking.
  The four-vertex fans come from the terrain tile renderer (one per tile per layer),
  terrain decals and 2D UI helpers. The only per-frame VBO streaming is the JSON
  effect system: a 144-byte sprite buffer rewritten whole, and a 144,000-byte
  particle buffer written as `n*144`-byte prefixes, each drawn as `GL_QUADS`.
  [Evidence](research/client-frame-loop.md).
- Native model viewer (NATIVE-VIEW-001). `native/` builds an arm64 macOS viewer with SDL2 and OpenGL 2.1; no Wine or Rosetta. It loads v10/12/14/15 models through the repository's decoders. It animates them with the reconstructed tick and pose builder, after the bone-track loop, and skins them with the reconstructed transform. It draws them through a platform-neutral port of the mesh-draw corner loop. This is a viewer, not a client.
  * Golden data. The viewer's vertex streams equal the authored libraries and the validators' Python models byte for byte in 50 synthetic cases (CI). A full private run covered 12,627 installed models and 3,909,196 vertices (reported, single run, not re-run in review).
  * Mesh draw. The GL call stream equals the client's own mesh draw executed under Unicorn (CLIENT-MESHDRAW-EXEC-001, below); CI pins the client-verified digests.
  * Renders. Software-render hashes are pinned; CI checks them on macOS arm64 and Linux x86_64. Headless GL agrees with them on macOS (CI, synthetic) and on three installed models (reported).
  * Review. PR #66 was merged without independent review. The post-merge review found a TGA image-ID over-read and missing SDL2/libjpeg-turbo notices, both now fixed; see the handoff.
  * Limits. Live draw arguments and animation control are the viewer's own. [Evidence](research/native-viewer.md).
- Character assembly (NATIVE-CHAR-001). The native viewer and `mu-render character`/`chardump` assemble a player. Inputs: the shared `Player.bmd` skeleton (model 0xa91, 390 actions), the class body parts for a class byte (types `0x3700+…` plus skin index `(class&15)+16*(tier-1)`), and weapons/shield/wing on bones 33/42/47. Items attach through the root setter `0x012b7019` and a keep-root pose.
  * Instructions (reported, private single run; needs the restored client text, so not in CI). The rotation/transform position routines (384 cases), the class tier/skin/skip helpers (3x256) and the loader's part table (380 calls) match the actual instructions under Unicorn.
  * Installed chains (reported, private single run). `Player.bmd` posed by the actual builder (4 poses), then 300 class parts and 267 items (141,767 item vertices) through the actual root setter, builder and transform, are byte-identical to the authored C.
  * Golden data. `chardump` equals an independent reference in 18 synthetic cases (CI, macOS and Linux) and on 5 installed characters (reported, private).
  * Limits. The render routines themselves are static readings. World-path weapon details, attribute branches, back-carried weapons, effects and action names are open. [Evidence](research/native-character.md).
- World character render (NATIVE-RENDERCHAR-001). RenderCharacter `0x01363260`, RenderPartObject `0x017e63f4`, the item render `0x0176ce74` (item level glow +0..+15, excellent, ancient, quality caps), BackCarry `0x0139db9a`, the link render `0x012bd910` and the +15 `class15_*` attachments are executed under Unicorn with recorded mesh-draw calls and compared with `reconstructed/renderchar` (reported, private single runs: RenderObjDraw 16,150/16,150 random cases bit-exact on generic types, RenderCharacter plans 252/252, back-carry roots 1,045/1,045; type-specific types, back-carry matrices and monster weapon link bones are extracted tables). `mu-render character/actor --world-render` draws them. The EnchantEffect glow colour table is runtime data and stays a parameter; shadows and effects are not rendered. [Evidence](research/client-renderchar.md).
- Actors (NATIVE-ACTOR-001). `reconstructed/actors` and `mu-render actor` animate monsters and NPCs: OpenMonsterModel `0x0180b0f4` (model index type+0x7a5, Monster<type+1>.bmd, default/per-type action speeds), the character animation step `0x013960d2`, SetAction `0x012affa4` and the unarmed stop action `0x0139d6da` match the actual instructions under Unicorn (reported, private single run: 1276/1276, 4442/4442, 3000/3000, 13,824/13,824; negative controls differ). Server-class, NPC-file and Player-speed tables are extracted by emulating CreateMonster, OpenNpc and the player loader (949 classes, 110 NPC files, 213 speeds). Player poses per weapon are a static reading; monster weapons are not rendered. [Evidence](research/client-actors.md).

- Network protocol layer (NATIVE-NET-001). `native/core/mu_protocol.*` plus the `mu-proto` CLI reconstruct the client's own framing and send obfuscation around its `ws2_32` calls: C1/C2/C3/C4 headers and size rules, the 32-byte chained send XOR (`XorData` `0x00d52055`), the packet builder (`Begin`/`AddData`/`WriteSize`) and the receive dechunker (`nRecv` `0x01290792`). The authored C equals the client's actual instructions under Unicorn (`scripts/validate_protocol.py`: 500 build cases, 300 receive-framing cases, 0 mismatches). The C3/C4 CryptoModule (17 block ciphers identified by emulation KATs, key string recovered) and the receive dispatcher / login + server-list packet bodies are mapped but documented as the next step, not reconstructed. Offline only; no server contact, no bottle touched. [Evidence](research/client-net-protocol.md).
- Camera, picking, input and frame loop (NATIVE-FRAME-001). `reconstructed/camera` ports gluPerspective2, BeginOpengl's camera part, CreateScreenVector, the projections, MoveMainCamera's in-world path with the wheel FOV zoom (35/30/20), the terrain-pick chain (FaceNormalize, CollisionDetectLineToFace, InsideTest, RenderTerrainTile picking), the per-step key scan, the window-procedure mouse globals and the frame cap. `scripts/validate_camera.py` runs the client's instructions in Unicorn: 33,250 comparisons, 0 mismatches, and 11 planted mistakes all detected (private run). The scene state machine and key bindings are static. `native/` adds a frame-loop skeleton (`mu-frame`, `mu-frame-window`) with a flat placeholder terrain. [Evidence](research/client-camera-input.md).
- Native audio (NATIVE-AUDIO-001). The client plays everything through FMOD Ex (16 channels, groups Music/Environment/Effect, 2D only, one instance per sound id, no positional audio). `reconstructed/audio` reproduces its sound table, music player, per-frame ambient/music selection, OpenWorld music volume and options; every FMOD call matches the client instructions in Unicorn (2,407 frame cases, 2,023 manager scripts with 79,176 calls, 107 init scripts, 277 worlds, 9,153 UI conversions). `native/build/mu-audio` runs that logic on an arm64 software mixer and renders scripts to WAV. Music indices 43/44, event-world managers and one protector-virtualised gap stay open. [Evidence](research/client-audio.md).
- JSON effects (NATIVE-FX-001). `reconstructed/effects` ports the `.ein` loader, the particle system (type 0) and billboard (type 1) updates with every component, emitter shape and curve, and both vertex fills. `scripts/validate_effects.py` runs the client's own loader, update and draw in Unicorn: 1,870 cases (all 370 installed files plus 1,500 mutations), 109,774 frames, 0 mismatches in particle records, VBO bytes, draw state and `rand()` counts (private run). Emitters without `Frequency` hit the client's own `rand() % 0` divide fault at `0x00a80790`, matched in 44 cases. `native/` adds `mu-effect` (render, contact sheet, dump, scan). The EffectManager and render state are static. [Evidence](research/client-effects.md).
- Effect layer (NATIVE-FX-002). `reconstructed/effects/effects_tree.c` adds effect trees (`Children`, parent and external transforms, parentduration), the owner (action gate, visibility, tint), template instancing, bounding boxes, the EffectManager octree, frustum culling, the render pass and the effect texture upload. `scripts/validate_effect_tree.py` compares them with the client in Unicorn: 1,670 cases (370 installed trees, 600 mutations, 400 clones, 300 multi-effect scenes), 43,621 frames, 134,261 node records, 31,759 octree placements, 3,912 render passes, 0 mismatches (private run). Factory instances never fault: the emitter constructor turns `Frequency` 0 into 1. `mu-effect scene` draws several effects over a loaded world. The 15 factory call sites (monsters, map objects, Muun table) are mapped statically. [Evidence](research/client-effect-manager.md).

- Mesh draw executed (CLIENT-MESHDRAW-EXEC-001). The client's mesh draw `0x012b8d1d`, body `0x012bb35a`, GL state wrappers and texture-name parser `0x01185111` run under Unicorn on the pinned text with no client stubs; only the bitmap map lookups, `_getptd` and the case memory are modelled. The native port's GL call stream, final caches and colour, and written tables equal the client in 207 synthetic viewer, 500 mutated and 2,713 installed cases (7,033,092 records). Every branch probe is reached and four negative controls fail. This replaces the viewer's static state reading and the normal-table placeholder. Mesh `+0x1c` records come from texture names (parser verified on 9,461 installed names; loader wiring static). Client sin/cos/pow match the host libm in binary32 on the SSE2 path; arguments of magnitude 90,112 or more take an x87 fallback that Unicorn cannot verify. [Evidence](research/client-meshdraw-exec.md).
- Client data tables (NATIVE-DATA-001). `reconstructed/data` holds the table codecs (three-byte XOR `0x00976855`/`0x01072ebc`, checksum `0x00976895`, package XOR `0x00f1600f`) and the decode-unit schedules of 45 table loaders. The actual instructions match in 11,120 synthetic and 170 installed-image codec cases. All 45 installed loaders (43,968 units) and 51 checksum/zero-count mutations match in Unicorn. The item model getter `0x00eaa8cf` runs with the real Item.bmd loader and lookup: model index = code + `0xae6`, folder/file at record +8/+0x10c, all 4,881 items matched. `native/build/mu-data` dumps tables locally. Lang.mpr text entries stay zip-encrypted (password behind the protection boundary), and skill/minimap/movereq loaders are not located. [Evidence](research/client-data-tables.md).
- Walking around the world (NATIVE-WORLD-001). `reconstructed/movement` ports MovePath (path spline, turn), MoveCharacterPosition, CharacterMoveSpeed (Player: 12 units per 40 ms step, 15 once the run counter reaches 40), RequestTerrainHeight, SetAction, and the unarmed walk/stand selection (its path finder is now the single port in `reconstructed/path`, NATIVE-PATH-001); `scripts/validate_movement.py` compares them with the client's instructions in Unicorn (0 mismatches, planted mistakes detected; private run). Worlds' camera records (`Camera_Angle_Position.bmd`, Lorencia FOV 39) are decoded. `mu-world`/`mu-walk` walk the hero across real terrain with the client camera, pick and zoom. The near plane (20) and the path finder's direction table come from the runtime capture of the packed data section. [Evidence](research/native-world.md).
- A living native world (NATIVE-WORLD-002). The hero's footstep sound (PlayWalkSound `0x013b1f61`, its trigger in `0x013b23f8`, the foot reset after the animation step) and HeroTile are reconstructed in `reconstructed/audio/hero_sound.c` and compared with the client in Unicorn (31,250 cases, 0 mismatches). `mu-world`/`mu-walk` now play the client's footsteps and per-frame Lorencia music/ambient (SDL2 audio in the window, WAV headless), draw the terrain through the client frustum and tile tests, and animate monsters and NPCs from a labelled demo placement with the client action tables and the EffectManager effects their creation attaches (extracted for six classes). [Evidence](research/native-world-alive.md).
- Combat (NATIVE-COMBAT-001). `reconstructed/combat` ports the damage text (colour, scale, ShowDamage, CreatePoint, MovePoints, RenderPoints, RenderNumber), SetAttackSpeed (lifted), SetPlayerAttack, the in-range test, the monster hit predicate and the dead fade; `scripts/validate_combat.py` compares 12 routine families with the client in Unicorn (25,200 cases, 0 mismatches, every negative control detected; private run). Static readings map MoveHero's attack case (range, facing), the AttackTime timeline, the skill receive handlers and the end-of-attack visuals (older effect pools, not the EffectManager), the death counter and SetPlayerShock. `mu-world --combat` fights demo-placed monsters with click-to-attack, skills, arrows, damage text, hit/death/fade/removal; the server side is a labelled demo. [Evidence](research/client-combat.md).
- Combat effects, area skills, hero hit/death, sounds (NATIVE-COMBAT-002). `reconstructed/combat/skill_fx.*` ports the client's older effect system for skills and projectiles: CreateEffect/MoveEffect for arrows, Fire Ball, Energy Ball, Heal, Hellfire's circles, Inferno, Evil Spirit's laser, the Twisting Slash swirl and impact stones, CheckClientMagic, CreateParticle/MoveParticles/RenderParticles (Fire01, Thunder01, Spark03), CreateJoint/MoveJoint/RenderJoints (Heal, Evil Spirit), and SetPlayerShock/SetPlayerDie's Player branches and the attack swing sound; `scripts/validate_skill_fx.py` compares 10 families with the client in Unicorn (30,000 cases, 0 mismatches, 12/12 negative controls detected; private run). `mu-world --combat` draws skills through these pools with terrain lights, adds Evil Spirit/Hellfire/Inferno (keys 7..9), the hero's hit/death/respawn (`--hero-hp`) and combat sounds. [Evidence](research/client-combat.md#8-the-older-effect-system-area-skills-the-heros-hit-and-death-sounds-native-combat-002).
- Character select (NATIVE-CHARSEL-001). Scene 5 runs in world 0x5d (World94) with MoveMainCamera's camera-record path (now ported and verified); `reconstructed/charsel` ports the slot markers (CGMCharacterScene_Ex::CreateObject, every character on marker 1), CreateHero/SetCharacterScale (scale 1.7), RenderCharacterScene (one shown character, rotating highlight decals) and the Enter/Esc tick, and `reconstructed/ui/ui_charsel.c` the legacy window CCharSelMainWin; `scripts/validate_charsel.py` and `validate_charsel_window.py` compare them with the client in Unicorn (0 mismatches, planted mistakes detected; private runs). `mu-charsel`/`mu-render charsel`/`mu-charsel-window` render the scene with up to five synthetic characters; the marker position is fitted to a live capture because EncTerrain94.obj is not decoded, and static objects are not drawn. [Evidence](research/client-character-select.md).
- Scene flow (NATIVE-SHELL-001). `reconstructed/scene` ports the scene manager around SceneFlag `[0x01d1df70]`: the dispatcher `0x01859d8a` (2 title, 3 login, 4 loading, 5 character select, 6 game), the title scene `0x0185ad63` with its startup progress, the login creation `0x01851804` (world 0x5e, login music), the 3 → 5 tick tail (protocol 0x14), the frame-driver music block, start loading `0x0185a75a` (join request / hero copy, scene 4) and the one-frame loading scene `0x01851adc` with CLoadingScene (`reconstructed/ui/ui_loading.c`); `scripts/validate_scene.py` compares them with the client in Unicorn (7,000 cases and 120 loading-screen GL streams, 0 mismatches, 8 planted mistakes detected; private run). `mu-client` (SDL2 + OpenGL, headless GL/software; `mu-shell` for CI) runs the flow end to end offline over the native modules: title, server select, an OFFLINE DEMO account panel, character select, loading screen, the world with the chosen character, Esc back to character select; `native/client/offline-session.*` stands in for the out-of-scope network answers. [Evidence](research/client-scene-manager.md).
- Ambient life and weather (NATIVE-ENV-001). `reconstructed/environment` ports MoveBoids `0x00c9eb04` (birds, bats, butterflies, crows, Atlans shoals: spawn rules, movers, flock steering, despawn, sounds), MoveFishs `0x00ca05b3` (Lorencia fish on water tiles, rats, Atlans fish), MoveLeaves `0x01537a43` (Lorencia/Noria leaves, Devias snow, Atlans bubbles, Icarus rain, Tormenta Island's rain from its world class) and their render routines; `scripts/validate_environment.py` compares them with the client in Unicorn as world sessions (400 cases, 80,400 steps, 5,056,654 host calls and 3,778,740 rand() calls in order, 0 mismatches, 94/94 branch probes, 10/10 planted mistakes detected; private run). `mu-world`/`mu-walk`/mu-client draw the creatures and particles and the per-world clear colour. Static finding: worlds without `leaf01.OZJ` (Lorencia, Noria) end with no leaf bitmap, so the client simulates their leaves without drawing them; the game scene never enables fog. [Evidence](research/client-environment.md).
- Particles, sprites and blob shadows (NATIVE-PARTICLE-001). `reconstructed/particles` ports CreateParticle `0x0168fafd`/`0x015ae7b0`, MoveParticles `0x01616c80` and RenderParticles `0x0159123f` for Fire01, smoke01, rain02/03, Spark02/03 and Thunder01, RenderSprite `0x0184c39c`, CreateSprite/RenderSprites `0x01692508`/`0x0169270e`, RenderBodyShadow `0x012bc07a`, the bone lookup `0x0129f18a`, TransformPosition `0x012b6ef1` and RenderObjectVisual `0x017f9758` (Lorencia's Waterspout smoke and MerchantAnimal flares, Tormenta's slot 0x34 joints); `scripts/validate_particles.py` compares them with the client in Unicorn (12 families, 30,452 cases, 0 mismatches, 12/12 planted mistakes detected; private run). `native/core/mu_particles.*` draws the object fires and smoke, the creatures' and characters' shadows, glow sprites, rain splashes and the skills' sprites in mu-world ([finding](research/client-particles.md)).
- Joints, world-object effects, login particles (NATIVE-JOINT-001). `reconstructed/joints` ports the joint pool (CreateJoint `0x0153b02c`, MoveJoint `0x01556c26`, RenderJoints `0x01589b56`) for Tormenta Island's lightning `0x7f7d` 0x10..0x1a, the spark streaks `0x7fd5` and NATIVE-COMBAT-002's ribbons (one implementation; `skill_fx` wraps it); `skill_fx` adds the Tormenta tornado `0x40e` and `reconstructed/particles` the login mist/spray (clouds `0x7f89` 0x14, WATERFALL1 `0x801a` 2), Shiny01 and the Dungeon/Devias/Noria object visuals. Unicorn: `validate_joints.py` 9,000 cases plus the extended `validate_skill_fx.py`/`validate_particles.py`, 69,494 cases, 0 mismatches (private run). mu-world draws the crystals' lightning and the tornado; the login scene's lanterns, mist and spray leave the stand-ins; the finding surveys each world's creators ([finding](research/client-joints.md)).
- Dropped items and their labels (NATIVE-ITEMS-001). `reconstructed/items` ports the item viewport packet `0x0122c216`, CreateItem `0x016daa27` (models, special models, the 180-unit drop, sounds), ItemObjectAttribute `0x016da00b`, ItemAngle `0x01802a66` and the name builder `0x017ea422` (both lifted by `scripts/items_static.py`), MoveItems `0x017ea1aa` with the Shiny01 sparkle, RenderItems `0x017e9495` (zen pile, item render passes), TestFrustrum `0x016ccc14`, SelectItem `0x016b4fc0` and the label colours `0x00c84f00`; the labels are the hudPlayerName movie's item list (anchor, hover, Alt toggle, ItemNameMC layout: static readings). Monster hurt and death sounds (SetPlayerShock/SetPlayerDie monster branches over the extracted SetMonsterSound slots). `scripts/validate_items.py`: 11 families, 22,200 cases, 0 mismatches, 11/11 negative controls (private run). `mu-world --combat` drops demo items from kills; click/space pick-up, Alt labels, `--item-script` ([finding](research/client-ground-items.md)).
- Overhead names, monster HP boxes, chat bubbles (NATIVE-NAMES-001). The client draws them with the GFx movie `hudPlayerName`, not in its 3D/2D layer. `reconstructed/names` ports the movie's game handler: addInfo `0x00c82fd1`, the per-frame update `0x00c81d1e` (visibility, HP bars, guild/gens/server lines, positions), the head height `0x00c8526e`, the name/colour helpers, setHp, removeInfo, setTopMovie, the chat bubble `0x0169d87f` with setMessage, and SetMonsterInfo's object kind (NPCs are kind 4 and get no plate). `scripts/validate_names.py` compares them with the client in Unicorn (6,000 addInfo calls, 4,000 update frames with 11,632 operations, 5,096 classes, 4,000 bubbles and the helpers, 0 mismatches, 12/12 planted mistakes detected; private run). mu-world/mu-walk/mu-client create the hero's and the monsters' plates, send the demo HP, remove them at SetPlayerDie and show chat bubbles; with `--gfx` the real movie draws them, otherwise a stand-in (`core/mu_label`) ([finding](research/client-overhead-text.md)).
- Talking to NPCs (NATIVE-NPC-001). `reconstructed/npc` ports the talk answer's handler ReceiveTalk `0x01280659` (the window per result code: NpcShop, StorageInven, npcdialogue with its dialogue NPC, the mix, event and Ruud windows; the close-all, SND_Play 25/28, SetCursorPos, the unencrypted-answer report), the character pick `0x016b47bf` with the segment/OBB test `0x018500bf`, and the object box of every model from the character create's box section (executed). `scripts/validate_npc.py` compares them with the client in Unicorn: 4,096 talk cases (every result byte), 3,000 axis and 3,000 segment cases, 1,000 picks, 15,095 boxes, 0 mismatches, 5/5 planted mistakes caught. MoveHero's NPC branch, MoveCharacters' character bit and the talk case (no turn, no talk animation; refusals; the repair flag) are static readings. `mu-world --npc` walks the hero beside a clicked NPC and opens the client's NpcDialogue, NpcShop (item models, tooltips) and StorageInven movies from a labelled demo answer; buying, selling and the vault are local demo actions. [Evidence](research/client-npc-interaction.md).
- Fidelity pass over lights, item models and item labels (NATIVE-FIDELITY-001). The hero's light is RenderCharacter's light block `0x01367530` ((1, 1, 1) times the Hero +0x1a6 state tints); birds, bats, fish and butterflies take RenderObject's body light under ObjectInit's flags; the GFx item models follow RenderObjectScreen `0x016c2d82` (armour parts posed on the Player model at the client's per-group height, InvenItemAnimation, flat light (1, 1, 1)); ground-item labels get the set-item prefix of the set manager `0x009de132`/`0x009debe4`/`0x009e0551` (`WarriorLeather Helm +5`: no space, as the client), PentagramOption's tier and the client's suffix spacing; special item models load through the loader `0x0183220e`'s table. Unicorn: 9,398 cases, 0 mismatches over six families (hero light 855, creatures 226, RenderObjectScreen 3,000, special models 45, Lang lookups 370, set prefix 4,902), every negative control detected (private runs) ([finding](research/client-fidelity.md)).
- Native preview app (NATIVE-APP-001). `make -C native preview-app` packages `mu-client` as `Mu The Matrix Native Preview.app` (ad-hoc signed, self-contained Homebrew dylibs, optional libmugfx): a Swift launcher finds the free install (read-only) or asks once, prepares a local Native Data folder (all 179 GFx movies converted, local lang/object/sound tables copied), and starts the whole offline flow with every world feature, GFx, a screen-fitting window and an OFFLINE PREVIEW label; logs in `~/Library/Logs/MuTheMatrixNative`, an alert with the log on a crash, a settings window on Option. The `mu-nonet` guard interposes the socket API in mu-client: runs report 0 network attempts (one local AF_UNIX socket, the system's logging during OpenGL init). Tests check the bundle, signature, imports, guard, setup, plan and a headless smoke to the world; a private smoke over the installed game passes. [Note](research/native-preview-app.md).
- More Lang tables, NPC dialogue text, item prices (NATIVE-LANG-002). From the same live snapshot: BuffEffect (the bufflist's addBuff `0x00c5f278`, the buff popup lines `0x01298a54`), CharacterInfoSetup (the character window's rows: label, sort, button; the row builder `0x00b3dedc` with MSVC's std::sort), MonsterSoulConversion, SkillRequire and MUQuestString. The NPC dialogue text is QuestWords.bmd, not a Lang table: `reconstructed/npc/npc_dialogue.c` ports the dialogue manager's lookups and the window's choice `0x00be906d`, verified over the client's own loaders on the installed files. `reconstructed/price` ports ItemValue `0x0169320b` and ConvertRepairGold `0x016b8d16` (three excellent-option compares displaced out of the restored image are inferred). Unicorn: Lang families 3,875 cases, dialogue 18,444, prices 290,639, 0 mismatches, every planted mistake caught. mu-world/mu-client show the client's dialogue, prices and price lines, the bufflist with a buff popup (demo buffs) and the character rows; the finding surveys all 74 tables ([finding](research/client-lang-tables.md)).
- Quests (NATIVE-QUEST-001). `reconstructed/quest` ports the quest system singleton (MUQuest/MUQuestString read live with new langread options; categories, active sets, item and value maps), the F6 quest packets' handlers, the goal/reward texts and the game side of NpcQuestProgress, npcdialogue's quest list and MyQuestInfo's quest tabs. `scripts/validate_quest.py` runs the client's routines in Unicorn and equals libquest in every family (also the running client's own quest system from the snapshot); planted mistakes caught. mu-world/mu-client play a quest offline: a quest NPC's dialogue, the quest list, pages, accept, kills counting, complete, MyQuestInfo (T), with a labelled demo server. No quest marks over NPCs exist in this build ([finding](research/client-quests.md)).
- Skills in the interface (NATIVE-SKILL-001). The skill table loader is the Skill(Kor) row parser `0x01170ca5` (61 columns, lexical casts, the column names from the client's own consumers and labels); `reconstructed/skill` also ports the bar feed `0x00c58797`, StartSkillDelay/IsSkillReady/tick, the stat check, the mana/AG check, the class special cases, the skill icon draw and the skill tooltip builder `0x0117da56` with its wrap and popup. Unicorn: 13 families, 12,763 cases, 0 mismatches, 11/11 planted mistakes caught. mu-world/mu-client play the bar, SkillInfoPopup and the Skill Imprint window (U, drag to the bar) and cast the selected skill through the checks (demo learned list) ([finding](research/client-skills.md)).
- Maps and travel (NATIVE-MAP-001). The "minimap" is the GFx movie hudMap (Tab): its world image is `GFx/NaviMap/navimap<world+1>.ozp`, its NPC/portal markers come from the server (opcode 0xE7), so no minimap.bmd loader exists. `reconstructed/map` ports the overlay's game side (per-frame marker/offset `0x00c6af22`, the 0xE7 records, the show rule and E7 request), the Move window (move manager, MSVC std::sort orders, availability `0x00bdc0c7`, rows, click and the C1 8E 02 request) and the client's gate entrance test `0x016a4608`. Unicorn: 10 families, 5,001 cases, 0 mismatches, 10/10 planted mistakes caught. `core/mu_map` adds an offline demo server; mu-world/mu-client change worlds with the existing loader (no loading picture, as live), and show hudMap and the Move window (M) through the GFx layer. Live capture of both windows and two warps ([finding](research/client-maps.md)).
- Native frame time and window (NATIVE-PERF-001). Profiling mu-client in the login, character select, Lorencia and Tormenta Island (135,10 and 50,46) found the native port's own costs: a full-frame read-back, software 2D compositing and re-upload every frame (8 ms in the world and 19-24 ms in character select at 3456 × 2160), one Metal draw per terrain tile and mesh, and SDL_Delay's oversleep at the login cap (23.9 fps). The 2D layer now replays the reconstructed 2D calls on the GPU (`native/viewer/ui_gl.c`, mu_ui_raster's semantics), the GFx character list renders into an IOSurface, the terrain/mesh streams are batched without changing them (`native/viewer/gl_batch.c`, pixel-identical), and the cap sleeps precisely. Every windowed scene holds 25.0 fps at 1280 × 800, 1728 × 1080 and full screen with frame work p95 ≤ 16.2 ms; the window is resizable with macOS full screen and the client quits with the preview app's launcher. Reconstructed routines unchanged. [Note](research/native-performance.md).
- Item attributes and table layouts (NATIVE-DATA-002). The 708-byte Item.bmd record is named from the game code that reads it (kind/type, level, slot, skill, inventory size, damage/defense, speeds, durability, magic power, stat/level/class requirements, price, set attribute, resistances, drop/trade/store/sell/repair flags, stack size, stat options, pentagram/elemental values). `reconstructed/data` adds maximum durability `0x00ccc5b0` and the warehouse/repair bans `0x016bec14`/`0x016be1d9`. In Unicorn, the real loader, getters, predicates, ItemConvert copy, durability and bans agree on all 4,881 items and 300 synthetic records: 604,981 comparisons, 0 mismatches. A layout catalog names 27 other tables with per-field evidence classes; `mu-data` prints named JSON. No skill/minimap/movereq loader exists in the restored text. [Evidence](research/client-item-attributes.md).
- Click-to-move (NATIVE-PATH-001). `reconstructed/path` ports the path finder (PathFinding2 `0x012b0e85`, FindPath `0x012b1c45`: lazy-cost best-first search over TerrainWall, 8 neighbours, 5/7 costs, heuristic `(3(5|dx-dy|+7min+1))/4`, 500-pop budget, FIFO ties, `(wall & 0x1e) < level`, safe-zone retry at level 4, best-heuristic fallback for unreachable targets, 15-node path) and the follower (MovePath `0x012b0846` Catmull-Rom sub-targets and 45-degree turning, the 12/15-unit 40 ms step). `scripts/validate_path.py` runs the client's instructions in Unicorn: 7,945 + 3,100 comparisons on synthetic grids and all 82 installed attribute maps, 0 mismatches, 16 planted mistakes detected (private run). `native/core/mu_path.*` and `mu-path` render clicks over a top-down terrain view. SendMove `0x016b5cd0` is recorded as the network boundary only. [Evidence](research/client-path.md).
- Long-distance auto move and walk/run rules (NATIVE-PATH-002). A manifest-backed live read of the running client (read-only `memread`, game lock, server-select screen) pins the neighbour table `0x01cf1640` (same digest as capture-04). `reconstructed/path` adds BuildPath's trimming variant, the long-distance helper `0x012b104c` (budget 300,000,000, mask 0x1c, 500-node list) and the auto-move PATH_t (start, three-node segments, refresh, reset). `reconstructed/movement` adds SetPlayerWalk's run counter (base classes 3/4/6/7, boots or gloves +5, ride buffs, riding pets; 0 in safe zones; 15 instead of 12 from the 40th moving step), SetPlayerStop's reset and CharacterMoveSpeed's predicates as character-field functions. `scripts/validate_path.py`: 22,715 comparisons, 0 mismatches, 30/30 mutations (private run). `mu_walk`, the native walker, `mu-path --class/--boots/--long` and `mu-world --boots/--auto-move` use them. MoveHero's auto-move branches and S-click trigger are static. [Evidence](research/client-path.md).

## Verification

The suite discovers 380 Python tests (macOS, CLIENT-MESHDRAW-EXEC-001 worktree rebased on main through the audio merge, #75).
Portable checks pass 345 and explicitly skip 35 private-input checks, and `scripts/local-macos-ci.sh` passes. Before the frame,
actor and audio merges, all 49 `native/tests` checks passed with `MU_RECOVERY_INTEGRATION=1`, including the private viewer,
character and terrain checks and the mesh-draw execution harness.
Before that, the NATIVE-CHAR-001 worktree discovered 282 tests with 25 skips.
Before NATIVE-CHAR-001 the suite discovered 270 tests and skipped 22 private-input checks.
In the previous count, the suite discovered 236 tests and skipped eighteen private-input checks. In the frameloop worktree, the new frame-map check
passes with `MU_RECOVERY_INTEGRATION=1` and `MU_GAME_ROOT`; the full opt-in suite
was not rerun there. In the skinning worktree, opt-in integration passed all 209
earlier tests. The mugl and hotpatch source checks need no private inputs.
In the bone-tracks worktree it passed all 155 tests from before the seven launcher-guard tests.
The rotation worktree's opt-in integration passed 142 of the earlier 147.

The v14 reader matches its pinned independent oracle on 216 installed files and
91 synthetic vectors. A complete model rescan preserves every one of 12,754
statuses and all 12,663 previously pinned parsed-input hashes. The exact-client
v12 comparison runs actual captured leaf instructions without helper stubs.
Its deliberately wrong feedback order fails 312 overlap cases.

Detailed identities, counts and CI references are in `evidence-index.json`.
Original-file scan manifests and binary evidence remain ignored local inputs;
CI runs authored fixtures and reports the private skips explicitly.

## Runtime boundary

The original client runs on the Mac through Wine; that work (the Mac app, the player disk image, the free
Wine runtime, the mugl OpenGL proxy, fast x87 and the launcher fixes) moved to its own repository,
[mu-the-matrix-mac](https://github.com/fryezero/mu-the-matrix-mac), on 2026-10-21. Its status is in that repository's `docs/status.md`.

For code recovery, no Windows PC is currently available. The separate Mac-only Linux guest
([`runtime-linux/`](../runtime-linux/README.md)) still has outbound networking blocked and reaches an
unresolved localhost connection. Native Windows capture/equivalence remains unverified, although the optional
Windows helper builds and its own memory/hash smoke checks pass under Wine. The native reconstruction reads
selected live client state with the read-only tools in [`live-readers/`](../live-readers/README.md), from a
client running in Wine under the shared game lock.

## Repository and next work

The public [repository](https://github.com/fryezero/mu-the-matrix-native)
contains reviewed authored source, synthetic fixtures and evidence summaries.
PRs #4, #6, #8, #10, #13, #14, #16, #18, #20, #23, #25, #26, #28, #30, #32, #34 and #36 are merged after macOS/Linux checks.
No game executable, asset pack or memory capture was uploaded.

The client-linked v12 milestone is merged through PR #23. Two selected v15
dispatch slots now resolve into restored client code. See
[the capture finding](research/model-dispatch.md). Next trace the original v14 helper or bounded model record-loading/matrix code.
Original types, hierarchy semantics, initialization dependencies, simulation,
networking, renderer/input/audio equivalence and a complete client build remain
unfinished. Read `handoff.md` for exact local artifact paths and entry addresses.

The fixed v15 dispatch scope is merged through PR #26 after macOS/Linux CI.
Hierarchy findings are merged through PR #25. Post-merge review corrections
are merged through PR #28 after both platform checks. Strict model acceptance is unchanged.

The v15 key context is merged through PR #30. The ECB source and guest comparator
are merged through PR #32 after macOS/Linux CI. The guest is shut down. Decoder equivalence does not
resolve the model loader's allocation, hierarchy or actual rendering behavior.

Pose arithmetic is merged through PR #34 after macOS/Linux CI. Next validate original rotation/model
record loading, keeping actual FP state and unknown prior output contents open.

Issue #35 adds a fixed four-byte rotation dispatch capture. Two reads match
value 1; early packed code is refused without a payload and every prior scope
repeats. [Finding](research/client-trig-state.md). Actual FP state and full
rotation/trigonometric equivalence remain open. Guest is shut down.

Issue #37 adds rotation source and an actual-instruction comparison with
8,012 matches, 2,816 alias/alignment and 256 FP-state variants. A wrong axis
order fails 7,547. [Finding](research/client-rotation.md). Client SSE2 trig
algorithms are not reconstructed. Out-of-domain angles, non-finite values and live
caller FP state remain open. No guest run was needed.

Issue #40 adds the bone-track loop source and an actual-instruction comparison.
All 342 synthetic comparisons and every installed v12/v14/v15 model the readers
accept match, including dummy records, zero-count allocations and overlapping
layouts. Skipping zero-size allocations fails 57 comparisons.
[Finding](research/client-bone-tracks.md). Client allocation failure, the real
heap/memcpy feature state, rejected v15 files and pose-builder interpolation
remain open. No guest run was needed.

Issue #46 adds the pose-builder source and an actual-instruction comparison
seeded by the actual bone-track loop. All 483 synthetic, 1,822 helper and 47,833
installed calls match; lerp differs in 364 and a modulo frame wrap in 60.
[Finding](research/client-pose-builder.md). The caller's frame/action choice,
prior output and root contents, live FP state and renderer use remain open.
No guest or CrossOver run was needed.

Issue #53 adds the model transform and animation tick sources, a static map of
the pose-builder callers and the mesh draw's GL order. The transform matches on
every installed model the readers accept, chained through the actual loop and
builder, and the tick matches on 35,871 installed calls. Transposed rotation,
translated normals, per-tick prior updates and an ignored lock limit all fail.
[Finding](research/client-skinning.md). The draw routine was not executed, and
live object state, action changes and the frame loop remain open. No guest or
CrossOver run was needed.

Issue #55 (CLIENT-FRAME-001) maps the message loop, scene dispatcher and frame driver,
including the 40 ms Sleep cap and the fixed 40 ms logic step. It also labels all
24 fan and 27 quad glBegin sites with their return addresses and recovers the
effect system's stream-VBO pattern. Everything is static and checked by
`scripts/client_frame_static.py`. [Finding](research/client-frame-loop.md). Runtime
per-routine counts, `IGC.dll` hook behaviour and whether animation runs per frame
remain open. No guest or CrossOver run was needed, and nothing was patched.

NATIVE-VIEW-001 (branch `claude/native-viewer`) adds the native model viewer `native/`. It is a viewer for verified model code, built with SDL2 and OpenGL 2.1, a CGL headless path and a deterministic software rasterizer. Golden data equals the reconstructed functions on synthetic models in CI and on all 12,627 posable installed models in a private run. The mesh-draw call stream equals an independent rule model. [Finding](research/native-viewer.md). The mesh draw itself was never executed, so its state and mode readings stay static. No game, bottle or registry was touched.

NATIVE-NET-001 (branch `claude/native-net`) adds the client's network protocol layer under `native/core/mu_protocol.*` with the `mu-proto` CLI, portable tests and a Unicorn validator. It reconstructs the C1/C2/C3/C4 framing, the chained send XOR, the packet builder and the receive dechunker from the restored `main.exe`, verified bit-exact against the client's own `AddData`/`XorData`/`nRecv` instructions (`scripts/validate_protocol.py`). The C3/C4 CryptoModule cipher (primitives identified by emulation) and the receive dispatcher plus login/server-list packet bodies are mapped statically and left as the documented next step. The `ws2_32` calls are platform boundaries; protection modules were not analysed. Offline only. [Finding](research/client-net-protocol.md).

CLIENT-MESHDRAW-EXEC-001 (branch `claude/native-unicorn`) executes the client's mesh draw `0x012b8d1d`, body `0x012bb35a`, GL state wrappers and texture-name parser under Unicorn. It compares them with the native port: every GL call, final cache and written table are equal in 207 synthetic viewer, 500 mutated and 2,713 installed cases. CI pins the client-verified stream digests. [Finding](research/client-meshdraw-exec.md). No game, bottle or registry was touched.

NATIVE-UI-001 (branch `claude/native-ui`) reconstructs the client's 2D interface layer in `reconstructed/ui` and validates it against the client's own instructions in Unicorn (`scripts/validate_ui.py`): state wrappers, the 2D projection, bitmap/colour/sprite quads, the title scene, the GDI text path, OpenTga/OpenJpeg (all 487 installed OZT, 246 OZJ; libjpeg-turbo equals the client's IJG 6b on intact files) and the login overlay. `mu-render ui` renders the title/loading screen and the login overlay natively; a window-only live capture matched the title within 0.6/255 per channel. [Finding](research/client-ui-2d.md). The UI-manager windows (server list, buttons) and the 3D login world are not covered.

NATIVE-UI-002 (branch `claude/native-ui2`) reconstructs the legacy window layer in `reconstructed/ui` (CSprite frames, CButton hover/press/click, CWin drag and hit tests, CWinEx, CutText), the server-select window `CServerSelWin` and the credits window `CCreditWin`, and validates them in Unicorn (`scripts/validate_ui_widgets.py`: platform calls and full object state equal in 400 CutText, 120 sprite, 60 CWinEx, 120 server-window and 40 credits cases). `mu-render ui servers|credits` renders both screens natively over synthetic data; against window-only live captures every opaque pixel of the buttons (normal, checked, hovered), notice box and arrow is identical. [Finding](research/client-ui-widgets.md). MENU/CREDIT are a GFx movie; the 3D login world, the GFx layer and the character-select windows are not covered.

NATIVE-HUD-001 (branch `claude/native-hud`) maps the in-game interface: the bottom bar with the HP/MP orbs and skill bar, the inventory, the character info window, the chat and the item tooltip are all GFx (Scaleform) movies (registry `0x00ac4a79`, 139 windows); the legacy NewUI layer is created but does not draw them, and the classic inventory control is dead code. The game side around the movies is reconstructed in `reconstructed/hud` and compared with the client in Unicorn (`scripts/validate_hud.py`): the item grid (200 cases, 22,166 steps), the slot pass (300), the per-window orthographic item pass (600 cases, 38,640 calls), RenderItem3D's general path (3,000), the InfoPopup HTML assembly (400 tooltips) and 14 tooltip-formatter types (3,000 with the installed formats), all equal; six negative controls are caught. `mu-render ui inventory|tooltip` renders an inventory with 3D items and table-driven tooltips natively. [Finding](research/client-hud.md). GFx frames, the full tooltip builder, RenderObjectScreen and the item render-info loader (scale) are open.

NATIVE-GFX-001 (branch `claude/native-gfx`) inventories the GFx movies and prototypes the native route for them. The 179 `.ozg` movies are the ModulusCrypt envelope around GFx 3.x movies (`CFX`/`GFX`, SWF 8–10, all AS2, CLIK, 1,584 external DDS images in `.ozd`, 159 atlases, 7,750 sub-images, fonts from `gfxfontlib.swf`/`fontconfig.txt`). `native/gfx/gfxconvert.py` turns them into standard SWF files. The pinned external Ruffle (MIT/Apache, fetched by script, not vendored) loads and runs all 179; the bottom bar, the inventory and the reconstructed tooltip HTML render close to the live captures. `native/gfx/mugfx` (C ABI) bridges ExternalInterface and GFx-style Invoke. `mu-gfx-window` (SDL2/OpenGL) drives `setHPMP` with demo values and the inventory's callbacks into the reconstructed grid and slot pass. Both movies cost 6 ms/frame at 1280×800 with full readback on the M5. Gaps: GFx AS2 extensions, 6 compacted fonts, zero-copy textures. [Finding](research/native-gfx.md).

NATIVE-GFX-002 (branch `claude/native-gfx2`) makes the GFx movies the native client's interface. The GFx ActionScript extensions the movies use (right/middle button `*Aux` handlers, `hitTestDisable`, `topmostLevel`, `noAdvance`, the CLIK focus/`Selection`/`Mouse`/`System.capabilities.numControllers` extensions, `appendHtml`, `textAutoSize`, `verticalAlign`) are a five-patch series on the pinned Ruffle (`native/gfx/ruffle-patches`, applied by script, nothing vendored); `loadBitmapFromLib` is the one gap. mugfx ABI 2 adds keyboard/text input, the GFx hit test, cursors, macOS device fonts, window-sized players, Retina scale and IOSurface sharing with the GL compositor (bar + inventory + chat 2.98 ms/frame against 5.85 ms for the full-window read-back). The six packed fonts convert to the same-named "Slate Mobile" DefineFont3. `native/gfx/mu_gfx_layer.c` plays the bar (hotkeys, skill and item bars), the inventory over the reconstructed grid (pick/drop, right click, tooltips from the NATIVE-HUD-001 pipeline), the character window and chat with local echo, and `mu-world --gfx DIR` shows it over the 3D world. 14 tests (layer against a stand-in libmugfx in CI; every patched extension under Ruffle locally). [Finding](research/native-gfx2.md).

NATIVE-GFX-003 (branch `claude/native-gfx3`) runs the HUD as the client runs it: one base movie. `base.swf` loads `ExternalBase.swf`, and its UI loader loads ImageData, Tooltip, Popups, main, ItemDurability, Chat, AlarmFrame, topmenu, bufflist, hudPlayerName, hudMap and hudNotice. The layer answers its channels as the client's handlers do. Two patches join the Ruffle series: GFx's movie load order and host-supplied images. mugfx ABI 3 adds `loadClip` from the movie directory, game images, IME and double-buffered IOSurfaces. Results:

- The skill slots show the client's skill sheets; the skill table comes from the installed skill.bmd, which is an inference, because the build's table is in the encrypted Lang.mpr.
- The item hotkeys show item models that the host renders into the game image `image0`.
- `loadBitmapFromLib` works (PartyFrame buffs).
- mu-world and mu-client draw the item models over the inventory: RenderItem3D placement and glow levels.
- The window placement (registry alignment, SetScale below 700 px) and InitMenuInfo (menu ids, GlobalText placeholders) take the client's form.
- The chat's leftover rows are gone, IME composition shows in the chat input, and `mu-client --gfx` shows the interface in the world scene.

`scripts/validate_gfx3.py` runs the client's LoadFrameFiles, InitMenuInfo, SkillInfo and window-creator routines in Unicorn: all equal the layer (80 window cases), and 5 planted mistakes are caught. The comparison corrected the menu's submenu groups and showed that id 14 opens the inventory. 12 tests (base movie on the stand-in library in CI; the Ruffle checks locally). [Finding](research/native-gfx3.md).

NATIVE-LANG-001 (branch `claude/native-lang`) gets the game text and script tables of the encrypted `Data\Lang.mpr` without its password. The client's own code loads the package; `live-readers/langread` then copies the tables main.exe built (the script-table manager `0x06fbaa60` and its std::map trees) out of a client this project started. The copy is read-only and was made under the game lock at the server list; three runs of about 64 s, no login. `scripts/live_lang_to_plain.py` writes local plaintext; it is never committed. The tables were located only through main.exe's consumers (GlobalText `0x0095f027`, the skill lookup `0x00961620`, the startup table list `0x0115eceb`); the loader and the protection stay opaque. `native/core/mu_lang` uses them when `MU_LANG_DIR` is set:

- the GFx labels, the client's skill table and the map names in mu-world and mu-client;
- skill distance and GetSkillInformation in combat;
- EnchantEffect colours in the world render;
- character-select tips and login strings.

Placeholders remain without the tables. `scripts/validate_lang.py` runs the client's consumers over the snapshot in Unicorn: 43,400 cases equal the native module, and 5 planted mistakes are caught. [Finding](research/client-lang-tables.md).

NATIVE-PLAYERS-001 (branch `claude/native-players`) puts other players into the native world. The client side of the player viewport is reconstructed in `reconstructed/players`: the packet class byte, ChangeCharacterExt `0x0137b68c` (the 18 equipment bytes → part, weapon, wing and helper slots with levels, excellent and ancient bits, the ride state and the engine calls), the move packet `0x3d` and MoveCharacters' remote step `0x013b852a` (path, walk, stop, position), all equal to the client's instructions under Unicorn (`scripts/validate_players.py`: 1,000 cases per family, 0 mismatches, 7/7 planted mistakes detected); the viewport record, CreateCharacter's defaults, the destroy / DeleteCharacter path and the personal-store `setStore` are static readings. `native/core/mu_world_players` runs it in mu-world/mu-client from a labelled demo players file (`--players`): the demo server's packets and viewport range, class and Item.bmd parts drawn with the render passes, routes replayed through the client path finder and MovePath, deaths with SetPlayerDie and the fade, plates with PK colours, guild lines, party HP bars and store boxes through hudPlayerName. [Finding](research/client-remote-players.md).

NATIVE-HELPERS-001 (branch `claude/native-helpers`) gives characters their helpers. `reconstructed/helpers` holds the Guardian Angel's bug (CreateBug, MoveBug, RenderBug, DeleteBug) and the mount manager's side (kind, factory and 21 classes with their models, play speeds and rider bones, the moves with dust and flying steps, the action map, the rider actions 0x26 / 0x47 / 0x67 and the lift, the render with the shadow), equal to the client's instructions under Unicorn (`scripts/validate_helpers.py`: 8,639 cases, 0 mismatches, 5 negative controls and 6 planted mistakes detected); the manager's set/init, the Imp's link block and the 0x25 equipment packet are static readings. `native/core/mu_world_helpers` draws them in mu-world/mu-client for the hero (`--helper`, DEMO) and the demo players (`pet=`, `ride=`). [Finding](research/client-helpers.md).
