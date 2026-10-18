# Native viewer (NATIVE-VIEW-001)

This is the first native macOS rendering milestone. It is an arm64 viewer that does not use Wine or Rosetta. It loads a client BMD model and its textures, animates it with the reconstructed animation tick and pose builder, skins it with the reconstructed CPU transform (`mu_model_transform`) and draws it with a port of the client's mesh draw `0x012b8d1d` and body `0x012bb35a`. That port's GL call stream equals the routine executed under Unicorn ([CLIENT-MESHDRAW-EXEC-001](../docs/research/client-meshdraw-exec.md)). It is a model viewer, not a game client. See [the finding](../docs/research/native-viewer.md) for evidence and limits.

## Build

```sh
brew install cryptopp sdl2 jpeg-turbo      # Debian/Ubuntu: libcrypto++-dev libsdl2-dev libjpeg-dev
make -C native                             # core + headless tool build/mu-render (macOS and Linux)
make -C native viewer                      # windowed viewer build/mu-viewer (SDL2 + OpenGL 2.1)
make -C native frame-window                # frame-loop skeleton window build/mu-frame-window (NATIVE-FRAME-001)
```

Without libjpeg, JPEG textures are reported as missing (`MU_NO_JPEG=1` forces that). The core needs only clang and Crypto++, which BMD v14 already requires.

## Run

```sh
native/build/mu-viewer "$MU_GAME_ROOT/Data/Monster/Monster01.bmd"
native/build/mu-viewer --headless --backend gl --compare --out /tmp/m.png MODEL.bmd
native/build/mu-render render MODEL.bmd --out /tmp/m.png        # software rasterizer, prints SHA-256
native/build/mu-render dump MODEL.bmd --out /tmp/m.bin --action 1 --frame 2.5 --ticks 3
native/build/mu-render corners MODEL.bmd --out /tmp/m.ops --flags 0x1000 --client-time 2500 --case-out /tmp/m.case
native/build/mu-render replay /tmp/m.case --out /tmp/r.ops --tables-out /tmp/r.tables
native/build/mu-render scan "$MU_GAME_ROOT/Data"                # read-only corpus pass

native/build/mu-proto build C1 F1 010203 --xor                 # compose a packet
native/build/mu-proto parse c106f1010203                       # classify a frame
native/build/mu-proto dechunk c106f1010203c2000700aabbcc        # split a stream
native/build/mu-frame [MODEL.bmd] --out-dir DIR --frames 180      # headless frame loop, scripted clicks and zoom
native/build/mu-frame-window [MODEL.bmd]                          # client camera, click-to-move, wheel zoom, 25 FPS cap
native/build/mu-render ui title --root "$MU_GAME_ROOT" --size 1024x768 --out /tmp/title.png   # 2D layer
native/build/mu-render ui login --root "$MU_GAME_ROOT" --font Tahoma --out /tmp/login.png
```

Character mode (NATIVE-CHAR-001, [finding](../docs/research/native-character.md)) assembles a player from the shared `Player.bmd` skeleton. Class body parts come from a class byte: low nibble class, high nibble evolution flags. Slots 1..5 (helm..boots) can be overridden with `--part`. Weapon slot 0 links to bone 33 (right hand), slot 1 to bone 42 (left hand) and `--wing` to bone 47:

```sh
G="$MU_GAME_ROOT"
native/build/mu-viewer --game-root "$G" --class 1 --action 4 --prior-action 4 \
    --weapon 0 "$G/Data/Item/Sword01.bmd" --weapon 1 "$G/Data/Item/Shield01.bmd"
native/build/mu-render character --game-root "$G" --class 0 --action 10 --prior-action 10 --frame 1 \
    --prior-frame 1 --weapon 0 "$G/Data/Item/Staff01.bmd" --out /tmp/dw.png
native/build/mu-render chardump --game-root "$G" --class 0x11 --part 2 "$G/Data/Player/ArmorMale05.bmd" \
    --wing "$G/Data/Item/Wing04.bmd" --out /tmp/c.bin      # golden data for the tests
```

