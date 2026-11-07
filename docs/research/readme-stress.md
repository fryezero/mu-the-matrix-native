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

The captures use FOV 65, 1600x1000, the normal game HUD, closed panels/map, fixed
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
| 26-80-players-lorencia.jpg | `7d4f91626d705d029a53c1e6f19bfbea706156ba6bd2b0113e7a6a34235bf4ae` | `eb3b1ca3533a9f0dc5ca25c8ba5f1ba6de347777c8888178254548c88a3d19d6` |
| 27-80-players-tormenta-combat.jpg | `4100c2c9cc1861b0fccefd50cd3c2ef25e80bbde473ea3e18fcceddea127d0aa` | `6b08873220070c20a0c0504595b8fa9003f842a5795d2c8bd6964c8e53630e8d` |

These are the APP-POLISH-006 re-shoots (below). The October 28 originals were
`cad4e399…` (JPEG) / `ec3bd8ef…` (PNG) and `a8386983…` / `d26946a3…`.

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

## Dark corners at FOV 65 (REGRESS-001, 2026-11-06)

The dark area left of the Lorencia bridge and in Tormenta's far-right corner is the client's own clear colour:
(10, 20, 14)/256 in Lorencia, black in Tormenta. It shows where the terrain's FOV-independent 2D cull ends. The
client never renders at FOV 65 (its largest is the world FOV, 39 here), so these corners are not something a
player can see. Both frames fill at FOV ≤ 45 (1,600×1,000, the same tiles). A later README lane should re-shoot
26/27 at `--perf-fov 45` or at the world FOV. Details are in the [REGRESS-001 handoff](../handoffs/REGRESS-001.md).
