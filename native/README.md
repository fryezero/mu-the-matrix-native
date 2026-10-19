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

Click-to-move (`core/mu_path.*`, `build/mu-path`, NATIVE-PATH-001, [finding](../docs/research/client-path.md)) runs the client's path finder and path follower from `reconstructed/path` on a world's attribute map: `mu-path find|render|batch ROOT --world W --from X,Y --to X,Y` prints the client path and walk and renders it over a top-down terrain view; `--synthetic maze|rooms|noise|safezone|open` needs no game data. NATIVE-PATH-002: the walker's run counter follows SetPlayerWalk's rule (`--class C`, `--boots L`, `--run` = boots +5: 12 units per step, 15 from the 40th moving step; the safe zone keeps 0), and `--long` walks with the client's long-distance auto move (one search of up to 500 nodes, three-node segments, a new search where the list ends). `mu-world`/`mu-walk` take `--boots L` and `--auto-move X,Y`; in `mu-world` and `mu-client` (through `mu_walk`), S + left click starts the auto move toward the clicked tile, and every hero walk uses the run rule and the speed predicates.

`mu-render ui` (NATIVE-UI-001) renders the title/loading screen and the login scene's 2D overlay with the
reconstructed 2D routines (`reconstructed/ui`) and a software GL subset. See [the finding](../docs/research/client-ui-2d.md).
`mu-render ui servers` and `mu-render ui credits` (NATIVE-UI-002) add the server-select and credits windows
of the legacy window layer over synthetic server and credit data; `--frames "x,y,down,up;..."` drives hover,
press and click. See [the widget finding](../docs/research/client-ui-widgets.md).
`mu-render ui inventory` (NATIVE-HUD-001) places items in the inventory grid by their Item.bmd size, runs the
reconstructed slot pass and RenderItem3D and draws the item models under the client's orthographic item pass
(the GFx frame is a plain stand-in); `--hover N` adds the item's tooltip from itemtooltip/itemtooltiptext through
the reconstructed formatter cases, `mu-render ui tooltip --item CODE[:LEVEL]` draws one tooltip. See
[the HUD finding](../docs/research/client-hud.md).

`native/gfx` (NATIVE-GFX-001/002) plays the client's GFx windows with a pinned external Ruffle plus the GFx
patch series `native/gfx/ruffle-patches` (applied by `apply-ruffle-patches.sh`, which `fetch-ruffle.sh` runs). It
holds the movie inventory, the GFx→SWF converter, the `mugfx` C ABI, the GFx layer `mu_gfx_layer.c` (bar,
inventory, tooltips, character window, chat; loads libmugfx at run time) and `mu-gfx-window`. Build:
`native/gfx/fetch-ruffle.sh && native/gfx/build-mugfx.sh`. `mu-world --gfx DIR [--gfx-open inventory,character]`
shows the interface over the world (DIR: movies converted with `gfxconvert.py --bridge --transparent --var
_root.isClient=true --fontconfig English --font-subset latin --movie main --movie InventoryFrame --movie InfoPopup
--movie CharacterInfoFrame --movie chat`). See [the finding](../docs/research/native-gfx.md) and
[NATIVE-GFX-002](../docs/research/native-gfx2.md).
NATIVE-GFX-003 ([finding](../docs/research/native-gfx3.md)) plays the HUD as the client's base movie. For that,
convert `base ExternalBase ImageData Icons main Chat Tooltip Popups ItemDurability AlarmFrame topmenu bufflist
hudPlayerName hudMap hudNotice` along with the windows, using the same options. The skill and item hotkey icons
appear, and `loadBitmapFromLib` works. With a game root, mu-world draws the item models over the inventory and
into the hotkey image. `mu-client --gfx DIR [--gfx-open ...]` shows the interface in the world scene.
`scripts/validate_gfx3.py` compares the layer's game side with the client in Unicorn.

Viewer controls:

- Mouse: left drag orbits, right drag (or Shift+left) pans, the wheel zooms.
- Animation: Space plays or pauses. Left and Right switch actions. Up and Down change the speed. `,` and `.` step one frame while paused. S toggles the action's stop flag.
- Drawing: M cycles the render flags (2, 0x42, 4, 0x1000, 0x4000, 1); the mesh draw derives its mode from them. L toggles lighting and T toggles the alpha test. C cycles culling (follow the state reading, off, on). F flips the front face and G toggles wireframe.
- Files and view: N and P load the next or previous model in the directory. R resets the camera. O saves a screenshot.