`--origin`, `--angles`, `--head`, `--scale` (default 0.9, the creation value), `--color`, `--lighting` and `--wing-scale` set the character object. The animation options drive the Player. `--prior-action` should normally equal `--action`: at an integer frame the pose shows the prior key. In the viewer, Left and Right change the Player action.

The frame-loop skeleton (`core/mu_frame.*`, [finding](../docs/research/client-camera-input.md)) runs the client's 40 ms logic steps and frame cap, its in-world camera, wheel FOV zoom, key scan and terrain picking from `reconstructed/camera`. The terrain is a flat placeholder and the hero walks in a straight line.

`mu-render ui` (NATIVE-UI-001) renders the title/loading screen and the login scene's 2D overlay with the
reconstructed 2D routines (`reconstructed/ui`) and a software GL subset. See [the finding](../docs/research/client-ui-2d.md).
`mu-render ui servers` and `mu-render ui credits` (NATIVE-UI-002) add the server-select and credits windows
of the legacy window layer over synthetic server and credit data; `--frames "x,y,down,up;..."` drives hover,
press and click. See [the widget finding](../docs/research/client-ui-widgets.md).

Viewer controls:

- Mouse: left drag orbits, right drag (or Shift+left) pans, the wheel zooms.
- Animation: Space plays or pauses. Left and Right switch actions. Up and Down change the speed. `,` and `.` step one frame while paused. S toggles the action's stop flag.
- Drawing: M cycles the render flags (2, 0x42, 4, 0x1000, 0x4000, 1); the mesh draw derives its mode from them. L toggles lighting and T toggles the alpha test. C cycles culling (follow the state reading, off, on). F flips the front face and G toggles wireframe.
- Files and view: N and P load the next or previous model in the directory. R resets the camera. O saves a screenshot.

Game logic advances in fixed 40 ms steps, like the client's frame driver. All options are listed by `mu-render` without arguments.

## Actor mode (NATIVE-ACTOR-001)

`mu-render actor` renders an animated monster or NPC ([finding](../docs/research/client-actors.md)). `--type` is a server monster class (CreateMonster table), `--monster` a monster type (`Data/Monster/Monster<type+1>.bmd`), `--npc` an NPC model index. Actions get the client's play speeds; each 40 ms step runs the reconstructed SetAction and animation step with the tick:

```sh
native/build/mu-render actor --game-root "$MU_GAME_ROOT" --type 0 --action 2 --time 1 --out walk.png \
    --frames 12 --frame-steps 2 --strip walk-strip.png --gif walk.gif
native/build/mu-render character --game-root "$MU_GAME_ROOT" --class 1 --pose walk --weapon-kind 1 \
    --weapon 0 "$MU_GAME_ROOT/Data/Item/Sword01.bmd" --time 0.3 --frames 10 --gif dk-walk.gif
```

Monster actions: 0/1 idle, 2 walk, 3/4 attack, 5 hit, 6 die. `--pose stand|walk|attack` picks a Player action with the client's base Player speed (the pose mapping is a static reading).

## Walking around the world (NATIVE-WORLD-001)

`mu-world` (window, `make -C native world`) and `mu-walk` (headless software, built by `make -C native`) run one
in-world session (`core/mu_walk.*`, [finding](../docs/research/native-world.md)): the world's terrain, the hero
from the character module, the client camera with the world's camera record (Lorencia: FOV 39), click-to-move
through the client pick and path finder, the client walk step (12 units per 40 ms step) and the wheel zoom.

```sh
native/build/mu-world --game-root "$MU_GAME_ROOT"                       # click to walk, wheel zooms
native/build/mu-world --game-root "$MU_GAME_ROOT" --headless --backend gl --frames 900 --every 3 \
    --out-dir DIR --walk "137,131 141,135" --wheel "290:1 470:-1"     # scripted clicks and zoom
```

## Terrain mode (NATIVE-TERRAIN-001)

