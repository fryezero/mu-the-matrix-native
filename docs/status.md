# Current status

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
- Walking around the world (NATIVE-WORLD-001). `reconstructed/movement` ports MovePath (path spline, turn), MoveCharacterPosition, CharacterMoveSpeed (Player: 12 units per 40 ms step, 15 once the run counter reaches 40), RequestTerrainHeight, SetAction, the client path finder (PathFinding2/FindPath) and the unarmed walk/stand selection; `scripts/validate_movement.py` compares them with the client's instructions in Unicorn (0 mismatches, planted mistakes detected; private run). Worlds' camera records (`Camera_Angle_Position.bmd`, Lorencia FOV 39) are decoded. `mu-world`/`mu-walk` walk the hero across real terrain with the client camera, pick and zoom. The near plane (20) and the path finder's direction table come from the runtime capture of the packed data section. [Evidence](research/native-world.md).
- Item attributes and table layouts (NATIVE-DATA-002). The 708-byte Item.bmd record is named from the game code that reads it (kind/type, level, slot, skill, inventory size, damage/defense, speeds, durability, magic power, stat/level/class requirements, price, set attribute, resistances, drop/trade/store/sell/repair flags, stack size, stat options, pentagram/elemental values). `reconstructed/data` adds maximum durability `0x00ccc5b0` and the warehouse/repair bans `0x016bec14`/`0x016be1d9`. In Unicorn, the real loader, getters, predicates, ItemConvert copy, durability and bans agree on all 4,881 items and 300 synthetic records: 604,981 comparisons, 0 mismatches. A layout catalog names 27 other tables with per-field evidence classes; `mu-data` prints named JSON. No skill/minimap/movereq loader exists in the restored text. [Evidence](research/client-item-attributes.md).
- Click-to-move (NATIVE-PATH-001). `reconstructed/path` ports the path finder (PathFinding2 `0x012b0e85`, FindPath `0x012b1c45`: lazy-cost best-first search over TerrainWall, 8 neighbours, 5/7 costs, heuristic `(3(5|dx-dy|+7min+1))/4`, 500-pop budget, FIFO ties, `(wall & 0x1e) < level`, safe-zone retry at level 4, best-heuristic fallback for unreachable targets, 15-node path) and the follower (MovePath `0x012b0846` Catmull-Rom sub-targets and 45-degree turning, the 12/15-unit 40 ms step). `scripts/validate_path.py` runs the client's instructions in Unicorn: 7,945 + 3,100 comparisons on synthetic grids and all 82 installed attribute maps, 0 mismatches, 14 planted mistakes detected (private run). `native/core/mu_path.*` and `mu-path` render clicks over a top-down terrain view. SendMove `0x016b5cd0` is recorded as the network boundary only. [Evidence](research/client-path.md).

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

The original client works on Windows. Earlier isolated CrossOver `win10_64`
starts fail with a Rosetta selector error. A new `win10`/win32 compatibility path
uses .NET 4.8, builtin WIC/GDI+, WPF software rendering and the default IGCN skin
in a cloned installation. The authored setup and local validation are recorded
in [the CrossOver finding](research/mac-crossover-32bit.md), issue #39.
The fresh test bottle passed all eight synthetic image-pipeline steps, kept
the launcher alive for 65.8 seconds, and was deleted after validation.
The owner now reports GAME START, login and gameplay in MuMatrix32. This is
original-client compatibility gameplay, not a recovered native build. Issue #42
adds an idle-bottle startup reset and monitor validation. An injected stale
source-to-monitor link reproduces the exact Settings exception; the guarded
reset rebuilds the link and Settings opens again in MuSettings-test. Both fresh
win32 and win10_64 bottles have valid monitor registrations. Natural sleep/display
change recovery during an active game remains unverified. MuMatrix32 is reserved
for Claude's frame-rate work and was not modified by this task. No Windows PC is currently available. The separate Mac-only Linux
guest still has outbound networking blocked and reaches an unresolved localhost
connection. Native Windows capture/equivalence
remains unverified, although the optional Windows helper builds and its own
memory/hash smoke checks pass under Wine.

MAC-PERF-001, issue #45 / PR #47, adds an opt-in pinned Rosetta Timewalker
cache build, matching-checksum x87 self-check, authored PE32 transform/GL probes
and launcher selection with plain CrossOver fallback. MAC-PERF-002, issue #48,
adds an authored MIT wrapper that defaults fast translation to arguments
containing `main.exe`. MuTheMatrix.exe and .NET dependencies use the real loader;
the unfiltered fast runtime hangs on .NET. The installer builds/signs and
fingerprints our wrapper in the cache without editing pinned upstream source.
Caller substring overrides and an empty apply-to-all override are supported.
The idle-process guard, prefix-scoped reset and plain monitor check remain.
The real launcher produced its normal window in setup-owned MuX87Filter-test
under required-fast selection with the default filter. The matching-filter
benchmark measured 279.1 Mverts/s fast versus 2.7 plain with matching checksum
3.904312. The test bottle was removed. All 163 portable tests pass, with fourteen
private-input skips; both review axes and the publication audit pass.

MAC-PERF-003, issue #51, adds the authored MIT mugl OpenGL batching proxy,
361-name export generation, host-tested primitive conversion and a default-on
setup step with `MU_GL_BATCHING=0` opt-out. Deployment checks Wine's system32
builtin marker and records the proxy SHA-256. The setup-created MuMugl-test
bottle passed three plain/proxy framebuffer comparisons at 20,000 quads/frame:
38.7 to 118.7 FPS for one quad/block, 65.2 to 118.9 for four, and 76.8 to 119.6
for sixteen. All thirty-six GL regression hashes match, with zero state failures or
GL errors. Setup off/on/rerun checks pass. The launcher started main.exe with
active batching and a 25.0 FPS log; one interval reduced 999,569 blocks to 8,966
draws. The test bottle was removed. Owner in-world testing remains open.
The x87 hypothesis is superseded by Claude's reported in-world EIP profile,
which places 73% of main-thread samples in OpenGL; fast x87 did not improve
in-world FPS. These figures are compatibility evidence, not native recovery.