Game logic advances in fixed 40 ms steps, like the client's frame driver. All options are listed by `mu-render` without arguments.

## World render mode (NATIVE-RENDERCHAR-001)

`--world-render` draws a character or actor the way the client's world render does ([finding](../docs/research/client-renderchar.md)): item level glow passes (+0..+15), excellent and ancient passes, back-carried weapons in a safe zone, the +15 `class15_*` attachments and monster weapons on the create-assigned link bones:

```sh
native/build/mu-render character --game-root "$G" --class 1 --weapon 0 "$G/Data/Item/Sword13.bmd" --world-render \
    --item-level all=15 --excellent weapon0=1 --attachments --world-time 900 --glow-color 0.4,0.6,1 --out /tmp/w.png
native/build/mu-render character --game-root "$G" --class 1 --weapon 0 "$G/Data/Item/Axe07.bmd" --world-render --safe-zone --out /tmp/b.png
native/build/mu-render actor --game-root "$G" --type 0 --world-render --actor-weapon "0=$G/Data/Item/Axe07.bmd" --out /tmp/m.png
```

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

## A living world (NATIVE-WORLD-002)

`mu-world`/`mu-walk` also play the client's footsteps and per-frame music/ambient (SDL2 audio in the window, `--wav`
headless; `--sound-table` is the table `scripts/extract_audio_tables.py --tsv` extracts locally), draw the terrain
through the client frustum (`--legacy-box` for the old square) and place monsters and NPCs from a demo placement file
standing in for the server ([finding](../docs/research/native-world-alive.md)):

```sh
native/build/mu-world --game-root "$MU_GAME_ROOT" --placement native/world/lorencia-demo-placement.txt \
    --sound-table /local/audio-tables.tsv
```

## Combat (NATIVE-COMBAT-001)

`--combat` adds the client side of a fight to `mu-world`/`mu-walk` (`core/mu_combat.*` over `reconstructed/combat`,
[finding](../docs/research/client-combat.md)): a click on a monster selects it, the hero walks into the client's
attack range, faces it and attacks with the SetPlayerAttack action and the SetAttackSpeed play speed; AttackTime counts
to 15 and the end of the attack creates arrows (bows), the Fire Ball model and the Energy Ball and Heal bitmaps; keys
1..6 cast Fire Ball, Energy Ball, Cyclone, Twisting Slash, Triple Shot and Heal. Damage text, hit reactions (action 5),
death (action 6), fade, sinking and removal run the client routines. The server side (damage, death, respawn,
counter-attacks) is a labelled demo.

```sh
native/build/mu-world --game-root "$MU_GAME_ROOT" --placement native/world/lorencia-demo-placement.txt \
    --tile 182,127 --class 1 --combat-weapon sword
native/build/mu-walk --game-root "$MU_GAME_ROOT" --headless --frames 400 --every 4 --out-dir DIR \
    --placement native/world/lorencia-demo-placement.txt --tile 182,128 --class 2 --combat-weapon bow \
    --combat-script "6:attack:hound;150:skill:24:spider;300:skill:26:budge dragon"
```

`--combat-weapon none|sword|twohand|spear|bow|crossbow|staff`, `--attack-speed N`, `--combat-seed N`; script items are
separated by `;` (`F:attack:ACTOR`, `F:skill:N:ACTOR`, `F:click:ACTOR`, `F:stop`). Headless runs add `combat_frame`
lines and a `combat` summary.

NATIVE-COMBAT-002: skills and projectiles are drawn by the client's older effect system (`reconstructed/combat/skill_fx.*`,
verified: CreateEffect/MoveEffect, particles, joints, the spell hit check) with effect lights on the terrain; keys
7, 8, 9, 0 add Evil Spirit, Hellfire, Inferno and Cyclone; the hero's hits and death take SetPlayerShock/SetPlayerDie's
actions and voices; swings, casts and voices play through the sound table. `--hero-hp N` sets the demo hero's hit
points (death, respawn at the home tile after 100 steps).

## Ambient life and weather (NATIVE-ENV-001)

