# Native client frame time (NATIVE-PERF-001)

The native preview (`mu-client`, NATIVE-APP-001) was reported at about 22 fps on the Apple M5, below the client's
own 25 fps logic and frame cap, while the Wine-run client holds 25 fps on the same Mac. This milestone profiled the
native client in its real scenes, removed the costs that were the native port's own (not the client's), and made the
window resizable with a macOS full-screen mode. It is a rendering and host milestone: no reconstructed routine, and
no GL call stream that was compared with the client, changed, so there is no new Unicorn comparison. The evidence is
pixel comparisons (before/after renders identical or within a stated tolerance) and frame-time logs.

## Method

- `--perf FILE` (mu-client, mu-world; `native/core/mu_perf.*`) logs one line per frame with the phase times: events,
  logic (the scene's due logic steps, camera, terrain frame, effect update), terrain, objects, characters (hero and
  actors with shadows), items, env, particles, effects, labels, scene (the login or character-select 3D pass), gfx
  (the GFx layer), overlay (the 2D layer), present, swap, sleep (the client's cap). `--perf-sync` waits for the GPU at
  each phase end (diagnostic). `native/tools/perf_report.py` gives fps and frame/work percentiles (work = frame time
  without the cap's sleep).
- `mu-client --auto --hold SCENE` plays the offline flow in the window (as headless `--auto`) and stays in the scene:
  3 login (server list), 5 character select (GFx list), 6 world. Worlds: the demo session (Lorencia 140,130 with
  the demo monsters, players and NPCs), and local sessions joining Tormenta Island (world 141) at 135,10 and 50,46;
  objects from the local decoded files, combat/items/NPC demo, names, environment, particles, sound, GFx: the preview
  app's command line.
- CPU profiles with `sample` on busy headless runs (3456 × 2160, every frame drawn); window runs on the Mac's display
  (one external 1920 × 1080 screen, backing scale 1: 1280 × 800 and 1728 × 1080 windows, macOS full screen
  1920 × 1080). No Retina display is attached, so "Retina full screen" is measured as headless GL work at
  3456 × 2160 (the 16-inch MacBook Pro's full-screen backing size) plus the window runs' present/swap cost.
- `MU_PERF_BASELINE=1` runs the code paths from before this milestone (plain sleep at the cap, the software 2D layer
  over a read-back frame, immediate-mode draws), so before and after are the same binary on the same machine.
- Pixel checks: `native/tools/imgdiff.py` over headless captures (RGB compared, framebuffer alpha ignored).

## What the profile showed

At 1504 × 936 (the app's window) Lorencia's frame work was about 14 ms, inside the 40 ms cap; the measured windowed
rate was 25.0 fps in the world. The "22 fps" came from three things:

1. The window title averaged frames over the whole run, loading included (484 frames in 22 s).
2. The login, title and loading scenes use the client's cap `Sleep(40 - elapsed)` (`0x0185267a`), which does not
   compensate an oversleep; SDL_Delay on macOS overslept by 1-2 ms (timer coalescing; up to 10 ms when the window is
   in the background), so the login ran at 23.9 fps with frames of 42 ms. The world and character-select caps
   measure render start to render start and caught up on average, with 30 % of frames above 40 ms.
3. The costs that grow with the window: every frame mu-client waited for the GPU (`glFinish`), read the whole frame
   back (`glReadPixels`), flipped and copied it twice in memory, drew the 2D layer in software over it (in character
   select also the GFx character list, blended on the CPU) and uploaded it again as a texture. At 3456 × 2160 that
   was 8 ms in the world and 19-24 ms in character select per frame.

The CPU profile of a busy Retina-sized world frame (main thread, before): terrain 24 % (almost all inside
`glBegin`/`glEnd`: each tile is a Metal draw with its own state validation in Apple's GL), objects and characters
17 % in the mesh draw and its GL calls plus 8 % posing the objects (`mu_model_transform_all`), the read-back path 30 %,
the GFx layer 11 % (Ruffle's frame advance and render), the scene logic 5.5 %.

## Changes (rendering and host only)

- **The 2D layer on the GPU** (`native/viewer/ui_gl.c`). The reconstructed 2D routines (`reconstructed/ui`) emit
  their GL calls through a sink. The software raster (`core/mu_ui_raster.c`) stays the reference and the headless
  default; mu-client's window now replays the same calls on GL over the 3D frame still in the framebuffer, with the
  raster's semantics (tracked state applied per primitive, quads and fans split like the raster, depth and fog
  without effect, MODULATE, alpha test GREATER 0.25, mipmap filters as the base level, the raster's per-triangle
  choice between the magnification and minification filter instead of GL's per-pixel one, RGB/short texture data
  converted like the raster, colour-only clear). A texture re-uploaded while an earlier draw of the frame still reads
  it (the client re-uploads its font texture for every string) goes to a fresh texture name; re-specifying it made
  the driver wait for the GPU. The GFx character list renders into an IOSurface (mugfx shared rendering) sampled in
  place. Headless `--gpu-overlay` runs the same path for comparisons; `--cpu-overlay` restores the old one.
- **Draw batching** (`native/viewer/gl_batch.c`). The terrain tile renderer and the mesh draw keep emitting the
  client's call stream; the batch between them and GL drops state calls that change nothing (the mesh draw
  re-applies the whole state before every mesh), collects consecutive primitives with the same state, texture and
  mode (immediate mode's current colour and texture coordinate kept per vertex) and draws them with one
  `glDrawArrays` (triangles, quads) or `glMultiDrawArrays` (the same fans), in the same order. Used for the terrain,
  objects and characters in mu-world/mu-client, the login world and character select. `MU_NO_GL_BATCH=1` turns it
  off.
- **The cap's Sleep** (`mu_sleep_ms`): the thread takes the time-constraint (real-time) policy for the sleep only and
  returns to the standard policy before any game work; measured wake error 0.003-0.009 ms (nanosleep alone: 1-10 ms).
  The shell's audio stream update moved before the cap measures the pass, and the frame starts before the event
  pump, so `Sleep(40 - elapsed)` covers the whole pass as in the client's idle loop.
- The title shows the rate of the last 25 frames.

Not changed: the reconstructed routines, their arithmetic and their GL streams; what each scene draws; the GFx
layer's own rendering (Ruffle). Object posing stays per frame (a pose cache keyed on the posing inputs would save
about 2 ms in Tormenta's dense areas; not needed for the target).

## Pixel checks

| Comparison | Scenes | Result |
|---|---|---|
| batch vs immediate (mu-world headless GL, 1280 × 800, frames 0/20/40/60) | Lorencia (demo placement, combat, items), Tormenta 135,10, Tormenta 50,46 | 12/12 identical |
| batch vs immediate (mu-client flow, no GFx, 1280 × 800, every 10th frame) | title, login, character select, loading, world, back | 32/32 identical |
| GPU vs software 2D layer (mu-client flow with GFx, 1280 × 800, every 25th frame) | title frames, loading | max delta 1 (rounding) |
| | login (overlay, server list) | 4,719 px differ, max 19; 7 px (0.0007 %) above 2 (bilinear sampling) |
| | character select (window list, GFx list, label) | ≤ 2 except one 14-px column at a quad edge (0.0014 %) |
| | world (label over 3D and GFx) | identical |

With GFx on, two runs of the same build already differ in a 13-14 px column of the HUD (frame 80/90 of the flow:
Ruffle's timing), so the GFx comparisons above are between runs of the same flow and the identical-image checks run
without GFx. Tolerance used by the tests: at most 0.05 % of the pixels above a channel delta of 2. Observation (synthetic stream
of `perf_gl_host.c`): the software raster covers some pixels on the shared diagonal of a blended quad twice and blends
them twice, GL once; the remaining larger single-pixel differences at quad edges (the character-select column, the
login pixels) are of this kind or of the edge rule, and GL's result is the one the client's own GL draws.

## Frame times

Window runs, everything on (GFx, combat/items/NPC demo, names, environment, particles, objects, sound) unless
`nogfx`; `--auto --hold SCENE`, 14 s (login), 18 s (character select), 28 s (worlds), the first 25 frames of the
scene dropped (loading). Work = frame time without the cap's sleep. The 1728 × 1080 window is clamped by macOS to a
1728 × 1018 drawable on the 1080-line display; `full` is macOS full screen, 1920 × 1080. Before = `MU_PERF_BASELINE=1`
(same binary). Logs: `renders/perf/matrix/`.

| run | before fps | before frame p50/p95/p99 ms | before work p50/p95/p99 ms | after fps | after frame p50/p95/p99 ms | after work p50/p95/p99 ms |
|---|---:|---|---|---:|---|---|
| charsel-1280x800 | 25.0 | 40.1/43.5/45.5 | 16.5/20.0/21.2 | 25.0 | 40.0/41.6/43.6 | 13.9/15.1/15.9 |
| charsel-1728x1080 | 25.0 | 40.0/42.9/44.9 | 18.0/20.7/22.0 | 25.0 | 40.0/41.4/42.9 | 15.0/16.2/17.1 |
| charsel-full-nogfx | 25.0 | 39.9/42.3/43.2 | 15.7/17.3/17.7 | 25.0 | 39.9/42.2/43.2 | 14.7/16.0/16.3 |
| charsel-full | 25.0 | 40.0/42.3/43.2 | 18.4/20.8/21.4 | 25.0 | 40.1/41.1/42.6 | 15.4/16.2/16.7 |
| login-1280x800 | 23.9 | 41.9/42.8/42.9 | 17.9/19.0/20.6 | 25.0 | 40.0/40.7/40.8 | 12.6/14.1/16.2 |
| login-1728x1080 | 24.0 | 41.8/42.7/42.8 | 18.6/19.9/21.1 | 25.0 | 40.0/40.7/40.9 | 12.7/14.4/15.7 |
| login-full | 23.9 | 42.0/42.6/42.9 | 19.1/19.6/19.9 | 25.0 | 39.9/40.8/40.9 | 12.8/14.2/15.1 |
| lorencia-1280x800 | 25.0 | 40.1/42.6/44.3 | 12.3/15.2/16.3 | 25.0 | 40.1/43.7/45.9 | 10.1/13.6/15.4 |
| lorencia-1728x1080 | 25.0 | 39.9/43.0/44.0 | 13.8/16.9/17.7 | 25.0 | 39.8/43.0/44.2 | 9.7/13.0/14.2 |
| lorencia-full-nogfx | 25.0 | 39.9/41.1/42.1 | 13.9/14.1/14.6 | 25.0 | 40.0/42.0/42.8 | 11.3/12.6/12.9 |
| lorencia-full | 25.0 | 40.1/42.5/43.9 | 15.3/17.6/18.9 | 25.0 | 40.1/42.5/43.9 | 10.2/13.2/14.6 |
| tormenta-135-10-1280x800 | 25.0 | 40.1/44.6/46.7 | 12.6/15.5/17.2 | 25.0 | 40.1/44.0/45.7 | 10.6/14.1/15.8 |
| tormenta-135-10-1728x1080 | 25.0 | 40.0/43.3/45.1 | 12.0/15.3/17.4 | 25.0 | 40.0/43.8/45.5 | 11.0/13.5/15.8 |
| tormenta-135-10-full | 25.0 | 39.9/42.4/44.0 | 12.9/15.1/16.2 | 25.0 | 40.1/43.6/44.9 | 10.7/13.3/14.9 |
| tormenta-50-46-1280x800 | 25.0 | 40.1/42.7/44.0 | 12.3/15.1/16.1 | 25.0 | 40.0/43.8/45.8 | 9.5/13.4/15.9 |
| tormenta-50-46-1728x1080 | 25.0 | 40.1/42.7/44.6 | 14.2/16.8/18.0 | 25.0 | 40.1/43.2/44.2 | 10.1/13.3/14.2 |
| tormenta-50-46-full-nogfx | 25.0 | 39.9/41.5/42.4 | 13.5/14.0/14.2 | 25.0 | 39.9/42.5/43.8 | 11.4/13.1/13.6 |
| tormenta-50-46-full | 25.0 | 40.1/42.1/43.9 | 14.9/16.8/18.4 | 25.0 | 39.9/42.3/44.2 | 10.7/13.3/14.4 |

Every scene now runs at 25.0 fps (the login went from 23.9 to 25.0); frame work p95 went from 15.1-20.8 ms to
12.6-16.2 ms, p99 at most 17.1 ms: more than half of the 40 ms frame is free in every scene and size. The worlds' frame
p95 of 42-44 ms is the client's own cap: it measures whole milliseconds from render start to render start and
sleeps `40 - elapsed`, so a 41 ms frame is followed by a 39 ms one (the mean stays at exactly 40 ms).

Retina full-screen size, headless GL at 3456 × 2160 (every frame drawn, no cap, 260 frames, first 25 of the scene
dropped; the window adds the swap, 0.25-0.3 ms in the full-screen runs). Logs:
`renders/perf/retina/`.

| run | before fps | before frame p50/p95/p99 ms | before work p50/p95/p99 ms | after fps | after frame p50/p95/p99 ms | after work p50/p95/p99 ms |
|---|---:|---|---|---:|---|---|
| charsel-3456x2160 | 42.2 | 23.5/25.7/26.8 | 23.5/25.7/26.8 | 132.6 | 7.4/8.1/8.4 | 7.4/8.1/8.4 |
| login-3456x2160 | 47.6 | 21.0/21.4/21.6 | 21.0/21.4/21.6 | 173.3 | 5.8/6.1/6.5 | 5.8/6.1/6.5 |
| lorencia-3456x2160 | 45.8 | 21.6/24.3/25.7 | 21.6/24.3/25.7 | 76.0 | 13.1/14.8/16.4 | 13.1/14.8/16.4 |
| tormenta-135-10-3456x2160 | 52.3 | 19.1/21.4/22.5 | 19.1/21.4/22.5 | 80.6 | 12.3/14.1/15.5 | 12.3/14.1/15.5 |
| tormenta-50-46-3456x2160 | 47.2 | 21.0/23.4/24.7 | 21.0/23.4/24.7 | 68.6 | 14.5/16.9/17.7 | 14.5/16.9/17.7 |

Phases at 3456 × 2160 (mean/p95 ms), Lorencia before → after: terrain 4.91/5.01 → 3.53/3.68, objects 4.56/4.65 →
4.56/4.80, characters 1.13 → 1.18, GFx 2.45/4.46 → 2.49/4.43, overlay 7.48/8.43 → 0.09/0.11, logic 1.09 → 1.10.
Character select: overlay 18.75/20.69 → 3.24/3.82, scene 4.49 → 3.87. The heaviest Retina-size frame after the
changes (Tormenta 50,46) needs 17.7 ms at p99, against 24.7 ms before; with the GPU 2D layer the work no longer grows
with the pixel count except for the GFx movies.

## Window

The window is resizable (minimum 640 × 480) and has macOS full screen (green button, Ctrl-Cmd-F, `--fullscreen`, the
app's "Full screen" window size; SDL's Spaces full screen). On a size change mu-client resizes its drawable, the shell's
2D layer takes the client's values for the new size (window size and screen rates `0x01cf1624/8`, `0x06fbcd94/8`;
the GDI fonts chosen by window width; the text DIB), places the server window again and creates the
character-select window again (CUIMng::CreateCharacterScene placement), and the login, character-select and world
views take the new size. The GFx layer resizes every movie's stage and runs the client's window placement again
(SetWindowSize, SetAlign; SetScale(83) below 700 points of height, and back to 100 above — the client sets it only once,
at creation). The GFx character list keeps its right-edge placement (the movie places it once, from the stage it
starts with). Checked with window scripts (`resize:W,H`, `fullscreen`, `shot:NAME`) in the login, character select
and Lorencia: 1280 × 800 → 900 × 600 → 1500 × 950 → full screen 1920 × 1080 → back (captures local under
`renders/perf/resize-*`).

The preview app's launcher sets `MU_EXIT_WITH_PARENT=1`; mu-client checks its parent every frame and quits when the
launcher is gone (tested: launcher-like parent killed with SIGKILL, the client exits within 0.5 s with status 0).

## Checks

`native/tests/test_native_perf.py`: report and image tools on synthetic data; `perf_gl_host.c` (offscreen GL):
a synthetic 2D stream through the raster and the GPU replay (max delta ≤ 2), a terrain/mesh stream immediate vs
batched (identical, fewer draws, fewer applied state calls); mu-client headless over the synthetic tree (GPU overlay
within tolerance in title, login, character select and world; batching identical; one perf line per frame); private:
Lorencia batch identity and the demo flow's overlay tolerance over the installed client. `test_native_app.py`
checks `MU_EXIT_WITH_PARENT` and the full-screen setting.

## Limits and next steps

- No Retina display was attached: the Retina numbers are headless work at 3456 × 2160 plus the measured present cost,
  not a Retina window run.
- The GFx layer (Ruffle) is now the largest single phase in the world (2.5 ms mean, 4.5-5 ms p95).
- Object posing per frame (about 2 ms in Tormenta at 50,46) could be cached per object while its posing inputs do
  not change.
- mu-world's own window (a developer tool) keeps a fixed size.
