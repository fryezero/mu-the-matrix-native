# APP-REFRESH-007

Implementation handoff, 2026-11-07. Worktree `worktrees/app-refresh-007`, branch `claude/app-refresh-007`. Claude
Opus 5.5 lane. Offline only: no original client, launcher, live read, account, network or protection work. The
owner's Wine play app, its prefix settings and the staged Wine app were not touched. Docs-only PR (brief rule 6c).

## What the installed app now has

The Native Preview was reinstalled from main **`53cffd00`** (#327, steward batch 65). It has everything since
APP-REFRESH-006 (`7e6a9292`):

- #312 APP-REFRESH-006's own exporter change (Native Data requires `itemtrs.tsv`; no app change);
- #313 RENDER-EFFECTS-016: 0x70c's Fire06 stones supported;
- #314 APP-POLISH-005: Windleaf (Elf, character-select row 2) arrives in the Lorencia field at 182,128 with skill
  2044 on hotkey 2; mu-client prints the `{"effects": …}` line;
- #315, #327 TEST-SPEED-004/005: tooling only;
- #316 RENDER-ITEMS-002Q and #325 RENDER-ITEMS-002R: item bodies 1,276 → 1,345 of 1,674;
- #317, #318, #323 README;
- #319 RENDER-WORLDS-SLOTS3: the outer rand draw in every world;
- #320 APP-POLISH-006: crowd HUD vitals, demo item durability;
- #321 REGRESS-001: the offline quest accept works again;
- #322 RENDER-EFFECTS-017: armour particle kinds, raster clamp to edge;
- #324 RENDER-WORLDS-FOG: world 0x1e's box fog;
- #326 RENDER-WORLDS-121: Test Area 121's two slots, Devias 0x67's action choice.

**Not included:** nothing that had merged at build time is missing. Batch 65 (#326 + #327) merged at 00:44 CST,
during this lane's prep, so the build waited for it.

**Order of events:** prep while batch 65 was gated: rollback, the Native Data diff, the proof helpers (dry-run on the
APP-REFRESH-006 app). Then the worktree was checked out detached at `53cffd00` (so the bundle's `MUNativeCommit` is
the main SHA), built, installed at 00:45, and every proof below ran on that build. The worktree then went back to the
branch (fast-forward to the same commit) for the docs and checks.

## Installation

- `~/Applications/Mu The Matrix Native Preview.app`: `MUNativeCommit` 53cffd00, real Ruffle.
  - Built with `nice -n 10 make -C native -j4`, `make -C native -j4 world`, then
    `nice -n 10 make -C native/app -j4 MUGFX_LIB=~/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx.dylib`
    (bundles `Contents/Frameworks/libmugfx.dylib`, 17.9 MB, and now `Resources/session/demo-skills.txt`).
  - The library is the same build APP-REFRESH-006 bundled (22 Oct). It was not rebuilt: since then main's
    `native/gfx/mugfx` changed only by NATIVE-PERF-003's profiling hooks (`mugfx_perf_frame`/`_end`, which
    `mu_gfx_layer.c` looks up with `dlsym` as optional), the `MU_GFX_TEST_CLOCK` deterministic clock (only with that
    variable set) and release-profile flags (ThinLTO). None changes what a player sees.
  - No Preview was running. Installed with `ditto` over the removed old copy. Strict deep signature check
    (`codesign --verify --deep --strict`) and `--check-bundle` pass (mu-client, network guard, GFx library (Ruffle)).
  - `--print-settings`: "GFx movies 179, text tables 31, object files 47, sound table yes; setup done".
- **Rollback:** `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-007/`:
  - `Mu-The-Matrix-Native-Preview-APP-REFRESH-006-7e6a9292.app.zip` (11.7 MB, 55 entries, SHA-256
    `69f22636…c296714d`);
  - `settings.json.before`, which selects `APP-REFRESH-006/Native Data` (unchanged by this lane).
  - To roll back: unzip the app into `~/Applications`; `settings.json` needs no change.
  - The `app-refresh-002/` to `-006/` rollbacks are kept.

## Native Data: kept (`APP-REFRESH-006/Native Data`)

No export input changed since the set behind the installed Native Data was built.

- `git diff --stat 20b9d88b origin/main` (20b9d88b is APP-REFRESH-006's exporter commit, which built that set) over
  `scripts/build_native_data_export.py`, `live_lang_to_plain.py`, `live_effect_table_to_plain.py`,
  `live_objects_to_plain.py`, `extract_audio_tables.py`, `native_data_manifest.py`, `pins.py`, `native/data`,
  `native/app/Sources` and `native/app/bundle-dylibs.sh`: **empty**.
- `7e6a9292..origin/main` over the same paths shows only 20b9d88b itself and `native/app/Makefile` (bundling
  `demo-skills.txt`, an app resource, not Native Data).
- The setup's movie converter (`native/gfx/gfxconvert*.c`) did not change: `native/gfx` differs only in
  `mu_gfx_layer.{c,h}` (APP-POLISH-006's durability setter, compiled into mu-client).
- `mu-native-data check` on the folder: "Native Data manifest OK". `settings.json` was not changed.

## Journey proofs (installed app, `53cffd00`)

**Smoke:** `--smoke --backend gl`, isolated logs/settings, `PATH=/nonexistent`, `--no-store`, with and without
`--audio`: ok, world reached, Apple M5, guard `mu-nonet`, 0 connects, 0 inet, 0 lookups, 0 other calls denied.

**Headless:** the installed bundle's mu-client with the app's own launch plan (`--print-plan` over an isolated
support dir holding a copy of the owner's settings), `--no-store`, isolated option settings, network guard loaded
(every run: 0 denials). The field session is the bundled one with `join 1 0 179,131 90`.

| Proof | Result |
|---|---|
| Selected-skill right-click cast (Budge Dragon) | `skill_casts` 1, 0 refused |
| Kill, drop, Space pickup | `kills` 1, `drops` 1, `space_picks` 1, 1 pickup request, 1 completed |
| Audio (option.ini `[DEFAULT]` `IsMusicPlay=1`, `Volum=9`; `--wav` over the same journey) | 898,228 stereo frames at 44.1 kHz; peak 31,656 = **−0.300 dBFS**; 0 samples above 31,656; 0 at full scale; RMS 4,777 |
| Warps travel M → Noria → M → Devias | `travel: world 0 -> 3` (175,117), `world 3 -> 2` (208,47); `travels` 2, `travel_plates_removed` 4, `plates` 1, `stale_plates` 0 |
| Arrival HUD and a Hound hit (`MU_HUD_TRACE=1`, 800 frames) | HUD = session = **1100/1100** HP, 200/200 MP, 52/52 SD, 25/25 AG for 13 samples; one hit → 1077/1100 for 16 samples; Hound killed (`kills` 1, `drops` 1). Travel run: 1100/1100 in all 21 samples |

**Windowed:** the installed app itself (`MuNativePreview --seconds 75`, isolated support, log and option dirs,
muted, the field session, `MU_NATIVE_EXTRA_ARGS="--no-store --auto --hold 6 --input-script '…' --out-dir '…'"`).
Travel 0 → 3 → 2: `travel_plates_removed` 4, `plates` 1, `stale_plates` 0. HUD 1100/1100 in all 67 trace samples.
1,686 frames in 75.0 s (about **22.5 fps**) at a 3200×2000 drawable. Guard `mu-nonet`, 0 denials. Window name
"Mu The Matrix Native Preview — OFFLINE PREVIEW (no server connection)" (CGWindowList), no fps suffix.

- The display is now Retina: the window is 1600×1000 points with a 3200×2000 drawable (APP-REFRESH-006: 1504×936
  at 1x). Script clicks are in drawable pixels, while the windowed GFx layer is drawn at 2x. So the Warps rows sit
  at twice the 1x points: Noria 244,514 and Devias 244,648, not 122,257 / 122,324.
- The first two windowed runs used the old points (and then the halved ones). Both clicks landed inside the Warps
  window without selecting a row, so the hero did not travel. The third run used the 2x points and travelled.
  A later refresh on this display should start from the 2x points.

### New proofs

**(a) Windleaf and skill 2044.** The bundled session as installed. Flow: login → character-select row 2
(`click:row:2`, `dblclick:row:2`) → key 2 (`key:0x32`) → right-click a monster near 182,128.

| Run | Cast | `{"effects": …}` line (client output) |
|---|---|---|
| Headless, installed mu-client, GL 1504×936, 220 frames, Budge Dragon at (845,100) | `skill 2044 at actor 10: ok`; `skill_casts` 1, 0 refused; bar selection 2044 | `"skills":1,"sounds":2,"effects_created":121,"max_live_0x70a":1,"max_live_0x70c":11,"max_live_rings":66,"decals":1524,"decal_quads":56348,"unsupported":0` |
| Windowed installed app (`--seconds 25`, 3200×2000), still copy of the demo placement, Bull Fighter at (920,1020); from the app's client log | `skill 2044 at actor 8: ok` (four runs) | `"skills":1,"sounds":2,"effects_created":121,"max_live_0x70a":1,"max_live_0x70c":11,"max_live_rings":66,"decals":1504,"decal_quads":55880,"unsupported":0` (decals 1,365 to 1,504 by run: they count drawn frames) |
| Before: the APP-REFRESH-006 app (rollback copy), same headless flow | Windleaf joins Devias (world 2), bar selection 26, `skill_casts` 0 | no `effects` line |

- The headless numbers are APP-POLISH-005's own (121 effects, 1/11/66, 1,524 decals, 2 sound cues, 0 unsupported).
- The windowed run used a scratch copy of the bundled placement with `wander` removed, as APP-POLISH-005 did:
  the monsters wander on wall-clock steps, so a frame-scripted click in a window can miss them.
- Screenshot 2 is the client's own framebuffer capture (`shot:` action) at frame 125 of that windowed run. It shows
  the rain, the 0x70c rings and the crater decals. Window captures by `screencapture` at fixed seconds missed the
  rain's few seconds.

**(b) Quest accept offline (#321).** `test_native_quest.LorenciaDemo`'s scripted dialogue, run with `mu-world` from
the same main (the installed mu-client has no scripted NPC verbs; the quest lane is the same `world_gfx.c` code),
with the installed Native Data `lang` and `gfx` and the bundled libmugfx, no `MU_QUEST_SCENARIO`:
`"accepted":1,"completed":1,"progress":3,"undecodable":0,"active":[]`. Frame 60 reaches
"dialogue request 901: the NPC's quest list (demo server)", and no request 902 appears. APP-POLISH-006 recorded
`accepted 0` on main `71692108` for the same script.

**(c) World 0x1e box fog (#324).** Box x 16100..19000, y 18900..21700 world units = tiles 161..190 × 189..217.
Session `join 1 30 <tile>` (world 30 = 0x1e, `Data/World31`); 200 frames; frame 199. The installed app against the
APP-REFRESH-006 rollback app (the same session without the `skills`/`hero` lines, which the old client rejects):

| Tile | 006 → installed, mean abs. diff per channel | Pixels changed | Mean brightness 006 → installed |
|---|---|---|---|
| 176,190 (inside) | **18.79** | 440,326 of 1,024,000 | 25.8 → 7.0 |
| 163,195 (inside, near the west edge) | 4.12 | 156,131 | 10.1 → 6.0 |
| 158,195 (outside) | **0.00** | **0** (byte-identical frame) | 14.1 → 14.1 |

The session placed the hero in the box; the frame outside it is unchanged, and the one inside darkens to the fog
colour from the far floor in (screenshot 4). RENDER-WORLDS-FOG measured 17.6 at 176,190 with `mu-world`.

**(d) New item bodies (#316/#325).** `mu-render ui inventory` from the same main, the installed game, time 123456,
`MU_LANG_DIR` = installed Native Data `lang`, codes 6300..6303 and 2096 (wings `0x2382`..`0x2385`, bow `0x1316`;
code = type − 0x0ae6). "Before" is `mu-render` built at `7e6a9292` (temporary worktree, deleted):

| | Models drawn / missing | Level 0 | Level 13 |
|---|---|---|---|
| `7e6a9292` (APP-REFRESH-006) | 5 / 0 | 2,175 triangles, `eca07870…b6c5` | 2,175, `eca07870…b6c5` (level ignored) |
| `53cffd00` (installed) | 5 / 0 | 7,455, `91b79f79…cca3` | 10,775, `da9fd01e…82c5` |

11,553 (level 0) and 11,946 (level 13) pixels change. In screenshot 5 (level 13, before | after) the plain fallback
becomes the recipes' passes. The four wings draw smaller (their long lower parts are no longer drawn) and the bow
draws red with its glow. These are offline native renders, not compared with an original-client capture.

**(e) Test Area 121 (#326).** Session `join 1 121 128,128`: rc 0, world 121, scene 6 for 143 frames, no crash.
The client logs "objects: …/Native Data/objects/EncTerrain122.plain: cannot read (drawing none)". The export set
has no objects for world 121: RENDER-WORLDS-121 records that the installed `EncTerrain122.obj` does not decode
natively and that 121 has no capture. So #326's two slots cannot show in the installed app; skipped beyond arrival.

**Screenshots** (local, never committed): `~/Documents/MTM/mu-mac-tools/native/renders/app-refresh-007/`, 760 px
wide or less, quantized (0.9 MB in all). Demo names only (Ironclad, Windleaf, Hero, Aeris, demo monsters).

| File | Shows |
|---|---|
| `1-title-lorencia-arrival.png` | window-only capture of the installed app: title bar "… OFFLINE PREVIEW (no server connection)", field arrival, HUD 1100/1100 |
| `2-windleaf-2044-rain.png` | windowed installed app, client framebuffer at frame 125: skill 2044's rain, rings and craters |
| `3-devias-after-travel.png` | window-only capture after Warps travel 0 → 3 → 2: Devias 208,47, only the hero's plate |
| `4-world30-box-fog-before-after.png` | headless frame at world 0x1e 176,190: APP-REFRESH-006 app (left), installed app (right) |
| `5-new-bodies-before-after-level13.png` | inventory grid crop at level 13: `7e6a9292` (left), installed main (right) |

## Checks (TEST BUDGET: no lane gate; docs-only PR, rule 6c)

Heavy steps under `nice -n 10`, `make -j4`. Load stayed at 4.5–11.7 (1 min) and memory at 63–69% free; no step
waited.

| Step | Result | Wall time |
|---|---|---|
| Rollback zip + settings copy | 11.7 MB, 55 entries | 0.8 s |
| Native Data input diff | empty since 20b9d88b | < 1 s |
| Build at `53cffd00`: `make -C native -j4`, `world`, `make -C native/app -j4 MUGFX_LIB=…` | ok; signed, `--check-bundle` ok | 16 s + 4 s + 9 s |
| Install (`ditto`) + strict signature + `--check-bundle` + `mu-native-data check` | ok | < 1 s |
| Installed smoke, without and with `--audio` | ok, 0 network | 13 s + 13 s |
| Headless journey with `--wav` / Hound+HUD (800 frames) / travel | see above | 12.5 s / 14.0 s / 12.6 s |
| Windowed travel (third run counts; two coordinate misses before it) | see above | 77 s × 3 |
| (a) Windleaf headless / windowed (four runs: two shot timings, a burst, the `shot:` run) / 006 before / HUD trace | see above | 9.4 s / 26 s × 4 / 8.7 s / 9.2 s |
| (b) quest, `mu-world` 420 frames | accepted 1 | 4 s |
| (c) fog, 3 tiles × 2 apps | see above | 5.5–7.2 s each |
| (d) `mu-render` at `7e6a9292` (temp worktree build) + 4 inventory renders | see above | 6 s + 4 × 1 s |
| (e) world 121 arrival | see above | 6.2 s |
| `scripts/audit_repository.py` (one new file) | 2,024 staged files, 0 rejected | 19 s |
| Rule 6c doc modules: `tests.test_world_captures_2`, `tests.test_repository_policy` | 13/13 OK | 0.7 s |
| Rule 6c doc modules: `test_native_item_textures`, `test_native_data_manifest` (from `native/tests`) | 23 OK, 1 skipped | 22.7 s |

- Steward validators: none (docs only, rule 6c). No code or tool changed.

## Follow-ups

1. **Windleaf's HUD maxima are 0.** `MU_HUD_TRACE` for Windleaf: session = HUD = 1100/778/1775/284 (HP/MP/SD/AG),
   `max` 0,0,0,0 in all 5 samples, so the orbs read "1100/0" and "778/0" (screenshot 2). `fixture/hero_join.h` seeds
   maxima only for the recorded level-1 Dark Knight (APP-POLISH-006 found the same for class 0). A lane that gives
   the Elf demo its join maxima (fixture data, no formula change) would fix the orbs.
2. **Retina windowed coordinates.** Windowed input-script clicks are drawable pixels but the GFx layer is drawn at
   2x on this display, so 1x GFx coordinates miss (see Windowed above). A helper that scales GFx targets by the
   drawable/window ratio, or a `click:warp:N` action, would make windowed journeys display-independent.
3. **Test Area 121 has no objects** in Native Data (`EncTerrain122.obj` does not decode natively); #326's slots
   only show with RENDER-WORLDS-121's demo layout.
4. **Inventory wings 0x2382..0x2385 draw only their upper part** with the new recipes (screenshot 5). The recipes
   are compared with the original under Unicorn in RENDER-ITEMS-002R. The inventory picture itself is not compared
   with an original-client capture.
5. **libmugfx** is the 22 Oct build. A rebuild from main's `native/gfx/mugfx` would add only the profiling hooks and
   the test clock; do it when a player-visible GFx change lands.
6. Still open from APP-REFRESH-006: no `sounds` counter for the field journey (the Windleaf `effects` line now
   counts 2044's cues); ground skill 2045 is unreachable (no Skill(Kor) record); weapons spill past their cells;
   Arca War worlds 93/97/102/112 not installed; worlds 145/95/110 draw no objects; old export set
   `scratch/native-data/export.before-app-refresh-006` and the APP-REFRESH-001/legacy Native Data folders can go
   (the owner's call).

## Cleanup

- Kept: the rollback folder, the five screenshots.
- Deleted after the ready line: `scratch/app-refresh-007` (helpers, sessions, runs, frames, WAV, the unzipped
  rollback app, inventory renders), this worktree's `native/build`, and the temporary `worktrees/app-refresh-007-base`.
  The worktree stays until the steward merges.
- Helpers, rebuildable from this file and APP-REFRESH-005/006: `hl.py` (headless run of an app bundle's mu-client
  with the app's plan: `--session`, `--audio`, `--hud`, `--frames`, `--every`, extra args; `OPTION_INI`),
  `runw.sh` (the GUI app with `--seconds`, isolated dirs, muted option.ini, `MU_HUD_TRACE`, window-only shots via
  a compiled `~/Documents/MTM/mu-mac-tools/winshot.swift`), the scripts `hj.txt`, `hound.txt`, `travel-hl.txt` as in
  APP-REFRESH-005, the windowed `travel-retina.txt` (M at 300, click 244,514 at 331, M at 600, click 244,648 at
  631), the fog sessions (`join 1 30 176,190|163,195|158,195 90`) and the still placement (the bundled one without
  `wander`).