`mu-world`/`mu-walk` (and mu-client's world scene) run the client's environment routines from
`reconstructed/environment` through `core/mu_env.*`: every logic step MoveLeaves (behind the tick's guard),
MoveBoids and MoveFishs; every frame the birds, bats, butterflies, crows, fish shoals, fish and rats they spawn
(their BMD models, animated with the reconstructed tick), the leaf/snow/bubble/rain particles as RenderPlane3D quads
or RenderSprite billboards, and the world's clear colour. The ambient sounds (aBird1/aBird2/aBat, the rat) go to the
audio engine. Leaf particles stay invisible in worlds without `leaf01.OZJ` (Lorencia, Noria), as in the client:
its `.jpg` load replaces and empties the `.tga` bitmap ([finding](../docs/research/client-environment.md)).

```sh
native/build/mu-world --game-root "$MU_GAME_ROOT" --world 2 --tile 210,36            # Devias snow
native/build/mu-world --game-root "$MU_GAME_ROOT" --world 7 --tile 21,29 --headless --backend gl \
    --frames 300 --every 10 --out-dir /tmp/atlans                                       # Atlans shoals
native/build/mu-world --game-root "$MU_GAME_ROOT" --world 141 --tile 118,150          # Tormenta Island rain
```

`--no-env` disables the module, `--env-seed N` sets the rand() state at world entry (default 1), and
`--env-tga-leaves` loads the leaf `.tga` the client unloads (a viewer option, not client behaviour). Frame reports
add `"env": [boids, fishs, leaves, models drawn, particles drawn]`; the summary adds an `"env"` line.

## Particles, sprites and blob shadows (NATIVE-PARTICLE-001)

`core/mu_particles.*` runs the client's older particle and sprite system from `reconstructed/particles`
([finding](../docs/research/client-particles.md)) in `mu-world`/`mu-walk`/mu-client:

- CreateParticle from the object move pass (the fires and smoke of CreateFire), RenderObjectVisual (Lorencia's
  Waterspout smoke, MerchantAnimal flares; Tormenta's joints are counted), the rain splashes and the skills;
- MoveParticles once per logic step after the other movers;
- the sprite section after the environment: RenderSprites(0) (the butterfly glow, crow eyes, flares, Heal flash),
  then RenderParticles(0) with the client's bitmaps (`Data/Effect/*.OZJ`, the world's rain02/rain03);
- RenderBodyShadow for the ambient creatures and the hero's and monsters' parts.

`--no-particles` restores the stand-ins, `--particle-seed N` sets the module's rand() (default 1). The summary adds
a `"particles"` line, frame reports `"particles": [live, particles drawn, sprites drawn, shadows]`.

```sh
native/build/mu-world --game-root "$MU_GAME_ROOT" --world 0 --tile 142,130 --objects-dir LOCAL   # fountain smoke
native/build/mu-world --game-root "$MU_GAME_ROOT" --world 2 --tile 210,36                         # shadow on snow
```

## Joints, world-object effects, login particles (NATIVE-JOINT-001)

`core/mu_joints.*` runs the client's joint pool from `reconstructed/joints`
([finding](../docs/research/client-joints.md)) for both owners: the skills (`mu_combat`, now with the swirl's spark
streaks) and the world objects (`mu_particles`, which also keeps their effects). In `mu-world`/`mu-walk`/mu-client:

- Tormenta Island's crystals throw lightning joints `0x7f7d` (bolts, arcs, rings) and its markers raise the field
  tornado `0x40e` (an effect model); the Dungeon, Devias and Noria object visuals are ported (not seen without their
  decoded object lists);
- MoveEffects, MoveJoints, MoveParticles each step; effect models and RenderJoints(0) before the sprite section;
- the login scene's lantern sprites and its mist and spray particles go through the particle module (no stand-ins).

The summary adds a `"joints"` line, frame reports `"joints": [live, quads, effects]`. `--joint-demo SUB` (a viewer
test, not client behaviour) creates a lightning joint of subtype SUB above the hero every 20 steps.

```sh
native/build/mu-world --game-root "$MU_GAME_ROOT" --world 141 --tile 82,19 --objects-dir LOCAL   # crystals, tornado
native/build/mu-world --game-root "$MU_GAME_ROOT" --tile 133,127 --joint-demo 0x1a                # demo bolt
```

## Character select (NATIVE-CHARSEL-001)

`mu-charsel` and `mu-render charsel` (headless software, with the CCharSelMainWin 2D layer) and `mu-charsel-window`
(`make -C native charsel`, SDL2 + OpenGL) render scene 5 (`core/mu_charsel*`, [finding](../docs/research/client-character-select.md)):
World94 under its camera record, up to five synthetic characters (`--list FILE`), the selected one on slot marker 1
with the client's highlight. Marker 1 defaults to the position read from the running client; `--objects-dir DIR`
draws World94's static objects and takes the markers from a local decoded `EncTerrain94.plain`
([objects finding](../docs/research/client-objects.md), section 6).

```sh
native/build/mu-charsel --game-root "$MU_GAME_ROOT" --frames 50 --every 10 --cycle 10 --out-dir /tmp/charsel
```

## The client's scene flow, offline (NATIVE-SHELL-001)

`mu-client` (`make -C native client`, SDL2 + OpenGL) runs the client's own scene manager (`reconstructed/scene`,
[finding](../docs/research/client-scene-manager.md)) over the native modules: title with the startup progress →
login overlay and server select → an OFFLINE DEMO account panel (any input, nothing stored) → character select
(mu-charsel's session) → loading screen → the world (mu-world's session) with the chosen character's class and
equipment → Esc back to character select. There is no server connection: `client/offline-session.*` answers the
server list, login, character list and join from `client/demo-session.txt` (a real session would come from the
network layer, which is out of scope). `world/world_embed.c` and `charsel/charsel_embed.c` compile mu-world's and
mu-charsel's `main.c` unchanged as modules. `build/mu-shell` is the headless software build (`make -C native`).

```sh
native/build/mu-client --game-root "$MU_GAME_ROOT" --session native/client/demo-session.txt
native/build/mu-client --game-root "$MU_GAME_ROOT" --session native/client/demo-session.txt --headless --backend gl \
    --auto --frames 400 --every 20 --out-dir /tmp/shell                # whole flow, scripted, PNG captures
native/build/mu-shell --game-root "$MU_GAME_ROOT" --script "10:enter 14:text:demo 18:enter 40:enter" --wav /tmp/m.wav
```

In the window: click a server (or Enter), type anything and press Enter, choose a character with Left/Right or 1..5,
Enter plays, Esc returns (world → character select → server list), Esc twice on the server list quits.
`--sound-table`, `--placement`, `--world-objects` and `--charsel-objects` pass mu-world's and mu-charsel's options.

## The login scene's 3D world (NATIVE-LOGIN-001)

Behind the login overlay and the server list, `mu-client` now draws World95 (`core/mu_login`, `login/login_gl.c`,
[finding](../docs/research/client-login-scene.md)): the fixed camera record, the terrain (the sea), and with
`--login-objects DIR` (or `--objects-dir DIR` for all three scenes) the 47 objects of a local decoded
`EncTerrain95.plain` through the object lifecycle with the login world's handler `CGMLogInScene_Ex` (ship with its
glow meshes, wakes, sky, island beam, geese; lantern sprites and mist particles are stand-in billboards). The shell
runs the reconstructed tick head and render 3D part. `mu-render ui login|servers --scene` renders the same headless.

