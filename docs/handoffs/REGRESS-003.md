# REGRESS-003: grey ground patches in mu-world frames (README-IMAGES-D finding 1)

Claude Opus 5.5 lane, 2026-11-07. Branch `claude/regress-003`, worktree `~/Documents/MTM/worktrees/regress-003`, from
main `f7975115` (#345). Offline only: no original client, launcher, live read, account or network. The installed apps
were not touched.

## Verdict

Not a GL state leak, and not a regression. **mu-world wrote the framebuffer's alpha channel into its frame PNGs.** The
terrain's alpha-mapped layer 2, the grass sprites and other blended draws (`SRC_ALPHA, ONE_MINUS_SRC_ALPHA` also
blends the destination alpha) leave alpha below 1 in the framebuffer. The window shows only the colour channels,
so the game looked right (inference: SDL's Cocoa GL view is opaque by default; not checked in the live app). But a viewer that composites the RGBA PNG over a light background (Preview,
browsers, image tools) shows those pixels as flat light-grey polygons over the terrain and grey grass. The colour
channels were always correct, on both backends. It has never worked: main's October 22 build `024e9496` (#158) gives
the same alpha (234,960 GL / 235,226 soft pixels below 0xff at Lorencia 138,123, 1280×800, identical to `f7975115`).
`git bisect` has no good end, so it was not run.

mu-client's frame captures and its PrintScreen/O screenshot (`mu-client-screenshot.png`) had the same defect. In a
headless `--auto` run, every one of the 20 captures had 2,511 to 21,130 pixels below 0xff.

## Reproduction (verified)

README-IMAGES-D's command (research note `readme-refresh.md`, 08 command plus `--npc --npc-demo
native/world/lorencia-demo-npc.txt --npc-script 50:tipinv:0`, players file without Aeris's `party` flag), GL
1280×800, frames 0 and 60:

| Variant | Frame 60 pixels with alpha < 0xff |
|---|---|
| players without `party` (the finding) | 210,535 |
| shipped players file (party list open) | 207,539 |
| without `--npc-script` (no tooltip) | 211,399 |
| without `--npc` (and its script) | 226,015 |
| without `--gfx`, `--gfx-open` and the tooltip (frame 0) | 259,040 |
| minimal: `--tile 138,123` only, frame 0, GL / soft | 234,960 / 235,226 |

Every variant has the patches. The finding's "not with the shipped players file / without `--npc` / without the
tooltip" was a viewing difference, not a rendering one: the alpha is in all of them. The frame RGB flattened
(`convert('RGB')`) shows green grass and no grey polygons. The alpha channel alone is exactly the patch shapes: the
layer-2 terrain areas, the grass, the wing and cloth edges, the chat box and the shadows. README image 08 was
flattened by its compose step and is clean. All committed README PNGs are opaque (alpha extrema 255/255).

Ruled out on the way: the JPEG decode (TileGrass01.OZJ decodes green, mean 77/68/16), the game data (World1 files
identical in all four local copies), the environment (an `env -i` run gives the same bytes), and GFx (no `--gfx` is
the same).

## Fix

- `native/core/mu_png.c/.h`: `mu_png_write_opaque()` writes the same RGBA PNG (same layout, filter 0, stored
  deflate) with every alpha byte 0xff. `mu_png_write()` is unchanged and keeps alpha for the model, effect, UI and
  sprite tools that want it.
- `native/world/world_tool.c` (mu-world and mu-walk frame saves) and `native/client/main.c` (`write_png` frame captures
  and the PrintScreen/O screenshot) use it.
- The frame reports' `sha256` still hashes the raw RGBA readback, unchanged. Pinned frame hashes, `--time-series` samples,
  perf baselines (`MU_PERF_*_BASELINE`) and `MU_PERF_HASH_ONLY` runs see no difference.

No client reference applies: the client's window and its screenshot (JPEG from the back buffer) carry no alpha. The
native GL state wrappers (`mu_gl_*`) and blend state are untouched, so every frame's colour is byte-identical.

## Regression test

`native/tests/test_native_capture_alpha.py`:

- portable: the open world of `test_native_world.py` with a 24×24 layer-2 patch at alpha 128 under the hero, 320×200.
  The soft frame (mu-walk) and the headless GL frame (mu-world) must be fully opaque. The report hash must differ from
  the PNG's (the raw alpha was below 1, so the scene exercises the defect), and the colour must differ from the same
  view without the patch. Two runs must write the same file. **Before the fix both fail: 1,587 of 64,000 pixels
  opaque.**
- private (`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`, `MU_NATIVE_DATA_DIR`, `MU_GFX_LIB`): the README-IMAGES-D
  scene above, GL and soft, frame 60 opaque.

## Software raster backend

Affected the same way: `--backend soft` frames had the same alpha (235,226 px at the minimal view; 247,377 at the
scene's frame 0). After the fix, soft frames are opaque with byte-identical RGB.

## Byte identity

- October 22 tour (14 views): 28/28 PNG RGB byte-identical; 28/28 had alpha below 0xff before and are opaque after; 28/28
  OBJECT + light dumps and 14/14 frame reports (with `sha256`) byte-identical (binary path normalised). The PNG file
  bytes differ by design (alpha). Wall 21 s before / 18 s after.
- DATA-ACQ-002 (32 views): 64/64 PNG RGB identical, 64/64 opaque after, 64/64 dumps and 32/32 reports identical. Wall
  43 / 48 s.
- The failing scene: frame 60's RGB identical to before, report `sha256` identical (`55023c9f…`), alpha now 0xff
  everywhere.
- mu-client `--auto` headless run (640×400, 400 frames, every 100): 20/20 captures RGB identical, opaque after.
- README images: no change (none touched; they were flattened).

## Findings for other lanes

1. **Frame 0 of the GFx scene is not run-to-run stable.** Two runs of the same binary give different frame-0 report
   hashes (`a0fa9ed7…` / `28a541a4…`): 35 pixels in the bottom HUD (x 344..843, y 723..799). Frame 60 is stable.
   This was not investigated; it looks like the first GFx frame's timing.
2. Other window capture paths still write alpha: `mu-charsel` (`charsel_tool.c` frames and screenshot),
   `native/frame/main.c`, the GFx window screenshot (`mu_gfx_window.c`), and the viewer screenshots. They now have
   `mu_png_write_opaque` available. They were left alone to keep this change to the world and the app.

## Checks

The PR body lists them with counts and wall times. Steward validators: the 14 rows `--list-affected origin/main`
selects (symbol level, 2 kept by fallback), run without mutants at `db18e665`.

## Cleanup

Scratch (`~/Documents/MTM/mu-mac-tools/native/scratch/regress-003`), renders and this worktree's build dirs are deleted
after the ready line. Only `scratch/regress-003/regress-003-before-after.jpg` (146 KB, the PR's crop: before
composited over white | after) is kept until the steward merges. No later lane needs an input from this lane.
