# Native Preview refresh, APP-REFRESH-001

2026-10-28. Initial main `7d813a9`. This is an offline app refresh and native
integration check. No reconstructed routine changed; no new instruction-equality
claim is made. Original client, launcher, live state and service were untouched.

## Reproduced faults

1. The app's default local export path still used `Documents/mu-mac-tools`.
   `Paths.defaultScratch` now prefers `Documents/MTM/mu-mac-tools` when present,
   retaining the legacy fallback and explicit override. A synthetic HOME test
   fails before the change and passes afterward.
2. The session skill migration reads mana and AG from its session's hero domain.
   World-tool seeds deliberately supply only class/place, so all three world
   session creation paths had zero mana. The INPUT-001 right-click journey
   selected skill 19 but reported `mana`, zero casts and zero kills.
3. Combat's initial/respawn A0/30 frame wrote only HP. Its zero-filled MP/SD/AG
   fields erased the progress fixture's resources. This packet replaces all four
   resource fields in the verified hero handler. World scenarios now include the
   existing progress fixture's baseline stats and resource replies; combat
   obtains MP/SD/AG from that independent server model and keeps its HP policy.
   Three path regressions fail before the fixes and pass after them. Synthetic
   gameplay records a selected cast, attack, kill/drop and Space pickup.

All initialization remains in the offline fixture path. The hero seed, production
session checks, skill requirements, encrypted-send refusal and reconstructed
handlers are unchanged. The synthetic baseline does not reconstruct an account
join or prove live casting.

## First run

Build with `make -C native && make -C native viewer`, then
`make -C native preview-app MUGFX_LIB=/absolute/path/to/libmugfx.dylib`.
This run reused the existing real ABI-3 Ruffle build in
`mu-mac-tools/native/scratch/polish/libmugfx.dylib`; no network fetch was needed.
The optional later GPU profiling extension is not a new library-build claim.

Both production-pin setups ran with `env -i`, temporary HOME/CFFIXED_USER_HOME
and `PATH=/nonexistent`. No Python executable was available to the app. The
bundled C converter produced 179 movies and 82 NaviMaps. Root/component checks,
repeat setup and corrupted-build refusal through setup/plan/smoke pass; the
three refusals start no client. A second setup imported newly exported existing
snapshots: 27 language files, 32 object/sidecar files for 16 worlds, one sound
table. The exporters used the supported executable pin, not a retroactive stamp
of old outputs. Exports and converted assets remain private.

## User-path evidence

- Synthetic doctor: all eight binaries and offscreen OpenGL pass on Apple M5.
  Scene flow reaches the world; walking reaches tile 124,123 with one arrival,
  no path refusal and 12 units per position step.
- Signed app with real installed assets and Ruffle: a 516-frame windowed journey
  opens/closes inventory, character, imprint, master/fourth/fifth trees, quests,
  Move, friends, options, personal store and system menu, plus chat. Every panel
  PNG was inspected. The twelve unsupported bindings retain named refusals;
  J retains the recovered empty handler.
- Physical-script mouse clicks on Move rows travel 0 → 3 → 2 → 0. Noria, Devias
  and Lorencia screenshots show textured terrain, world objects and characters.
  The separate 180-frame mu-world travel drive records three travels, zero
  failures. These are offline travel adapters, not live map replies.
- INPUT-001 authored actor/root, real Ruffle and app-converted movies: selected
  skill 19 succeeds, left-click attack produces one kill/drop, Space completes
  one pickup. A separate eight-second windowed numeric attack/cast journey
  reaches scene 6. The updated recipe explicitly enables items and attacks
  after casting; encrypted skill requests alone do not promise demo damage.
- Sound logs include successful loaded playback and session-origin cues. The
  app's network guard reports zero IP/connect/lookup attempts. Audio time-series
  equality and human listening quality are outside this smoke claim.
  An explicit `--smoke --audio` run, with BGM enabled through Options in the
  temporary settings directory, renders 545,428 stereo PCM frames, peak 12,471
  in signed 16-bit samples. `--smoke` defaults to no audio. The installed sound
  preferences mute music and set effects to zero; those preferences were not edited.

Missing fourth-tree decoded tables, blank master content for the demo class,
and the unpopulated fifth tree remain visible pre-existing acquisition/domain
limits. No original-image equality, every-world rendering, live gameplay,
second-user capture, signing distribution or gate-5 completion is claimed.
Final gate, installation and cleanup results are in [the handoff](../handoffs/APP-REFRESH-001.md).

The resumed locked gate passes 1,521 tests, 1,334 passed and 187 explicit skips,
plus all eight fixture scenarios. The final 400-frame input repetition confirms
one selected cast, zero skill refusals and one kill/drop/pickup. Manifest
verification, repeat setup and three corrupt-build refusal paths pass again.
The installation uses the app's setup in a new build-verified data folder;
the legacy folder is preserved. The PR carries the post-merge install result.