```sh
native/build/mu-client --game-root "$MU_GAME_ROOT" --login-objects LOCAL
native/build/mu-render ui servers --root "$MU_GAME_ROOT" --scene --objects-dir LOCAL --size 1722x1048 --out s.png
native/build/mu-render ui login --root "$MU_GAME_ROOT" --scene --objects-dir LOCAL --no-ui --steps 25 --out l.png
```

## Model lighting as the client (NATIVE-LIGHT-001)

The game scenes now light models with the client's inputs ([finding](../docs/research/client-model-light.md)):
the light vector (1.3, 0, 2) of the light-override byte `0x01cf1048` = 1 (read live; `mu_model_scene_params`),
RenderObject's pose with the body scale in the bones for static objects (normals carry the scale into the light
term), and monsters/NPCs coloured by the frame light + 0.2 with light 0.4/0.8/0.2. The model viewer and the CLI
model tools keep override 0 unless `--light-override 1`. Per-object light inputs:

```sh
native/build/mu-terrain render "$MU_GAME_ROOT" --world 94 --objects LOCAL/EncTerrain95.plain --object-steps 25 \
    --light-report 1 --width 64 --height 48          # one JSON line per drawn object, per-normal lights
```

`mac-play/diagnostics/lightread PID OUT` (our own client, under the game lock) snapshots the client's lighting state;
`scripts/validate_model_light.py` compares the native lights with the client's pose builder and transform under it.

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
## Static objects (NATIVE-OBJECTS-001)

