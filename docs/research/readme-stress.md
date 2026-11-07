# Eighty-player README captures, README-STRESS-001

Two native offline images show the crowd in Lorencia and a skill fight in Tormenta
Island. No original client, launcher, account session or live state was used.

## White silhouettes: verified native texture-loading bug

The PERF-003 fixtures use armour index 9 at +11. Their base bitmaps load correctly
from Data/Player, so the earlier `textures_missing == 0` guard passes. However,
`mu_world_players.c:load_parts` passed the model directory, Data/Item, as the
explicit effect directory when retrying those bitmaps. The six chrome/glow
bitmaps live in Data/Effect. All six were absent from the retry's texture slots.

The item's high-level colour passes then reached `gl_backend.c:prepare` or
`b_prepare` with a zero texture name. Those backends disable texturing when the
requested texture is absent. The resulting additive passes saturate the armour
white in Lorencia and cyan under Tormenta's light. This is host texture loading,
not evidence of a missing special-item body recipe. The same +11 crowd fails in
immediate GL; removing the upgrades restores textured base armour.

The fix passes NULL for the fallback's effect directory, letting the existing
loader resolve Player/../Effect. No renderchar, reconstructed item decision,
shader, light, geometry, quality setting or item type was changed. The player
summary now reports `effect_textures_loaded` per slot; the stress checker rejects
missing glow textures as well as missing base textures. This finding is for the
items lane's awareness and does not reconstruct any remaining special-body rules.
Part 6 merged during this task and brings its separate coverage to 559/1,674 bodies.
The analogous ground-item fallback in `mu_items.c` is a separate consumer for
that lane to assess; this change covers the remote-player failure reported here.

A synthetic integration regression places an authored model in Data/Item, its
base textures in Data/Player, and six authored OZJ textures in Data/Effect. It
runs through the real player/session/model loader. Reinstating the old directory
makes it fail with 0 instead of 6 effect textures; the corrected loader passes.
This negative control was run after correcting the fixture's OZJ envelope.

## Controlled image hashes

Same offline Lorencia scene, 80 original PERF-003 loadouts, 1280x800, FOV 65,
frame 0, no GFx or monsters. SHA-256 below hashes PNG file bytes. Only the
fallback directory argument differs between the before and after builds, based on
b74de71 plus this lane's host changes. The publication images below were regenerated
after integrating main 9a827a4, including the item part-6 and skill-session lanes.

| Probe | Before | After |
|---|---|---|
| +11, batched GL | `8a3527e591bdf918b62781f0eb9570965731f88c908cf7731e777bfdb39064d4` | `b76c5fce8b9534c60c6196c311ed0373a2169b2c0ef911b955f2e5c734566925` |
| +11, immediate GL | `8a3527e591bdf918b62781f0eb9570965731f88c908cf7731e777bfdb39064d4` | `b76c5fce8b9534c60c6196c311ed0373a2169b2c0ef911b955f2e5c734566925` |
| +0 control, both builds | `4104828eb55312f5b4501e1e1dac19d345cb3b415e74c59d284c5caeaf21b946` | `4104828eb55312f5b4501e1e1dac19d345cb3b415e74c59d284c5caeaf21b946` |

The intended hash change restores chrome textures on upgraded armour. Batched
and immediate rendering agree on each side; the base-armour control is unchanged.
Existing README media 01-25 retain their audit pins. No new x86 routine is
reconstructed, so these are native integration checks, not new Unicorn cases.

## Capture and privacy review

`native/tools/capture_readme_stress.py` generates 80 synthetic players in eight
loadout variations across five classes, with eight nearby demo monsters. Armour
indices are 0/3/4/6/9/10, upgrades 0/3/5/7, weapons span swords, axe, bows, staffs
and mace, and wings use indices 0-4 with some wingless characters. World-coordinate
diagonal rows form a screen rectangle with short, distinct synthetic nameplates.

The captures use the world FOV (39; FOV 65 until the README-IMAGES-C re-shoot below),
1600x1000, the normal game HUD, closed panels/map, fixed
comparison movie time, synchronous GFx presentation, normal scenery and effects.
Lorencia is world 0 at 182,128, frame 0. Tormenta is world 141 at 60,50, frame 100;
the shifted tile avoids foreground pillars obscuring the crowd. This is a fight
in the arena, not a real server raid or a reconstructed boss encounter.

Both scenes admit 80/80 players and 80/80 name records; all selected armour,
weapons and wings have zero missing base textures and all six glow textures.
Each 101-frame run reports five skill events, 416 created effects and 16 joints;
the actual GFx layer renders both saved frames. These counts do not imply all
combat branches or server outcomes are reconstructed.

