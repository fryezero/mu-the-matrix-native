# APP-POLISH-006: crowd HUD vitals, demo durability, quest-capture command, README 26/27

Claude Opus 5.5 lane, 2026-11-06. Branch `claude/app-polish-006`, worktree `~/Documents/MTM/worktrees/app-polish-006`,
from main `71692108` (after #317/#318, steward batch 56). Offline only: no original client, launcher, live read,
account, network or protection work. The installed Native Preview, the Wine play app and the staged Wine app were
not touched. No stat, damage, combat or power change: fixture data and a host setter only.

## 1. Crowd HUD maxima

Cause. `native/tools/capture_readme_stress.py` (README-STRESS-001) passed `--class 0 --hero-hp 1000000`. Since
APP-POLISH-002/003 (#294) the HUD shows the session hero's vitals. Class 0 has no recorded join data, so the seed
set no maxima (`fixture/hero_join.h` applies only to the recorded class-1, level-1 profile). The combat fixture's
A0/30 placement answer carries HP in 16 bits, and 1,000,000 mod 65,536 = 16,960. Result: `16960/0`, with MP/SD/AG
600/51/39 from the progress demo formula and maxima 0.

Fix. The command no longer overrides the world's offline join. The hero is the recorded level-1 Dark Knight
(FryeZEN2, 2026-10-22, the APP-POLISH-003 evidence): `hero_join.h` seeds HP/MP/SD/AG 1100/200/52/25 as current
and maximum, and combat HP is the world default 1100. Same data and evidence as APP-POLISH-003; no new values. The
hero, Preview, is in the middle of the crowd. It now has the Dark Knight body and still casts the same scripted
skills 9/10/14/24 with the staff stance.

| HUD (`MU_HUD_TRACE`, every sampled second) | HP | MP | SD | AG |
|---|---|---|---|---|
| Before (main `71692108`) | 16960/0 | 600/0 | 51/0 | 39/0 |
| After, Lorencia and Tormenta | 1100/1100 | 200/200 | 52/52 | 25/25 |

The script now verifies this. It sets `MU_HUD_TRACE=1` and rejects a sample whose HUD differs from the session or
has a zero or exceeded maximum. Its glow check also changed from `!= 6` to `< 6`: later item lanes load a seventh
effect texture on some +3/+7 slots, and the old check refused a complete crowd ("incomplete base/glow textures: W01,
slot 2"). `MU_GFX_LIB` from the environment now overrides the repository's Rust build path.

`native/tools/bench_stress.py` (NATIVE-PERF) keeps `--class 0 --hero-hp 1000000`. Its HUD is not published, and
changing the hero would change the measured workload behind the quoted frame rates.

## 2. Demo item durability

Cause. `mu_gfx_layer_add_item` sets every new item to durability 1, a placeholder from ed9ed6be (2026-10-22,
offline mix/upgrades), because the layer has no Item.bmd. Tooltips did not show it at first: the world built them
from a scratch HUD item at full durability. ffbed220 (same day, personal-store/repair services) switched inventory
tooltips to the layer's own instance snapshot, so they read 1: "Durability: [1/53]".

Fix, at the source. The world's demo inventory (`world_gfx.c:demo_items`) now sets each item's durability to what
the item constructor (`0x00ccc5b0`) gives a new instance: the Item.bmd maximum at its level, with a stackable item
being a stack of one. This is the rule `client_price` already used, now shared as `full_durability`. A new layer
setter, `mu_gfx_layer_set_item_durability`, writes wire byte 2 (0..255, valid instances only). The layer's
placeholder default and every other add path (scripted `mixadd`, shop purchases, transfers, stub hosts) are
unchanged.

| `mu-world --gfx … --npc-script "10:tipinv:0 20:tipinv:2"` | before | after |
|---|---|---|
| cell 0, Blade +9 | Durability: [1/53] | Durability: [53/53] |
| cell 2, Dragon Helm +7 | Durability: [1/78] | Durability: [78/78] |

## 3. Quest-capture command

`docs/research/client-quests.md` now exports `MU_QUEST_SCENARIO=native/fixture/scenarios/quest-progress.scn` and
records what the command shows today. Without the scenario: no active quest. With it: quest 7 at 3/3 (`state 2`).

Found, not fixed (quest lane): the scripted dialogue no longer sends the accept request (F6 72). `60:option:1` still
asks for the NPC's quest list (request 901), but `90:option:0` reaches dialogue request 902, so `"accepted":0`.
The private `test_native_quest.LorenciaDemo` (expects 1) fails for that reason on unmodified main `71692108`
(checked with this lane's C changes stashed), with the APP-REFRESH-006 movies.

## 4. README images 26 and 27

Re-shot with the fixed command from this branch's build, after merging main `84a7f05d` (#319 RENDER-WORLDS-SLOTS3
moved 2,951 Tormenta particle pixels and 18 in Lorencia, so the images were re-encoded from the merged build). Method and framing are README-STRESS-001's:
world 0 at 182,128 frame 0, world 141 at 60,50 frame 100, FOV 65, 1600×1000, the same 80 loadouts and 8 monsters,
`MU_GFX_PUBLIC_DEMO=1`, `MU_GFX_TEST_CLOCK=1`, headless GL, window-only. Inputs: Native Data APP-REFRESH-006
(read-only) and the bundled eight-patch GFx library (`scratch/polish/libmugfx.dylib`, read-only). JPEG quality 85,
4:2:0, optimized, no EXIF: 450 KB (26) and 407 KB (27). Each scene has 80/80 players and name records, complete base
and glow textures, 5 skill events, 417 effects and 16 joints. Audit pins and the [finding](../research/readme-stress.md)
digests are updated. The README caption names the HUD values. The NATIVE-PERF-004 frame rates next to the images
were not re-measured and are unchanged.

Privacy review: both encoded files were read at full size. They show only the synthetic names W01–F80, Preview, the
demo monster names (Bull Fighter, Hound, Budge Dragon, Spider), the offline welcome line, the fixture HUD and the
public demo's 1,000/10,000 experience bar. No account or real character name, chat, desktop chrome or path.
Nothing was painted over.

Differences from October that this lane did not cause: the left of the Lorencia bridge (water, shoreline) and the
far-right corner of Tormenta now render black. A first-parent bisect from #205 to `71692108` (probe: Lorencia
182,128, 800×500, FOV 65) found RENDER-TIME-003 (#258). That change is intended: the frustum now uses the client's
640-unit GetScreenWidth, which at this wide FOV culls those edges. Newer item and effect work also changes armour and
spell pixels. Two runs on one build give a byte-identical Tormenta frame. Lorencia frame 0 differs in 49 pixels of the HUD strip
(GFx timing at the first frame).

## Checks

Listed with wall times in the PR body.

## Cleanup

After the ready line: scratch (`native/scratch/app-polish-006`: before/after/final captures, tooltip and quest
runs, bisect probes; the bisect worktree was already removed) and this worktree's `native/build` are deleted. The
library symlink under `native/gfx/mugfx/target` is ignored and goes with the worktree. No local input needs
keeping. The worktree stays until the steward merges.