`mu-terrain objects ROOT --world N` reports the object file (the installed files are refused by OpenWorld's map
check after the client's decode, see [the finding](../docs/research/client-objects.md)), its records and the type →
model table. `mu-terrain render … --objects installed|gallery|PLAIN_FILE` and `mu-viewer --terrain … --objects …`
(B toggles) draw objects, and `mu-world --objects-dir DIR` draws them in the walk-around session from local
decoded `EncTerrain<n>.plain` files (made by `mac-play/diagnostics/objread` and `scripts/live_objects_to_plain.py`
from a client you started, under the game lock; never committed); `gallery` is a labelled demo layout of every model the world loads
(`--object-tile X,Y --object-columns N --object-spacing U`). `core/mu_objects.h` is the API for other sessions.

## World objects at runtime (NATIVE-OBJECTS-002)

With `--objects-dir`, `mu-world`/`mu-walk` run the client's object lifecycle (`core/mu_objects_runtime.c` over
`reconstructed/objects/object_render.c`, [finding](../docs/research/client-objects-render.md)): CreateObject per
record, MoveObjects every 40 ms step (animation tick, AddTerrainLight from street lights, candles and fires, fire and
smoke particles through the particle module of NATIVE-PARTICLE-001, a labelled stand-in with `--no-particles`),
RenderObjects culling and RenderObject with the body light from the terrain
light and the blend-mesh RenderBody arguments. `mu-terrain render … --objects FILE --object-steps N` does the same
for a still. The summary line reports `objects_created`, `object_steps`, `object_ticks`, `object_lights`,
`object_draw_list` and `objects_animated`.

```sh
native/build/mu-world --game-root "$MU_GAME_ROOT" --world 0 --tile 146,110 --objects-dir LOCAL --headless \
    --backend gl --width 1600 --height 1000 --frames 40 --every 39 --out-dir /tmp/fires
```

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
| `core/mu_path.*`, `tools/mu_path.c` | Click-to-move: client path finder, hero click rules and 40 ms walk step (`build/mu-path`) |
| `tools/mu_terrain.c` | Headless terrain CLI (`build/mu-terrain`) |
| `core/mu_protocol.*` | NATIVE-NET-001 network protocol: C1–C4 framing, the send obfuscation XOR, the packet builder, the receive dechunker and the serial counter. No Crypto++, no client bytes. See [the finding](../docs/research/client-net-protocol.md) |
| `core/mu_wav.*`, `mu_audio*.*` | WAV decoder, FMOD-boundary software mixer, platform decoder, script host (audio) |
| `tools/mu_audio.c`, `tools/mu_audio_live.c` | Audio CLI (`list`, `decode`, `render`, `scan`) and SDL2 live player |
| `viewer/` | SDL2 window, OpenGL immediate-mode backend, CGL offscreen context for headless GL |
| `core/mu_ui_raster.*`, `mu_ui_assets.*`, `mu_ui_font.*` | 2D layer: software GL subset, interface texture table through the reconstructed OpenTga/OpenJpeg, GDI text boundary (CoreText) |
| `tools/mu_render.c`, `tools/mu_render_ui.c` | Headless CLI used by the tests (`mu-render ui …` for the 2D layer) |
| `core/mu_hud.*`, `tools/mu_render_hud.c` | Inventory item pass and tooltips over `reconstructed/hud` (`mu-render ui inventory\|tooltip`, NATIVE-HUD-001) |
| `core/mu_walk.*`, `world/` | Walk-around session and its front ends `mu-world` / `mu-walk` (NATIVE-WORLD-001) |
| `core/mu_world_audio.*`, `core/mu_world_actors.*` | In-world sound, demo-placed actors and their effects (NATIVE-WORLD-002) |
| `core/mu_env.*` | Ambient creatures and weather over `reconstructed/environment`: models, weather bitmaps, step and draw (NATIVE-ENV-001) |
| `core/mu_particles.*` | Particles, sprites and blob shadows over `reconstructed/particles`: effect bitmaps, step, sprite pass, shadows, the object/environment/skill hooks (NATIVE-PARTICLE-001); the world objects' joints and effects, the login scene's sprites and particles (NATIVE-JOINT-001) |
| `core/mu_joints.*` | The joint pool over `reconstructed/joints`: slot search, MoveJoints, RenderJoints as quads, render-type state (NATIVE-JOINT-001) |
| `core/mu_combat.*` | Combat in the walk-around session: hero attack, skills, effects, damage text, hit/death reactions over `reconstructed/combat`; demo server (NATIVE-COMBAT-001); effect/particle/joint pools, area skills, hero hit/death, combat sounds (NATIVE-COMBAT-002) |
| `core/mu_charsel*`, `charsel/` | Character-select session, its 2D layer and the front ends `mu-charsel` / `mu-charsel-window` (NATIVE-CHARSEL-001) |
| `core/mu_objects.*` | Static map objects: client `.obj` decode and map check, records, type → model table (`reconstructed/objects`), model loading and placement (NATIVE-OBJECTS-001) |
| `core/mu_objects_runtime.c` | Object lifecycle: CreateObject, MoveObjects/MoveObject, RenderObjects/RenderObject, object lights, stand-in particles (NATIVE-OBJECTS-002) |
| `core/mu_frame.*`, `tools/mu_frame.c`, `frame/` | Frame-loop skeleton: client timing, camera, input and picking (NATIVE-FRAME-001); headless tool and SDL2 window |
| `core/mu_effect.*`, `tools/mu_effect_tool.c` | Data/Effect `.ein` particle systems and billboards through `reconstructed/effects` (instruction-compared), software-raster draw with the client's blend modes; headless CLI `build/mu-effect` (`render`, `sheet`, `dump`, `scan`) (NATIVE-FX-001). See [the finding](../docs/research/client-effects.md) |
| `core/mu_effect_scene.*` | Effect trees and scenes of several effects like the client's EffectManager: template cache by name, clones, owner-attached instances, octree, frustum render pass over a loaded world; `mu-effect scene` (NATIVE-FX-002). See [the finding](../docs/research/client-effect-manager.md) |
| `client/`, `world/world_embed.*`, `charsel/charsel_embed.*` | mu-client: scene manager runtime over `reconstructed/scene`, offline session, window/headless front end; mu-world and mu-charsel as modules (NATIVE-SHELL-001) |
| `core/mu_lang.*`, `core/mu_lang_maps.h`, `tools/mu_lang_tool.c` | Lang.mpr tables from local plaintext read off the running client: GlobalText, skills (GetSkillInformation), gates, moves, NPC names, EnchantEffect, map names; `build/mu-lang` (NATIVE-LANG-001). See [the finding](../docs/research/client-lang-tables.md) |
| `tests/` | Synthetic fixtures, golden reference harnesses (models and characters), unittest suites (client-verified mesh-draw digests) |