`MU_GFX_PUBLIC_DEMO=1` opts into authored HUD values: hero name Preview, HP max
12,000, MP max 8,000, SD max 4,000, AG max 2,000, XP range 1,000/10,000, zen
100,000 and ruud zero. The existing demo animation changes current values over
time. `--hero-name Preview` sets the overhead name independently. Normal host
and fixture defaults remain unchanged. A stub-layer regression checks the public
name and resource maxima. The combat HP argument is a separate synthetic fixture
value and never edits character or account data.

The two final JPEGs were visually reviewed at full size after encoding. They
contain only the native game image, authored short names, Preview, demo monster
names and the offline welcome line. No account names, other players' chat,
passwords, desktop chrome or private paths appear. JPEG encoding is quality 85,
4:2:0, optimized, 1600x1000, without EXIF or other source metadata. No pixels were
painted over, composited, recoloured or replaced. The exact JPEG bytes are pinned
in `scripts/audit_repository.py`.

Reproduce from the task worktree with existing local exports and its rebuilt
world and eight-patch GFx library. The output must be outside the repository:

```sh
./tools/python/bin/python native/tools/capture_readme_stress.py \
  --game-root "$MU_GAME_ROOT" --objects "$MU_OBJECTS_DIR" \
  --gfx "$MU_GFX_DIR" --lang "$MU_LANG_DIR" --out "$MU_README_OUT"
```

Since README-IMAGES-C the camera keeps the world FOV. `--fov N` sets the native-only
`--perf-fov` override; leave it out for the README images.

The script writes exact private argv/environment, PNG hashes and workload checks
to commands.json. No decoded assets or runtime inputs are published. The
committed script retains the authored scene recipe after local cleanup.

## Performance boundary

