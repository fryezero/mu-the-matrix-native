# Model viewer

`mu-viewer MODEL.bmd` loads a client BMD model with its textures, animates it with the reconstructed tick and
pose builder, skins it on the CPU and draws it with the ported mesh draw. Headless it renders one frame to a
PNG and prints the frame's SHA-256; `--compare` renders the other backend as well and reports how many
pixels differ. `mu-render info MODEL.bmd` prints the parsed layout.

## Sub-features

- `model-info` the layout: version, meshes, bones, actions, textures, anomalies.
- `model-render` a GL render of the textured synthetic model that is not a flat background.
- `model-compare` GL and software renders agree within the project's threshold.
- `model-view` a yaw change changes the image.
- `model-pose` another action and frame changes the image.

## How to get to it (user POV)

- `mu-viewer MODEL.bmd` opens the window: left drag orbits, right drag pans, wheel zooms, Space plays,
  Left/Right change the action, N/P the next model in the folder, O saves a screenshot, Esc quits.
- `mu-viewer MODEL.bmd --headless --backend gl|soft --out PNG [--compare] [view options]` renders one frame.
- `mu-render info MODEL.bmd` prints the layout; `mu-render` with no arguments lists every option.

## Driving it with run-tool.sh

Preconditions:

- `RUN` from `new-run.sh`, `doctor.sh "$RUN"` OK, `V` set, `M="$RUN/root/Data/Verify/synthetic1_v12.bmd"`.

- **Layout.** Run `$V/run-tool.sh "$RUN" model-info mu-render info "$M"`. Exit 0; the JSON has `"version": 12`,
  `"meshes": 3`, `"bones": 7`, `"actions": 3`, textures `skin.tga`, `cloth.tga`, `metal.tga`, `"strict_anomalies": 0`
  and one `parent-forward` anomaly (bone 2's parent is bone 5, by design of the fixture).
- **Render and compare.** Run `$V/run-tool.sh "$RUN" model mu-viewer "$M" --headless --backend gl --compare --width 320 --height 240 --out "$RUN/proof/model.png"`.
  Exit 0; stderr names the GL renderer; stdout is one row with `backend gl`, the GL `sha256`, `other_sha256`
  (software), `differing_pixels`, `pixels_over_8` below 384 (320 x 240 / 200, the `native/tests` threshold) and
  `mean_channel_diff` below 1.0. At the sync commit: 19 differing pixels, 8 over 8/255.
- **View change.** Run `$V/run-tool.sh "$RUN" model-yaw mu-viewer "$M" --headless --backend soft --width 160 --height 120 --yaw 90`
  and `$V/run-tool.sh "$RUN" model-front mu-viewer "$M" --headless --backend soft --width 160 --height 120`.
  The two `sha256` values differ. At the sync commit the front render is
  `ba54598e0f11415ddfa16e812f98d0c16b9f7aa14a5f7b09429e4d6bcf829c99` and the yaw-90 render
  `a7959d5db84f17b87900886ae24f7219b341a7c551874acf258128372532c44c` (software hashes are host-independent).
- **Pose change.** Run `$V/run-tool.sh "$RUN" model-pose mu-viewer "$M" --headless --backend soft --width 160 --height 120 --action 1 --frame 1`.
  Its `sha256` differs from the front render (at the sync commit `3abb98e6aed044db082a410e600018c73edf2d54fb1b6da0c48707507d7e0fd2`).
- **Proof.** Open `proof/model.png`: striped, multicoloured triangles on a dark blue-grey background, not a
  flat colour. Keep the four stdout rows.

## Gotchas

- `Player.bmd` alone has no meshes: its render is a flat background and proves nothing about drawing.
- Synthetic textures are seeded noise, so meshes look striped; that is the fixture.
- stderr says `1 value(s) outside the strict BMD semantics, drawn as the client reads them`: the fixture's
  forward parent, expected.
- `--frame F` alone with action 0 does not change this fixture's image; use `--action 1 --frame 1`.
- GL hashes depend on the GPU and driver; only software (`--backend soft`) hashes are comparable across Macs.
- `--compare` differences come from rasterization rules, not geometry; a jump in `pixels_over_8` past the
  threshold is the signal, a handful of edge pixels is normal.