```sh
native/build/mu-terrain info   "$MU_GAME_ROOT" --world 0                 # load report of Data/World1
native/build/mu-terrain render "$MU_GAME_ROOT" --world 142 --out k.png   # software render, prints SHA-256
native/build/mu-terrain scan   "$MU_GAME_ROOT"                           # every Data/World* folder
native/build/mu-viewer --terrain "$MU_GAME_ROOT" --world 0               # free camera: WASD/QE, drag, wheel
native/build/mu-viewer --terrain "$MU_GAME_ROOT" --world 0 --headless --backend gl --compare --out t.png
```

`--world` is the client's world index (Lorencia 0, Twisted Karutan 142); the folder is resolved like the
client. The tile rules come from `reconstructed/terrain`, compared with the client's instructions by
`scripts/validate_terrain.py`; see [the finding](../docs/research/client-terrain.md). Static objects are not
drawn: the installed `EncTerrain*.obj` files do not decode with the client's loader routine.
## Audio (NATIVE-AUDIO-001)

```sh
make -C native audio            # build/mu-audio and build/libmuaudio (no Crypto++ or SDL2 needed)
make -C native audio-live       # build/mu-audio-live (SDL2 audio)
scripts/extract_audio_tables.py --text CAPTURE --data DATA --out /tmp/t.json --tsv /tmp/t.tsv   # local only
native/build/mu-audio list --table /tmp/t.tsv --root "$MU_GAME_ROOT"
native/build/mu-audio render --table /tmp/t.tsv --root "$MU_GAME_ROOT" --script SCRIPT --out /tmp/scene.wav
```

The script language and the engine's platform choices are described in `core/mu_audio_host.h` and
`core/mu_audio.h`; the client logic it runs is `reconstructed/audio` ([finding](../docs/research/client-audio.md)).
MP3/OGG decode through AudioToolbox on macOS only.

NATIVE-TERRAIN-002 ([finding](../docs/research/client-terrain-frame.md)): `mu-terrain render` takes
`--light X,Y,R,G,B,RANGE`, `--decal X,Y,SIZE,ROT`, `--detail 4`, `--frustum HX,HY` (client culling around a hero
position) and `--legacy`; `mu-viewer --terrain` toggles lights (L), the client frustum (F), a decal (K) and the
graphics option (4). Water/lava worlds such as Vulcanus (63) and Atlans (7) now draw.

## Layout

