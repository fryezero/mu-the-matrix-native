# README-IMAGES-D: README images for the item, inventory and cape work (#337..#344)

Claude Opus 5.5 lane, 2026-11-07. Branch `claude/readme-images-d`, worktree `~/Documents/MTM/worktrees/readme-images-d`,
from main `a7f7b247` (#343), fast-forwarded to `02e4d94d` (#344 RENDER-ITEMS-CLOAK) before the cape image. Docs and
media only: no runtime source, validator or capture script changed. Offline only: no original client, launcher, live
read, account or network. The installed Native Preview, the Wine play app and the staged Wine app were not touched.
[Claim sources, commands and hashes](../research/readme-refresh.md#readme-images-d-claim-sources-and-media).

## Images

All are window-only headless GL renders of this lane's `mu-world` at the world FOV, 39, with the APP-REFRESH-006
Native Data (read-only) and `MU_GFX_PUBLIC_DEMO=1`. Nothing was painted over.

| Image | Before | After | Size |
|---|---|---|---|
| 08 inventory (replaced, same name) | grid items and a tooltip; equipment slots empty | Lorencia 138,123: the equipment slots hold the hero's Cookery Short Sword +9 excellent, Small Shield +7 and Wings of Heaven (INVENTORY-FX); the same items worn in the world, with the sword's glow; Blade +9 tooltip | 780×800 PNG, 402 KB (was 720×800, 363 KB) |
| 31 Lorencia demo outfits (new) | – | the shipped offline demo at 140,124, frame 90: Ironclad with the +9 excellent sword's level glow (inset from a 3200×2000 render of the same frame), Redhand on the gold Fenrir with the Xeno Blade +11 and Wings of Eternal | 1600×1000 JPEG, 434 KB |
| 32 capes and effects (new, test fixture) | – | Lorencia 136,133, frame 30: Velvet mid-stride with the InnocenceCape streaming, Nocturne's black cloak (class 4, `0x2394`), the hero Preview's InnocenceCape from behind, Seraph's Cloak of Brilliance (two half-capes and its sparks), Thorne's and Ashe's armour owner effects (`0x1bc3`, `0x1c78`) | 1600×1000 JPEG, 329 KB |

Added media: 434 + 329 KB new, 08 grew 39 KB; about 0.8 MB in total.

32 is a 2560×1600 crop of a 3200×2000 render scaled to 1600×1000, so it frames 1.25× closer than a 1600×1000 view at
the same FOV 39 (about the client's zoom step 30). The caption says that it is a test fixture.

Not made:

- **Raklion spray (#337).** At the tour tile 224,211 the 0x14 statue's WATERFALL spray changes the frame by a mean of
  0.2–0.4 per channel (RENDER-WORLDS-RAKLION). In a 1600×1000 render it is not visible at README size.
- **Karutan crystal (#340).** The 0x81 crystal glows at 205,17, but it covers about 0.2% of the frame. Four nearby tiles
  were tried: the area is dark and the hero stands behind pillars. Neither earns a README image; the world table row
  names both.
- **01 hero.** It stays: a custom +13 crowd with mounts, which the new item work does not change. 31 shows the demo
  outfits instead.

## Text

README: world table (Raklion/Karutan row), effects paragraph (item programs in the world, cloak sparks, armour owner
effects), item rendering (1,363/1,674, 311 left, cites 002T; demo outfits paragraph with 31; capes paragraph with 32),
the interface table's 08 alt text and caption, Progress rows (special items, interface) and What is still missing
(311 bodies). Audit pins: 08 changed, 31 and 32 added. Research note: [readme-refresh.md](../research/readme-refresh.md#readme-images-d-claim-sources-and-media).

## Privacy review

Each encoded file was read at full size in quadrants. Names visible: Ironclad, Redhand, the cut-off end of Aeris (31);
Preview, Velvet, Nocturne, Seraph, Thorne, Ashe (32, fixture names); Preview (08). 08's HUD has the public demo values
(1,100/1,100, 200/200, 25/25, 1,000 / 10,000 experience, zen 100,000). No account or real character name (the
owner's character never appears: every render passes `--hero-name`), no server address, chat, local path or desktop chrome.

## Findings for other lanes

1. **Grey ground patches.** `mu-world` GL 1280×800, Lorencia 138,123, with `--npc --npc-demo ... --gfx-open inventory
   --npc-script 50:tipinv:0` and a players file without any `party` player draws large flat light-grey polygons over the
   terrain and turns the grass grey (deterministic: identical bytes on reruns). Not with the shipped players file (the
   party list is open), not without `--npc`, and not without the tooltip. It looks like GL state or a texture name
   leaking from the GFx tooltip path into the terrain draw. Not investigated (docs lane). 08 uses the scene without
   `--npc`, which is clean.
2. Overhead names are drawn at a fixed pixel size, so a 3200×2000 render scaled down shows them small (31's inset, 32).

## Checks

Listed with wall times in the PR body. Steward validators: none (docs/media, rule 6c). No capture script changed, so
`test_native_stress` was not run.

## Cleanup

After the ready line, the scratch folder `~/Documents/MTM/mu-mac-tools/native/scratch/readme-images-d` (renders,
crops, fixture, compose script) and this worktree's `native/build` are deleted. No local input needs keeping; the
commands and the fixture are in the research note.
