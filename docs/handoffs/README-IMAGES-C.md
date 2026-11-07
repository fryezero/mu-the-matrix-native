# README-IMAGES-C: README 26/27 at the client's world FOV

Claude Opus 5.5 lane, 2026-11-06. Branch `claude/readme-images-c`, worktree `~/Documents/MTM/worktrees/readme-images-c`,
from main `3ecc205c` (#320). Offline only: no original client, launcher, live read, account, network or protection work.
The installed Native Preview, the Wine play app and the staged Wine app were not touched. Docs/media plus the capture
script's camera default; no renderer, world or HUD code changed.

## Why

REGRESS-001 (#321) found that the dark "black water" at the edges of README images 26 and 27 comes from the capture's
`--perf-fov 65`. That is a native-only camera override. The client's zoom `0x0185a9bf` picks from {20, 30, world FOV},
and the live Lorencia capture reads FOV 39.0. At 65 the view reaches past the terrain tiles that CreateFrustrum2D
`0x016d20d9` keeps, so the clear colour shows on 14.1% (Lorencia) and 9.2% (Tormenta) of the frame. Both frames fill
completely up to FOV 45.

## What changed

- `native/tools/capture_readme_stress.py` no longer passes `--perf-fov`, so the camera keeps the world FOV. An optional
  `--fov N` passes the override for comparisons. `test_app_polish6` checks both.
- README images 26 and 27 were re-shot at the world FOV, **39** (both scenes report `fov 39.000`). FOV 45 was shot too.
  It also fills both frames, but the crowd's corner players still stand past the frame edge. So 45 would trade the
  client's actual view for little framing gain, and 39 is the faithful choice.
- Same tiles (Lorencia 182,128 frame 0; Tormenta 60,50 frame 100), the same 80 loadouts and 8 monsters, the same HUD
  (recorded Dark Knight join, 1100/1100, 200/200, 52/52, 25/25), `MU_GFX_PUBLIC_DEMO=1`, 1600×1000. JPEG quality 85,
  4:2:0, optimized, no EXIF: 565 KB and 532 KB.
- Audit pins, the README caption (it names FOV 39 and the cropped corners) and the [finding](../research/readme-stress.md)
  (digests, method, measurements) are updated.

## Before / after

| Source PNG | Lorencia clear colour (10,20,14) | Tormenta pure black |
|---|---|---|
| Before: FOV 65 (REGRESS-001, empty scene) | 225,308 (14.1%) | 146,776 (9.2%) |
| After: FOV 39, README frames | 0 | 120,501 (7.5%), crowd shadows only |

Tormenta clears to black, and the projected player shadows are black too. A mask of the black pixels shows only
shadow polygons inside the crowd: none at the top of the frame and no uncovered edge region. Visually, the left of the
Lorencia bridge and Tormenta's far-right corner no longer show the dark field. The view is closer, so the crowd fills
the frame.

## Frame rates

The NATIVE-PERF-004 rates quoted next to the images (crowd80 23.2/20.2, tormenta80 24.8/20.8 fps) come from
`bench_stress.py`, which still uses `--perf-fov 65`. They were not re-measured. The README now says that they apply to
the benchmark's FOV 65, not to these FOV-39 screenshots.

## Privacy review

Both encoded JPEGs were read at full size in quadrant crops. They show only the synthetic names W01–F80, Preview, the
demo monster names (Bull Fighter, Hound, Budge Dragon, Spider), the offline welcome line (Tormenta), the fixture HUD
and the public demo's 1,000/10,000 experience bar. No account or real character name, chat, desktop chrome or path.
Nothing was painted over.

## Checks

Listed with wall times in the PR body. Steward validators: none (docs/media, rule 6c). The stress tests ran because the
capture script changed.

## Cleanup

After the ready line, the scratch folder `native/scratch/readme-images-c` (FOV 39/45 captures, masks, crops, build log)
and this worktree's `native/build` are deleted. No local input needs keeping.
