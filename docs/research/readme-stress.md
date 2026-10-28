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
items lane's awareness and does not claim any of its 1,173 remaining body types.
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
fallback directory argument differs between the before and after builds.

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
| 26-80-players-lorencia.jpg | `2c3d30185b21df1bb5d68989acbfb39d609cfc52d9f0427b53d63cc7a2260763` | `e4ba7038dc2e125b5ebddcee0fea6ddb44539aca152c99017fc59beb29d99c9b` |
| 27-80-players-tormenta-combat.jpg | `96ef090d054614cdff27d7e2fea8931fa2582b45fd0c551663760f029be4fd1d` | `13e457c1c9cde2290dcea280037b13d8528d8455c4b484e0f0097fab33f564a3` |
