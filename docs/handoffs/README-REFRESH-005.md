# README-REFRESH-005 (lane A: world, effects, combat, mounts, comparisons)

Claude Opus 5.5 lane, 2026-11-06. Branch `claude/readme-images-a`, worktree `~/Documents/MTM/worktrees/readme-images-a`,
from main `18ab0134` (#316 merged, #315 merged). Docs and media only: no runtime source, validator, pin of another
lane's image, live game, installed app or Wine app was touched. README-IMAGES-B (login, character select and
interface windows: 02, 03, 04a/b, 07, 08, 09, 13, 14, 19, 20, 21, 23, 24, 25) writes its own section.

[Claim sources](../research/readme-refresh.md#readme-refresh-005-claim-sources).

## Images

All new native panels are headless `mu-world` GL renders built from `18ab0134` (`nice -n 10 make -C native -j4`),
window-only, `MU_GFX_PUBLIC_DEMO=1`, demo names (Preview, Windleaf, the demo players), Native Data
APP-REFRESH-006 (read-only). JPEG quality 85, 4:2:0, progressive, no EXIF; every image reviewed at full size after
encoding. No pixels painted over except the privacy blurs named below.

| Image | Old (October 22/28) | New | Why |
|---|---|---|---|
| 01 hero | Lorencia, hero on a Dark Horse, ordinary demo players | Lorencia fountain, 1600×1000: hero on a Dark Horse, six demo players in +13 sets 270/276/282/313/402/9 (incl. #316's 0x19f4/0x19fa/0x1a00/0x1a1f/0x1a78 helms and chest pieces), third wings, Fenrir/Dinorant/Dark Horse, Panda, Dark Raven, HUD | textured new armour bodies (TEX-001..003, HIDDENMESH, 002Q), HUD vitals from the session |
| 05 worlds | Atlans fish, Devias snow path, Noria field, Lorencia water | October 22 tour tiles from today's main: Atlans coral with fish, Devias town, Noria glowing plants, Lorencia fountain | world objects/after passes since then; same views as the fidelity tour |
| 06 effects | Hellfire-type pillars, Twister, Lorencia fires/waterspout | Aqua Beam, Inferno, Meteorite, Ice at demo monsters | new primary visuals (RENDER-EFFECTS-002..004) |
| 10 combat | DK sword hit with HUD | Elf bow 0x12f9 attack, sparks, damage numbers, miss, HP bars (zoomed, FOV 30) | bow sparks/arrows (007..016), larger numbers |
| 12 pets/mounts | Imp, Dinorant, Dark Horse, gold Fenrir, Tauros with the live hero's name "Nighty" | Imp, Dinorant, Dark Horse, gold and red Fenrir, demo name Preview | privacy (a real character name), same layout 1400×280 |
| 22 mounts | 12 mounts + 4 close-ups, name "Nighty" | same 16 mounts/pet, larger crops, Preview | privacy, larger view |
| 15 lighting | live / before / after (October 18), other players' names, shop titles, chat and hero values readable | same live and before panels, live panel blurred (names, shop titles, chat, FPS, quest list), bottom = today's main at the same tile 144,140 | privacy and current native panel |
| 18 fidelity | live / before / after (October 22) | live (hero name blurred) / native October 22 after its fixes / native November 6, same tiles and crop | Icarus now draws its cloud cover and swirls |
| 16 login | kept | – | today's native login panel differs by animation phase only, no visible improvement |
| 17 model viewer | kept | – | mu-viewer and decoders unchanged |
| 26/27 80 players | kept | – | rerun of `capture_readme_stress.py` gives the same crowds; its HUD now reads the session vitals (`16960/0`, the fixture has no maxima), so the October frames are the better image |

New: **28** bows (0x12f9, 0x12fc, 0x12fb, 0x130a Triple Shot at frame 18, Windleaf, Lorencia 182,128; each scene 0
unsupported); **29** ground skill 2044 (frames 10/20/25/40: rain, rings, impact rings with stones, craters; 14
arrows, 121 effects, 0 unsupported); **30** worlds live vs native (DATA-ACQ-002 Kubera, Ignis, Kardamahal, Swamp of
Darkness, live hero name blurred, HUD cropped). Sizes 112–514 KB, all ≤ 650 KB. Audit pins: 8 changed, 3 added.

## Text

README: hero alt; world table (+5 rows) and coverage 144/144, 48/48, slots 142/144, Kubera image score; temporal
live half; captions of 05/15/18; new image 30 with the DATA-ACQ-002 note; effects 20/23 (65/77), rank-5 19/19, Bows
and Ground skills paragraphs with 28/29; alt texts of 06/10/12/22; item rendering 1,319/1,674, 18/24 links, 355
left, white types 13/1,691; 80-player text with NATIVE-PERF-004's figures; Sound (music 43/44, effect sounds);
Progress rows (world, items, item textures, interface, fidelity, temporal, skill visuals, bows/ground, audio,
packaging, performance, test tooling); What is still missing (rendering/performance).

## Checks (TEST BUDGET 6c: docs + media)

Listed with wall times in the PR body.

## Cleanup

Renders (`renders/readme-images-a`), scratch (`scratch/readme-images-a`, incl. a copy of the installed libmugfx)
and `native/build` are deleted after the ready line. No local input is retained; the committed README sources,
this handoff and the claim table record how each image was made. The worktree stays until the steward merges.