| Path | Role |
|---|---|
| `core/mu_bmd.*` | Envelope decoding through the repository's v12/v15 client-linked decoders and the v14 Crypto++ reader, then the client reader's unchecked stream walk; every `bmd10.py` check becomes a listed anomaly (`mu-render info`), structural limits still reject ([MODEL-EDGE](../docs/research/model-edge.md)) |
| `core/mu_model.*` | Lays the model out as client memory, runs `mu_bone_tracks_read` once, then calls `mu_animation_tick`, `mu_pose_build` and `mu_model_transform` unchanged; out-of-range vertex/normal bones read zero-filled spans at the client's addresses |
| `core/mu_edge.*` | Corner indices past their arrays: the client's reads redirected to zero entries (fresh-client state), so such meshes draw instead of being refused |
| `core/mu_character.*` | Character assembly: Player pose into one shared bone/root buffer, body parts skinned against it, items attached through the reconstructed rotation position and a keep-root pose |
| `core/mu_meshdraw.*` | Platform-neutral port of the mesh draw, body, GL state wrappers, normal-texcoord table and texture-name sub-object parser, emitting the literal GL call stream |
| `core/mu_meshdraw_case.*` | Self-contained mesh-draw case files (inputs + calls) shared with `scripts/validate_meshdraw.py` |
| `core/mu_scene.*` | Builds the client inputs for a BMD and forwards the stream to a backend (effective state per `glBegin`) |
| `core/mu_raster.*` | Deterministic software rasterizer for headless renders with host-independent hashes |
| `core/mu_image.*`, `mu_textures.*` | OZJ/OZT/OZB unwrapping as in `recover_images.py`, TGA, BMP and JPEG decoding, and the client's upload rules (TGA/JPEG rule, power-of-two padding, per-texture filter and wrap) |
| `core/mu_camera.*`, `mu_png.*`, `mu_options.*` | Camera with libm-free trigonometry, a PNG writer and SHA-256, shared options |
| `core/mu_actor.*`, `mu_gif.*` | Monster/NPC actors: file resolution, the reconstructed opener's action speeds over the model's client memory, SetAction and the animation step per 40 ms; animated GIF writer |
| `core/mu_terrain.*` | World loading (decryption, reconstructed parsers, heights, light, bitmaps) and the terrain raster adapter |
| `tools/mu_terrain.c` | Headless terrain CLI (`build/mu-terrain`) |
| `core/mu_protocol.*` | NATIVE-NET-001 network protocol: C1–C4 framing, the send obfuscation XOR, the packet builder, the receive dechunker and the serial counter. No Crypto++, no client bytes. See [the finding](../docs/research/client-net-protocol.md) |
| `core/mu_wav.*`, `mu_audio*.*` | WAV decoder, FMOD-boundary software mixer, platform decoder, script host (audio) |
| `tools/mu_audio.c`, `tools/mu_audio_live.c` | Audio CLI (`list`, `decode`, `render`, `scan`) and SDL2 live player |
| `viewer/` | SDL2 window, OpenGL immediate-mode backend, CGL offscreen context for headless GL |
| `core/mu_ui_raster.*`, `mu_ui_assets.*`, `mu_ui_font.*` | 2D layer: software GL subset, interface texture table through the reconstructed OpenTga/OpenJpeg, GDI text boundary (CoreText) |
| `tools/mu_render.c`, `tools/mu_render_ui.c` | Headless CLI used by the tests (`mu-render ui …` for the 2D layer) |
| `core/mu_walk.*`, `world/` | Walk-around session and its front ends `mu-world` / `mu-walk` (NATIVE-WORLD-001) |
| `core/mu_frame.*`, `tools/mu_frame.c`, `frame/` | Frame-loop skeleton: client timing, camera, input and picking (NATIVE-FRAME-001); headless tool and SDL2 window |
| `core/mu_effect.*`, `tools/mu_effect_tool.c` | Data/Effect `.ein` particle systems and billboards through `reconstructed/effects` (instruction-compared), software-raster draw with the client's blend modes; headless CLI `build/mu-effect` (`render`, `sheet`, `dump`, `scan`) (NATIVE-FX-001). See [the finding](../docs/research/client-effects.md) |
| `core/mu_effect_scene.*` | Effect trees and scenes of several effects like the client's EffectManager: template cache by name, clones, owner-attached instances, octree, frustum render pass over a loaded world; `mu-effect scene` (NATIVE-FX-002). See [the finding](../docs/research/client-effect-manager.md) |
| `tests/` | Synthetic fixtures, golden reference harnesses (models and characters), unittest suites (client-verified mesh-draw digests) |

## Data tables (NATIVE-DATA-001)

`make -C native build/mu-data` builds the table tool. It needs no Crypto++ or image libraries. Commands: `list [GAME_ROOT]`, `dump FILE`, `item-models FILE --json`, `model ITEM_BMD INDEX`, `decode FILE --out PATH` and `mpr Lang.mpr`. Output is local only; never commit decoded tables or text. See [the finding](../docs/research/client-data-tables.md). NATIVE-DATA-002 adds named fields to `dump`, plus `item ITEM_BMD CODE` (attributes, client max durability, bans) and `layouts` ([finding](../docs/research/client-item-attributes.md)).

## Tests

`make test` runs `native/tests`. The portable checks build everything from authored synthetic models and textures. The private checks run with `MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=...`. Set `MU_NATIVE_GOLDEN_PER_VERSION` and `MU_NATIVE_GOLDEN_MAX_VERTICES` to widen the installed golden sample. The private mesh-draw execution test needs Unicorn (`tools/requirements-lock.txt`) and the pinned evidence (`MU_CLIENT_TEXT`, `MU_IMAGE_DATA`, `MU_TRIG_FLAG`, `MU_MATH_DATA`, or the default `evidence/` paths); `MU_MESHDRAW_PER_FOLDER` widens its installed sample. Renders of installed assets stay local and are never committed.
