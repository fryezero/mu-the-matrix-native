# Terrain view

`mu-viewer --terrain ROOT --world N` draws a world's terrain (height map, tile layers, light map, the
client's per-tile GL stream) with the client camera. Headless it renders one frame to a PNG and prints its
SHA-256; `--compare` also renders the software rasterizer and counts the pixels that differ.

## Sub-features

- `terrain-render` a GL render of world 0 of the synthetic root.
- `terrain-compare` GL and software agree within the project's terrain threshold.
- `terrain-missing` a world the root lacks fails clearly instead of drawing something.

## How to get to it (user POV)

- `mu-viewer --terrain ROOT --world N` opens the window: drag to look around, G toggles wireframe,
  O saves a screenshot, Esc quits.
- `mu-viewer --terrain ROOT --world N --headless --backend gl|soft --out PNG [--compare]` renders one frame.

## Driving it with run-tool.sh

Preconditions:

- `RUN` from `new-run.sh`, `doctor.sh "$RUN"` OK, `V` set.

- **Render and compare.** Run `$V/run-tool.sh "$RUN" terrain mu-viewer --terrain "$RUN/root" --world 0 --headless --backend gl --compare --width 320 --height 200 --out "$RUN/proof/terrain.png"`.
  Exit 0; stderr names the GL renderer; stdout is one row with `backend gl`, `sha256`, `pixels_over_8` and
  `pixels` 64000; `pixels_over_8` is below 10 % of `pixels` (the `native/tests` terrain threshold). At the sync
  commit 3960 pixels (6.2 %) differed.
- **Missing world.** Run `$V/run-tool.sh "$RUN" terrain-missing mu-viewer --terrain "$RUN/root" --world 1 --headless --backend gl`.
  Exit 1 and stderr `.../Data/World2/EncTerrain2.map: missing or undecodable`; no PNG.
- **Proof.** Open `proof/terrain.png`: the whole frame is noise-textured ground seen from the client camera
  angle (-48.5 degrees), no black regions. Keep the stdout row.

## Gotchas

- `--world N` loads `Data/World{N+1}`: the synthetic World1 is `--world 0`.
- The synthetic tiles are seeded noise, so the ground looks like coloured static; a black frame or a flat
  colour would be the anomaly.
- Default size is 1280 x 800 and the PNG is about 4 MB; pass `--width --height` for quick runs.
- Lights, decals, objects and water animation need `--lights`, `--frustum`, `--objects` options and data the
  synthetic root does not have; they are not part of this recipe.