## Game text and script tables (NATIVE-LANG-001)

`Data\Lang.mpr` stays encrypted. `mac-play/diagnostics/langread` reads the tables the client built from it out
of a running client you started (read-only, under the game lock), and `scripts/live_lang_to_plain.py` writes them
as local plaintext. Never commit that plaintext. With `MU_LANG_DIR` pointing at it, the following use the client's
own text and tables:

- mu-world, mu-client and mu-walk: GFx labels, skill names and icons, map names, combat skill distance;
- `mu-render --world-render`: EnchantEffect colours (`--glow-color` overrides them);
- mu-charsel and the shell: tips and login strings.

Without it, everything keeps its placeholder. `build/mu-lang DIR summary|text N|skill N|map W|enchant CODE [MESH]|...`
queries the tables. See [client-lang-tables.md](../docs/research/client-lang-tables.md).

## Data tables (NATIVE-DATA-001)

`make -C native build/mu-data` builds the table tool. It needs no Crypto++ or image libraries. Commands: `list [GAME_ROOT]`, `dump FILE`, `item-models FILE --json`, `model ITEM_BMD INDEX`, `decode FILE --out PATH` and `mpr Lang.mpr`. Output is local only; never commit decoded tables or text. See [the finding](../docs/research/client-data-tables.md). NATIVE-DATA-002 adds named fields to `dump`, plus `item ITEM_BMD CODE` (attributes, client max durability, bans) and `layouts` ([finding](../docs/research/client-item-attributes.md)).

## Tests

`make test` runs `native/tests`. The portable checks build everything from authored synthetic models and textures. The private checks run with `MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=...`. Set `MU_NATIVE_GOLDEN_PER_VERSION` and `MU_NATIVE_GOLDEN_MAX_VERTICES` to widen the installed golden sample. The private mesh-draw execution test needs Unicorn (`tools/requirements-lock.txt`) and the pinned evidence (`MU_CLIENT_TEXT`, `MU_IMAGE_DATA`, `MU_TRIG_FLAG`, `MU_MATH_DATA`, or the default `evidence/` paths); `MU_MESHDRAW_PER_FOLDER` widens its installed sample. Renders of installed assets stay local and are never committed.