[PR #201](https://github.com/fryezero/mu-the-matrix-native/pull/201) measured
crowd80 18.37 fps, tormenta80 18.94 fps, retina80 17.58 fps and crowd40 24.90 fps
in its final shared-host repeat. See [PERF-003](native-performance-003.md) and its
[aggregate evidence](native-performance-003-summary.json). Those timings predate
this texture fix and use the original loadouts, spacing, 32 monsters and open
interface panels/map. The README rounds the two relevant historical values to
18.4 and 18.9 fps. These new composed captures are not timed; no speedup or
post-fix frame rate is inferred. The 80-player 25 fps target remains open.

## Publication media digests

| Image | JPEG SHA-256 | Native source PNG SHA-256 |
|---|---|---|
| 26-80-players-lorencia.jpg | `d4643c392b118c6bf708a30405c7763602c07496cb61225c8bc0aaf6982aa4dd` | `60037c7589972bff9d75c6e9263c2704b6f8f2cfd1901efa736f1844e5088f7f` |
| 27-80-players-tormenta-combat.jpg | `1e73af69c8ba9ffddce9dadc0f31038d8f568aa5839a09451bd879b88a02e94f` | `68215576719aae161c2f2b6fcb3e901752306b02290731244be3e4f767e0f7bd` |

These are the README-IMAGES-C re-shoots at the world FOV (end of this note). The
APP-POLISH-006 FOV-65 images were `7d4f9162…` (JPEG) / `eb3b1ca3…` (PNG) and
`4100c2c9…` / `6b088732…`. The October 28 originals were `cad4e399…` / `ec3bd8ef…`
and `a8386983…` / `d26946a3…`.

## APP-POLISH-006 re-shoot: session HUD vitals (2026-11-06)

Since APP-POLISH-002/003 (#294) the HUD shows the session hero's vitals, so the
October command's HUD read `16960/0`. The script overrode the offline join in two
ways. `--class 0` selected a Dark Wizard, a class with no recorded join data, so
the seed set no maxima. `--hero-hp 1000000` went to the combat fixture's A0/30
placement answer, whose HP field is 16 bits wide: 1,000,000 mod 65,536 = 16,960.
The script now passes neither, so the world's defaults apply: class 1, level 1,
the recorded FryeZEN2 join that `native/fixture/hero_join.h` seeds as current and
maximum (APP-POLISH-003 evidence), and combat HP 1100. Both scenes report HP
1100/1100, MP 200/200, SD 52/52 and AG 25/25 at every sampled second. The hero
(Preview, in the middle of the crowd) is therefore a Dark Knight. It casts the
same scripted skills 9/10/14/24 with the same staff stance. No stat, damage or
combat rule changed.

The script also checks the HUD now. It sets `MU_HUD_TRACE=1` and rejects any
sample whose HUD differs from the session or whose maximum is zero or below the
current value. Its glow check now requires at least six effect textures per
slot, not exactly six. Since later item lanes, some +3/+7 slots load a seventh,
and the old check refused the crowd although nothing was missing.

Same framing as before: worlds/tiles, FOV 65, 1600x1000, frames 0 and 100, the
same 80 loadouts and 8 monsters, `MU_GFX_PUBLIC_DEMO=1`. The build was this branch
merged with main `84a7f05d` (#319 RENDER-WORLDS-SLOTS3, which moves some Tormenta
particles), with Native Data APP-REFRESH-006 (read-only) and the bundled
eight-patch GFx library. Each scene: 80/80 players and name records, complete
base and glow textures, 5 skill events, 417 effects, 16 joints. JPEG quality 85,
4:2:0, optimized, no EXIF, 450 KB and 407 KB. Two runs of the Tormenta frame on one
build are byte-identical. Lorencia frame 0 differs between runs in 49 pixels of the HUD
strip only (GFx presentation timing at the first frame).

Visible differences from October that this lane did not cause:

- RENDER-TIME-003 (#258, bisected along main's merges from #205 to `71692108`)
  culls with the client's 640-unit frustum (GetScreenWidth `0x016bc355`). At this
  wide FOV, Lorencia's water and shoreline left of the bridge, and Tormenta's
  far-right corner, now fall outside the frustum and stay black. The change is
  intended; see that finding.
- Newer item and effect work changes armour and spell pixels in both scenes.

Privacy review of both encoded files at full size: only the synthetic names
(W01-F80), Preview, the demo monster names and the offline welcome line, plus
fixture HUD numbers and the public demo's 1,000/10,000 experience bar. No account
or real character names, chat, desktop chrome or paths. Nothing was painted over.
The NATIVE-PERF frame rates quoted next to the images were not re-measured and are
unchanged.

## README-IMAGES-C re-shoot: the client's world FOV (2026-11-06)

REGRESS-001 (#321) traced the dark edges of the FOV-65 images to the FOV itself.
`--perf-fov 65` is a native-only camera override (`world_tool.c`, 20..90). The
client's zoom `0x0185a9bf` picks from {20, 30, world FOV}, and the live Lorencia
globals read FOV 39.0. At 65 the view reaches past the terrain tiles that
CreateFrustrum2D `0x016d20d9` keeps, so the clear colour shows: 14.1% of the
Lorencia frame and 9.2% of the Tormenta frame in REGRESS-001's empty-scene
measurements. Both frames fill up to FOV 45.

The capture script no longer passes `--perf-fov`; both scenes report `fov 39.000`
(`world_fov 39.000`). FOV 45 was also shot from the same build. It fills both
frames too, but it still leaves the crowd's corner players out of frame. The extra
6 degrees would cost faithfulness for little framing gain, so the images use 39.
Everything else is unchanged: tiles, frames 0 and 100, the 80 loadouts and 8
monsters, the recorded Dark Knight HUD (1100/1100, 200/200, 52/52, 25/25),
`MU_GFX_PUBLIC_DEMO=1`, `MU_GFX_TEST_CLOCK=1`, headless GL, window-only. Inputs were
Native Data APP-REFRESH-006 (read-only) and the bundled eight-patch GFx library
(`MU_GFX_LIB`). Each scene has 80/80 players and name records, complete base and
glow textures, 5 skill events, 417 effects and 16 joints. The build was main
`3ecc205c` plus this lane's script change.

| Source PNG, 1600x1000 | Lorencia clear colour (10,20,14) | Tormenta pure black |
|---|---|---|
| FOV 65, empty scene (REGRESS-001) | 225,308 (14.1%) | 146,776 (9.2%) |
| FOV 39, README frame (this re-shoot) | 0 | 120,501 (7.5%), all crowd shadows |
| FOV 45, same crowd (not published) | 0 | 107,261 (6.7%), all crowd shadows |

Tormenta's clear colour is black, the same value as the projected player shadows.
A mask of the black pixels shows wing- and body-shaped shadow polygons inside the
crowd only. The top of the frame has none and no edge region is uncovered. Without
players, REGRESS-001 counted 1,281 black model pixels at FOV 39 on this tile (frame 0).

The JPEGs use quality 85, 4:2:0, optimized, no EXIF: 565 KB (26) and 532 KB (27).
The narrower view has more detail per pixel, so the files are larger than the FOV-65
images' 450/407 KB. Privacy review of both encoded files at full size, in quadrant
crops: only the synthetic names W01-F80, Preview, the demo monster names (Bull
Fighter, Hound, Budge Dragon, Spider), the offline welcome line (Tormenta), the
fixture HUD and the public demo's 1,000/10,000 experience bar. No account or real
character name, chat, desktop chrome or path. Nothing was painted over.

The NATIVE-PERF-004 rates quoted next to the images were measured by
`bench_stress.py`, which still uses `--perf-fov 65`. They were not re-measured and
apply to that benchmark view, not to these FOV-39 frames.
