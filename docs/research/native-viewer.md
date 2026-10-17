# Native model viewer (NATIVE-VIEW-001)

This is the first native macOS rendering milestone. It builds an arm64 viewer, without Wine or Rosetta, that:

- loads a client BMD model of any supported version and its textures;
- animates the model with the reconstructed animation tick `0x012b4dd3` and pose builder `0x012b5064`, after the reconstructed bone-track loop `0x012b4225`;
- skins it with the reconstructed CPU transform `0x012b5bde`;
- draws it with a port of the mesh draw `0x012b8d1d` and body `0x012bb35a` whose GL call stream equals the client's own routine executed under Unicorn ([client-meshdraw-exec.md](client-meshdraw-exec.md)).

This is a viewer. It is not a game client, and it does not change any acceptance gate in `roadmap.md`. The source is in [`native/`](../../native/README.md).

## Technology choice

The viewer uses OpenGL 2.1 (legacy compatibility context) through SDL2.

- **Same API as the client.** The client is fixed-function GL 1.x. Its mesh draw issues `glBegin(GL_TRIANGLES)`, then `glTexCoord2f`, `glColor3fv` or `glColor4f` and `glVertex3fv` per corner, then `glEnd` ([client-skinning.md](client-skinning.md#4-mesh-draw-gl-sequence-static)). On macOS, a 2.1 legacy context still runs that call sequence unchanged on Apple Silicon (observed renderer: "Apple M5, 2.1 Metal - 91.7"). The GL backend therefore issues literally the client's calls.
- **A route to the full client.** Porting the rest of the client (terrain fans, 2D UI quads, effect stream VBOs, the state wrappers) can reuse the same backend.
- **The renderer is replaceable.** All drawing goes through the `mu_render_backend` interface (prepare/begin/end plus a GL-shaped sink). A later Metal backend, or an immediate-mode batcher like mugl, can replace OpenGL without touching the model or mesh-draw code.
- **SDL2 covers future needs.** It supplies the window, the GL context, input and, later, audio and gamepads for the full client. It also builds on Linux. On macOS, Homebrew's sdl2 is sdl2-compat over SDL3.
- **Headless renders use two paths.** A CGL offscreen context with a framebuffer object needs no window. A separate deterministic software rasterizer gives hashes that are stable across hosts.

## What reuses which verified code

| Stage | Code used | Reimplemented here |
|---|---|---|
| v12 decode | `reconstructed/model-codec/model_codec.c` `mu_bmd12_decode` | no |
| v15 decode | `client_lea.c` `mu_client_lea_setup` + `mu_client_lea_decode`, published format key | no |
| v14 decode | `model-recovery/modulus.cpp` `mu_modulus_decrypt` (Crypto++) | no |
| Layout checks | C port of every `model-recovery/bmd10.py` check | yes; tested for equal acceptance |
| Bone tracks | `bone_tracks.c` `mu_bone_tracks_read` | no |
| Tick, pose, skin | `skinning.c` `mu_animation_tick`, `pose_builder.c` `mu_pose_build`, `skinning.c` `mu_model_transform`, `record_math.c` | no |
| Mesh draw, body, state wrappers, normal-texcoord table | `native/core/mu_meshdraw.c`, ported from the instructions and compared with the executed routine (CLIENT-MESHDRAW-EXEC-001) | ported: literal GL call stream, explicit host pointers |
| Images | wrapper rules of `asset-recovery/recover_images.py` | C decoders (TGA, BMP, libjpeg) |

`native/core/mu_model.c` lays the checked model out as client memory and owns these choices:

- the window base `0x10000000`, record order and a bump allocator;
- vertex, normal, texcoord and triangle arrays copied from the file;
- triangle records taken as the first 0x24 bytes of each 64-byte polygon;
- action lock flags copied from the file.

It uses the client's default output buffers (bones `0x06fce398`, vertices `0x078978a0`, normals `0x0812cce0`, light `0x06fd0918`, secondary light `0x075a9ee8`) and their strides. It refuses models above the capacities those addresses imply: 200 bones, 50 meshes and 15,000 entries per mesh. No installed model exceeds them; the largest have 200 bones, 30 meshes and 4,629 entries. Models without actions, and actions with zero keys, get identity bone matrices. That is a viewer choice; the client would read unrelated memory.

## Verification

### Evidence levels

The figures below are of two kinds. Keep them apart when citing this milestone.

- **CI-verified on every push** (synthetic data only, `make test` on `macos-latest` arm64 and `ubuntu-latest` x86_64):
  - the loader agreement and malformed-input checks;
  - the 50 golden cases (42 synthetic + 8 v14 oracle vectors);
  - 207 viewer and 40 mutated mesh-draw streams against digests of the client's own streams (pinned from the Unicorn validator, which recomputes them);
  - texture decoding against Pillow;
  - the five pinned software-render hashes, on macOS arm64 and Linux x86_64.

  Headless GL agreement on the synthetic model is CI-verified on macOS only. Linux has no SDL2 in CI, so that test is skipped there explicitly.
- **Reported, not reproducible from a clone.** These were single runs on the author's Mac against the private installed client, or in local containers whose harness lives outside the repository:
  - the full-corpus golden run (12,627 models);
  - the 2,402-texture comparison;
  - the GL/software pixel counts on installed models;
  - the culling-convention counts;
  - the windowed frame rate;
  - the corpus-scan totals;
  - the Ubuntu arm64 hash run.

  The private tests in `PrivateInstalledTests` re-check samples of these when run with `MU_RECOVERY_INTEGRATION=1`. The post-merge review (PR #66 comment) did not re-run them.

### Golden data

`native/tests/reference.py` builds the reference state independently, with the existing validators' case builders. It uses `build_case`, `make_setup` with the prior output span zeroed, `tick_setup`, `installed_meshes` and `transform_setup`, all at other addresses and with other allocators. It runs that state twice:

- through the authored libraries (`libskinning`);
- through the validators' pure-Python models (`python_tick`, `python_model`, `python_transform`).

The two must agree with each other. `mu-render dump` must then equal them byte for byte: the post-tick frame, prior frame, prior action and loop result, every bone matrix, and every mesh's vertices, normals, primary light and secondary light.

Portable, synthetic (CI):

- Two seeded models, each in v10, v12 and v15 envelopes, under 7 states (3 versions x 7 states x 2 models = 42 cases). The states cover:
  - action blends, ticks with prior updates, wrap, a stop-flag clamp, a negative speed and scene 5;
  - the special head bone and body angles, scale and origin, and the pose translate flag;
  - bone and vertex scale, world 30, bounds mode 2 and the light override;
  - lighting off and translate off.

  The models include a dummy bone, a forward parent (it composes from the zeroed prior slot), a lock-flag action and a four-corner polygon.
- 8 v14 models from the independent-oracle vectors.
- A negative control: a different frame changes the vertices.

Private, installed (`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`):

- (Reported.) The full corpus was run once with `MU_NATIVE_GOLDEN_PER_VERSION=100000 MU_NATIVE_GOLDEN_MAX_VERTICES=100000`. It took 466 s on this Mac. Each model is set to its longest action at mid-frame, blended from action 0, after 3 ticks at speed 0.37.

  | Version | Models | Vertices | Result |
  |---|---:|---:|---|
  | v10 | 698 | 96,078 | byte-identical |
  | v12 | 176 | 24,304 | byte-identical |
  | v14 | 216 | 54,094 | byte-identical |
  | v15 | 11,537 | 3,734,720 | byte-identical |

  The excluded models have no meshes, no actions, or an action with zero keys; the viewer gives those identity bones. The 17 reader-rejected v15 files are also excluded.
- The default private test samples 12 models per version with at most 3,000 vertices each.

### Mesh-draw equivalence

Superseded by CLIENT-MESHDRAW-EXEC-001 ([client-meshdraw-exec.md](client-meshdraw-exec.md)). The port is compared with the client's mesh draw and body executed under Unicorn: every GL call, the final caches and model colour, and the tables each draw wrote. Synthetic viewer, mutated and installed cases all match, and every branch probe is reached. CI pins the client-verified stream digests (`MeshDrawTests`). The private test re-runs the validator and checks that the pins equal the client's streams. The earlier independent rule model (`meshdraw_reference.py`) encoded the old static reading and has been removed.

What changed against the static reading:

* The draw mode is derived from the flags. The `--mode` and `--uv-mesh` options are gone; `--select`, `--color-scale`, `--skip-mesh`, `--texture`, `--client-time` (the time global, milliseconds) and `--env-vector` set the routine's other inputs.
* The normal-texcoord table is the routine's own writer, not 0.5 + 0.5·normal.
* Mode 0x8000 and flag 0x400 are ported. In the viewer, 0x8000 stops where the client faults: model bitmaps keep no pixels.
* The mesh `+0x1c` records come from the texture names.

### Textures

- Portable: OZT (both prefix variants), OZB, TGA (raw and RLE, both origins, 24 and 32 bit) and BMP decode identically to Pillow. A synthetic JPEG decodes within 8 levels. Bad wrappers are rejected. A TGA whose image-ID length runs past the end of the file is rejected; before the post-merge review fix, the uncompressed path read past the buffer (found with AddressSanitizer).
- Private (reported): 2,402 installed Monster/Player/NPC textures (1,989 JPEG, 413 TGA) are pixel-identical to `recover_images.decode`. The private test checks the first 400 Monster files.

### Renders

- `mu-render render` uses the software rasterizer. Five settings on a synthetic textured model have pinned SHA-256 hashes of the raw RGBA pixels: default (client GL_NEAREST), forced linear filtering with a pose, alpha blend with cull (`0x40002`), additive environment (`0x1040`), and alpha test unlit. CI checks the same hashes on macOS arm64 and Ubuntu x86_64. They were re-pinned for CLIENT-MESHDRAW-EXEC-001: the fixture TGAs now follow the client's TGA rule (32-bit, uncompressed, one with the ignored origin bit, one padded to a power of two). The earlier pins were also reported on Ubuntu 24.04 arm64 and x86_64 containers; the new ones were not. The PNG round trip and repeat determinism are checked, and the three envelopes render identically.
- `mu-viewer --headless --backend gl --compare` renders through CGL and an FBO and compares with the software path.
  - Synthetic, test bound: under 1% of pixels may differ by more than 8/255.
  - Installed models (reported, private): Monster05: 4 of 307,200 pixels differ by more than 8/255.
  - Installed Monster167 (v15): 5 of 480,000.
  - Installed Smith01 (v10): 6 of 480,000. Mean channel difference is below 0.006.
- (Reported.) The culling convention was checked empirically. With counter-clockwise front faces culled at the back, Monster05, Monster01, Smith01 and Monster20 differ from no-cull renders in 0, 6, 10 and 65 pixels at 320x240; clockwise differs in thousands. The spider (Monster10) differs either way, which suggests it has open single-sided parts.
- (Reported.) The windowed viewer ran for 3 s at about 115 fps (vsync) with animation.

Local render paths are listed in the handoff and are not committed.

### Corpus pass

Reported; `test_corpus_scan` pins these counts for private runs.

`mu-render scan` takes 6 s. It loaded, built client memory for, ticked, posed, skinned and drew:

- v10: 701 of 701;
- v12: 180 of 180;
- v14: 216 of 216;
- v15: 11,566 of 11,583 (the 17 known rejections).

No mesh was refused and no polygon has four corners. The v12, v14 and v15 vertex total is 3,814,006, the same figure as the CLIENT-SKIN-001 corpus.

## Not established (gaps)

- **Live draw arguments.** The mesh draw's rules are verified by execution, but the flags, alpha, select and texture arguments and the model fields that game callers pass are unknown. The viewer defaults to body flags 2, the dominant immediate. Texture filtering, wrap, row order, mipmaps, depth function, alpha reference and fog are static readings of the loaders and scene setup ([client-meshdraw-exec.md](client-meshdraw-exec.md#static-readings-not-executed)).
- **Large time values.** sin/cos arguments of magnitude 90,112 or more take the CRT's x87 fallback. Unicorn evaluates it with the host libm, so the port's equality there is unverified. This affects wave 0x400 after about 3.6 hours of client time.
- **Animation control is the viewer's own.** Action changes, speeds and stop flags are viewer controls; the client's action-change code is untraced. Player parts and attachments are now assembled by the character mode ([NATIVE-CHAR-001](native-character.md)).
- **Some inputs stay unsupported.** Mode 0x8000 faults in the viewer, as the client would on a freed pixel buffer. The 17 rejected v15 files remain rejected.

## Recommended next native milestones

1. **Character assembly.** Done in [NATIVE-CHAR-001](native-character.md). Its open items are the world-path weapon details (lighting flag, draw `0x0176ce74`, per-part animation state, attribute branches, back-carried weapons) and action names.
2. **Done:** the mesh draw and body executed under Unicorn ([CLIENT-MESHDRAW-EXEC-001](client-meshdraw-exec.md)).
3. **Terrain.** Done for the ground itself (NATIVE-TERRAIN-001, [client-terrain.md](client-terrain.md)); static objects wait for the `.obj` placement.
4. **Effects.** The JSON effect system with its 144-byte stream VBO sprites and particles (EFFECT-001).
5. **UI and fonts.** The 2D helpers `0x0184d9bb`/`0x0184dcb1` and the bitmap font path.
6. **Input and frame loop.** A port of the 40 ms logic and frame driver.
7. **Network and services last**, after the simulation boundary is understood.
