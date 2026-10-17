# Native model viewer (NATIVE-VIEW-001)

This is the first native macOS rendering milestone. It builds an arm64 viewer, without Wine or Rosetta, that:

- loads a client BMD model of any supported version and its textures;
- animates the model with the reconstructed animation tick `0x012b4dd3` and pose builder `0x012b5064`, after the reconstructed bone-track loop `0x012b4225`;
- skins it with the reconstructed CPU transform `0x012b5bde`;
- draws it with the per-corner rules of the mesh draw `0x012b8d1d`.

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
| Corner loop and colour pass | `native/core/mu_meshdraw.c`, a port of `mac-play/hotpatch/meshdraw.c` `md_run`/`md_light_run` | ported: same rules and operation order, explicit host pointers |
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
  - the 50 mesh-draw streams against `meshdraw_reference.py`;
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

`native/tests/meshdraw_reference.py` is a second implementation of the rules. It was written from `meshdraw-notes.md` and the static state reading, not from the C module (reported by the author; the repository cannot show authorship order), with binary32 rounding of every operation. It is fed the transform outputs that the golden test verified, and must match `mu-render corners` bitwise. That stream records the state, the pre-loop colour, begin/end and every texcoord, colour and vertex call.

- 25 option sets x 2 models (v10, v15) = 50 streams, more than 8,000 records.
- Coverage:

| Draw mode / flag | Rule | Covered |
|---|---|---|
| 2 | mesh UVs; uv offset on the selected mesh; per-normal colour with the light byte | yes (light on/off, mesh skip, secondary-light select) |
| 4 | object colour + normal-table texcoord | yes |
| 0x1000, 0x80000, 0x100000 | object colour + normal-table texcoord + uv offset | yes |
| 1, 0x40, others | no attributes | yes for 1 and 0x40 (the shared default branch); other values not exercised |
| alpha >= 0.99 / < 0.99 / NaN | glColor3fv / glColor4f / glColor4f | yes |
| flag 0x20 | planar projection about the origin (2000, 4000, 5) | yes (also 0x420: 0x20 wins) |
| flag 0x200000 | skip corner when voff > z of corners 0..2 | yes (no cull and partial cull) |
| colour pass | L*C, or S*C + 0.2 with model +0xcb == 1 | yes |
| mode 0x8000, flag 0x400 | client calls (alpha/colour mutation, client sine) | refused, emits nothing; tested |
| state reading | blend/depth/cull/alpha from flags 1, 0x10, 0x40, 0x80, 0x2000, 0x40000, 0x400000 | yes (static reading only) |

Direct ctypes checks cover refusing out-of-range indices before any call, and NaN alpha. In game, modes 2, 4, 0x1000 and 0x40 were the only ones observed (meshdraw-notes.md). The 0x20 and 0x200000 paths were never seen there, so in-game evidence for them is still missing.

### Textures

- Portable: OZT (both prefix variants), OZB, TGA (raw and RLE, both origins, 24 and 32 bit) and BMP decode identically to Pillow. A synthetic JPEG decodes within 8 levels. Bad wrappers are rejected. A TGA whose image-ID length runs past the end of the file is rejected; before the post-merge review fix, the uncompressed path read past the buffer (found with AddressSanitizer).
- Private (reported): 2,402 installed Monster/Player/NPC textures (1,989 JPEG, 413 TGA) are pixel-identical to `recover_images.decode`. The private test checks the first 400 Monster files.

### Renders

- `mu-render render` uses the software rasterizer. Five settings on a synthetic textured model have pinned SHA-256 hashes of the raw RGBA pixels: default, nearest filtering with a pose, blend with cull, additive environment mode, and alpha test unlit. CI checks the same hashes on macOS arm64 and Ubuntu x86_64. The author also reports them on Ubuntu 24.04 arm64 and x86_64 in local docker containers (x86_64 emulated). The PNG round trip and repeat determinism are checked, and the three envelopes render identically.
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

- **State and texture setup is a static reading.** The flag-to-state mapping, the pre-loop colour and the mesh texture bind follow the static reading; the mesh draw body was never executed. These are unknown:
  - the draw-mode selection from the caller's flags;
  - the uv-offset mesh selector;
  - texture filtering, wrap, mipmaps and row order;
  - the alpha-test reference;
  - the depth function;
  - fog.

  The viewer's values (GL_LINEAR, GL_REPEAT, top row first, LEQUAL, GREATER 0.25) are choices.
- **The normal-indexed texcoord table is a placeholder.** Its writer (`0x072acfd8`, used by modes 4/0x1000/0x80000/0x100000) is unrecovered. The viewer substitutes 0.5 + 0.5·(normal x, y), labelled as such.
- **Animation control is the viewer's own.** Action changes, speeds and stop flags are viewer controls; the client's action-change code is untraced. Player parts (`Player/ArmorClass*.bmd`, one key) need the shared `Player.bmd` skeleton and the keep-root attachment path, which are not wired.
- **Some draw paths are left out.** Mode 0x8000 and flag 0x400 need client routines and are refused. The 17 rejected v15 files remain rejected.

## Recommended next native milestones

1. **Character assembly.** Player skeleton plus part models, the root setter `0x012b7019` and keep-root attachments, so equipped characters can be viewed.
2. **Execute the mesh draw `0x012b8d1d` and body `0x012bb35a` under Unicorn** with a GL-call recorder, as planned in the CLIENT-SKIN-001 handoff. Compare against `mu_meshdraw` and this scene driver. That settles mode selection, state, textures and the normal table.
3. **Terrain.** Recover the tile renderer `0x016cd468` (fans per tile per layer) and the terrain formats (TERRAIN-001), and render a map with the same backend.
4. **Effects.** The JSON effect system with its 144-byte stream VBO sprites and particles (EFFECT-001).
5. **UI and fonts.** The 2D helpers `0x0184d9bb`/`0x0184dcb1` and the bitmap font path.
6. **Input and frame loop.** A port of the 40 ms logic and frame driver.
7. **Network and services last**, after the simulation boundary is understood.