See [measurements and limits](research/mac-performance.md) for local checks and
Claude's separately supplied launcher-to-main/profile observations. Post-patch
in-world FPS remains owner testing. MuMatrix32 was not touched. This improves
original-client compatibility; native source recovery acceptance gates are
unchanged.

MAC-PERF-004, issue #57, publishes Claude's opt-in v7.0 CPU hotpatch source
stacked on open PR #52. Local pinned-input generation reproduces nine helper
patches, 18,583 inline sites and 50,977 peepholes. Original byte tables and the
xform prologue stay private; CI uses empty tables with game hooks disabled.
Claude reports 20.5 FPS at mask 0, 24.1 at mask 7 and 24.7 at mask 15 in the
same approximate hunting area, and zero skinning comparison mismatches over
more than one million in-game calls. These are prior single-host reports,
not rerun measurements; the 44.8% mesh-draw attribution it cites was later
corrected (below). Default setup still uses #52. No running game, bottle or registry
was changed. [Evidence and limits](research/mac-performance.md#mac-perf-004-claude-v70-in-process-cpu-hotpatches).

MAC-PERF-005, issue #59, publishes Claude's opt-in v7.1 source: a native
replacement of the per-corner loop of mesh draw routine `0x012b8d1d`, a native
light-table precompute, a frame-pacing fix, direct batch append and zero-copy or
strided batch arrays, plus the `glstride` framebuffer-hash test. The three small
original patch-site byte sequences stay private (SHA-256 in `targets.json`,
generated into an ignored header); CI builds with zero tables and no game hooks.
Local checks: private regeneration matches the pinned digests and a private rebuild
has an instruction stream identical to Claude's DLL; neither was run. Claude reports
zero mismatches over about 9.5M call-stream, 8.2M direct-append and 2.5M light-table
verification meshes, equal framebuffer hashes at five masks, and, in the default
7599 mask, 24.1 fps at the hunting spot (22.6 at mask 15) with 33.8 ms of work. These
are supplied single-host reports, not rerun. The correction: the v7.0 finding that
the routine took 44.8% of main-thread self time came from a profile of a build
without frame pointers and charged mugl's own code to the caller; the routine's true
self time is about 3%. 25 fps remains the fixed 40 ms logic-step cap, with no single
dominant hotspot left. Default setup still uses #52. No running game or bottle was
changed. [Evidence and limits](research/mac-performance.md#mac-perf-005-claude-v71-mesh-draw-loop-frame-pacing-and-zero-copy-batches).

MAC-PERF-006, issue #61, publishes Claude's v7.2 `mugl.c`: the frame-pacing bit now
waits on a waitable timer instead of Wine's `Sleep`. Claude's diagnostic builds traced
the 17-22 fps seen with pacing on (28 ms of work) to macOS stretching Wine `Sleep`
calls (7-14 ms took 17-45 ms) whenever the game is not the frontmost Mac app, not to
the client's inactive throttle or a double sleep. Claude reports 25.00 fps in the
background over 140 s with 99.6% of frames at 38-42 ms, versus about 24.5 fps with half
the frames late for v7.1, and 24.95 fps frontmost; the logic still runs at 25 Hz. No new
patch site or original byte is added. A later 6-minute background soak at a hunting spot (MU Helper on) kept a 25.00 fps median with no growth in memory and no deaths or disconnects; one 2-second interval dipped to 6.3 fps and recovered, and an hour-long session is still open. These are supplied single-host reports, not rerun;
the new code was only compiled here. Default setup still uses #52. No running game or
bottle was changed. [Evidence and limits](research/mac-performance.md#mac-perf-006-claude-v72-precise-frame-pacing-waits).

MAC-KIT-001, issue #63, publishes the owner's reproducible Mac setup kit as
`mac-play/installer/`: an idempotent setup, a read-only verify, a launcher script and a
synthetic test suite that reproduce the hand-built MuMatrix32 layout in a new win32
bottle. The owner reports that the local copy built a fresh bottle in 3 min 44 s with
.NET 4.8 and ran in world at parity or better than MuMatrix32, after six live-found bugs
were fixed. This publication replaced machine-specific siblings with repository sources and
parameters, ships no DLL (pinned SHA-256 only; prebuilt v7.x DLLs are user supplied), keeps
account and Keychain names out of the tree, and runs its 180-check suite on macOS and Linux
in CI. A follow-up live run of the repository version in a throwaway bottle (`claude/kit-live-fixes`)
covered the public build, the private hotpatch build, a prebuilt `--dll-dir` and `--fast-x87` up to the
server-select screen (25.0 fps with the hotpatch builds, 19-20 fps with the public proxy; not logged in
because the account was in use elsewhere), found five bugs (non-reproducible PE timestamps, a
`--dll-dir` that demanded `mscoree.dll`, a test that depended on the checkout, a log shared by all
bottles, and verify ignoring the launcher's fast-x87 setting) and fixed them; the suite is now 190 checks.
It sits beside the older `setup-crossover-32bit.sh`. The throwaway bottle was the only bottle created;
MuMatrix32 was not touched.
[Evidence and limits](research/mac-crossover-32bit.md#reproducible-setup-kit-mac-kit-001).

## Repository and next work

The private [repository](https://github.com/fryezero/mu-the-matrix-recovery)
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
