# Native viewer (NATIVE-VIEW-001)

This is the first native macOS rendering milestone. It is an arm64 viewer that does not use Wine or Rosetta. It loads a client BMD model and its textures, animates it with the reconstructed animation tick and pose builder, skins it with the reconstructed CPU transform (`mu_model_transform`) and draws it with the ported per-corner rules of the client's mesh draw routine `0x012b8d1d`. It is a model viewer, not a game client. See [the finding](../docs/research/native-viewer.md) for evidence and limits.

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
native/build/mu-render corners MODEL.bmd --out /tmp/m.ops --mode 4
native/build/mu-render scan "$MU_GAME_ROOT/Data"                # read-only corpus pass

native/build/mu-proto build C1 F1 010203 --xor                 # compose a packet
native/build/mu-proto parse c106f1010203                       # classify a frame
native/build/mu-proto dechunk c106f1010203c2000700aabbcc        # split a stream
native/build/mu-frame [MODEL.bmd] --out-dir DIR --frames 180      # headless frame loop, scripted clicks and zoom
native/build/mu-frame-window [MODEL.bmd]                          # client camera, click-to-move, wheel zoom, 25 FPS cap
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

Viewer controls:

- Mouse: left drag orbits, right drag (or Shift+left) pans, the wheel zooms.
- Animation: Space plays or pauses. Left and Right switch actions. Up and Down change the speed. `,` and `.` step one frame while paused. S toggles the action's stop flag.
- Drawing: M cycles the draw mode (2, 4, 0x1000, 1). L toggles lighting and T toggles the alpha test. C cycles culling (follow the state reading, off, on). F flips the front face and G toggles wireframe.
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

## Layout

| Path | Role |
|---|---|
| `core/mu_bmd.*` | Envelope decoding through the repository's v12/v15 client-linked decoders and the v14 Crypto++ reader, then a C port of every `bmd10.py` check |
| `core/mu_model.*` | Lays the model out as client memory, runs `mu_bone_tracks_read` once, then calls `mu_animation_tick`, `mu_pose_build` and `mu_model_transform` unchanged |
| `core/mu_character.*` | Character assembly: Player pose into one shared bone/root buffer, body parts skinned against it, items attached through the reconstructed rotation position and a keep-root pose |
| `core/mu_meshdraw.*` | Platform-neutral port of the per-corner loop and colour pass from `mac-play/hotpatch/meshdraw.c` (no Windows or x86 dependencies, no client addresses) |
| `core/mu_scene.*` | Per-mesh client order: pre-loop colour, colour pass, state and texture, one `GL_TRIANGLES` block |
| `core/mu_raster.*` | Deterministic software rasterizer for headless renders with host-independent hashes |
| `core/mu_image.*`, `mu_textures.*` | OZJ/OZT/OZB unwrapping as in `recover_images.py`, plus TGA, BMP and JPEG decoding |
| `core/mu_camera.*`, `mu_png.*`, `mu_options.*` | Camera with libm-free trigonometry, a PNG writer and SHA-256, shared options |
| `core/mu_actor.*`, `mu_gif.*` | Monster/NPC actors: file resolution, the reconstructed opener's action speeds over the model's client memory, SetAction and the animation step per 40 ms; animated GIF writer |
| `core/mu_terrain.*` | World loading (decryption, reconstructed parsers, heights, light, bitmaps) and the terrain raster adapter |
| `tools/mu_terrain.c` | Headless terrain CLI (`build/mu-terrain`) |
| `core/mu_protocol.*` | NATIVE-NET-001 network protocol: C1–C4 framing, the send obfuscation XOR, the packet builder, the receive dechunker and the serial counter. No Crypto++, no client bytes. See [the finding](../docs/research/client-net-protocol.md) |
| `viewer/` | SDL2 window, OpenGL immediate-mode backend, CGL offscreen context for headless GL |
| `tools/mu_render.c` | Headless CLI used by the tests |
| `core/mu_frame.*`, `tools/mu_frame.c`, `frame/` | Frame-loop skeleton: client timing, camera, input and picking (NATIVE-FRAME-001); headless tool and SDL2 window |
| `tests/` | Synthetic fixtures, golden reference harnesses (models and characters), independent mesh-draw model, unittest suites |

## Tests

`make test` runs `native/tests`. The portable checks build everything from authored synthetic models and textures. The private checks run with `MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=...`. Set `MU_NATIVE_GOLDEN_PER_VERSION` and `MU_NATIVE_GOLDEN_MAX_VERTICES` to widen the installed golden sample. Renders of installed assets stay local and are never committed.
