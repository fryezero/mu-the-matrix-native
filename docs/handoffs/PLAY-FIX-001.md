# PLAY-FIX-001

Implementation handoff, 2026-11-03. Worktree `worktrees/play-fix-001`, branch `claude/play-fix-001`, from origin/main
`d9389d5`, merged with `994460c` (#279 APP-REFRESH-003). macOS 27.2, Apple clang 21. Offline only: no original
client, launcher, live read, account, network or protection work. The installed app was not touched (a later
APP-REFRESH lane reinstalls).

## 1. Stale actors after world travel

**Symptom (APP-REFRESH-003 screenshot 4).** After Warps travel Lorencia → Noria → Devias, the Lorencia monsters'
names ("Budge Dragon", "Hound", "Bull Fighter") float in Devias without models.

**Cause: the native client.**
- `world_rt_travel` unloaded the world and rebuilt the names model, but it never told the hudPlayerName movie.
- The movie persists across the travel, so it kept every old clip at its last position.
- On the re-attach the hero's plate was also replayed through addInfo a second time.
- The offline fixture is not at fault. On a world change the client clears its own characters; the server only
  sends the new viewport.

**What the original does** (`docs/research/client-maps.md`, "What a numbered teleport clears"; verified).
ReceiveTeleport `0x0128136d` with a non-zero number runs these before it compares the world:
1. ClearItems `0x017ea38b`: the movie's `clearAllItem`, then 1,000 item objects Live = 0.
2. ClearCharacters(HeroKey `[0x06fca288]`) `0x0137c276`: every live record but the hero's is killed. In scene 6
   it loses its plate through removeInfo `0x009a176b` → `0x00c83a04`, except in the Chaos Castle worlds of
   `0x009dacb8`. Owned objects are killed, and every record gets the 16-call release tail.
3. `0x00fcf496`, then ClearWorldMap and LoadWorld.

**Fix.**
- `reconstructed/map/map_clear.c` ports the four routines: the teleport clear order, `0x009dacb8`, ClearCharacters
  and ClearItems.
- `native/core/mu_world_names.c` `mu_world_names_clear_characters` runs ClearCharacters over the names model.
  `world_rt_travel` calls it before the unload, on the old world.
- `native/world/world_names_gfx.c` keeps the list of clips the movie holds when it re-attaches to the same layer.
  The hero's clip stays and the replay adds only missing keys. `stale_plates` counts clips without a plate.
- Reports: `travel_plates_removed` on the map line, and an `input_travel` line in mu-client's input report.
- The demo still spawns monsters only in its start world. The fixture invents no Devias or Noria monsters, since
  the real server would send that viewport.

**Before → after** (headless app plan, installed movie, Warps M → Noria → M → Devias):

| | travel_plates_removed | movie clips in Devias | stale clips |
|---|---|---|---|
| before (same build, clear disabled) | 0 | 5 | 4 |
| after | 4 | 1 (the hero) | 0 |

- Real-movie call log (mu-world Lorencia → Noria): removeInfo for keys 264..267, and addInfo for the hero 4660
  exactly once.
- Screenshots (window content, local): `~/Documents/MTM/mu-mac-tools/native/renders/play-fix-001/`
  - `1-devias-after-travel-BEFORE.png`: the installed Preview, "Budge Dragon" and "Bull Fighter" floating.
  - `2-devias-after-travel-AFTER.png`: only the hero's "Ironclad".

## 2. Audio clipping at Volum 9

**The original's mapping** (verified earlier, rerun here: `validate_audio` `settings`):
- Effect group = `(float)level / 9.0f` (`0x00f2fe04`, `0x00c764c0`), linear in FMOD.
- Music group 0.4 or 1.0 from OpenWorld.
- No other client gain.
- Native matched this already.

**Cause.**
- In the APP-REFRESH-003 capture no music played: Lorencia 179,131 is outside the safe zone, so the world selects
  no track.
- The full-scale samples came from Effect-group voices summing past full scale at gain 1.0: wind, birds, the
  blacksmith and harp loops, and combat sounds.
- `nBlackSmith.wav` (8-bit) is itself at full scale.
- Source MP3 peaks (afconvert): main_theme 31,766; Devias 32,732; Noria full scale (3 samples); Kardamahal full
  scale (124 samples).

**Fix.**
- `native/core/mu_audio.c` `mu_audio_limiter`: a linked-stereo peak limiter with instant attack, 50 ms release and
  a −0.3 dBFS ceiling (31,656).
- It ends every engine mix, and mu-client's shell limits the sum of its two engines.
- Below the ceiling its gain is exactly 1, so the output is bit-identical there.
- `mu-audio render` now also prints `rms16` and `fullscale`.

**Measured** (journey: cast, kill, drop, pickup; 1,111,672 stereo frames; peak / RMS / full-scale samples):

| Volum | before (installed) | after |
|---|---|---|
| 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| 3 | 16,674 / 1,611 / 0 | identical |
| 5 | 27,789 / 2,685 / 0 | identical |
| 7 | 32,768 / 3,759 / 19 | 31,656 / 3,738 / 0 |
| 9 | 32,768 / 4,828 / 628 | 31,656 / 4,606 / 0 |

- Lorencia town square (main theme at 0.4), Volum 9: 180 → 0 full-scale samples.
- Intended test change: `test_resampling_loop_and_single_instance` now ramps to 0.9 instead of 0.9975, below the
  ceiling, so it still checks exact resampling.

## 3. Kardamahal map name

- The original (live DATA-ACQ-002 capture `scratch/data-acq-002/live/143-kardamahal.png`) draws "Karda Mahal
  Underground Temple" in the same shrunk text in the top-left box. That box is the client's own GFx movie, which
  Ruffle runs natively.
- Native matches, so it was left unchanged.

## Checks

- **Gate.** `nice -n 10 bash scripts/local-macos-ci.sh` after merging #279: 38 suites, 1,815 tests, 1,574 passed,
  241 skipped, 0 failures. Fixtures, viewer and live readers ok; audit 1,806 files, 0 rejected.
- **New validator** `validate_teleport_clear` (`--cases 500 --mutations`), 0 mismatches:
  - teleport_clears 500, plates_hidden 1,540, clear_characters 100 and clear_items 24 cases (2,164 in all).
  - Coverage: 15,500 kills, 3,108 removeInfo (247 in Chaos Castle worlds), 162 owned-object kills, 40,000 tails.
  - 6/6 mutants caught.
  - Registry row in `scripts/validators.toml`; the private test is `tests/test_orphan_validators_private.py`, and
    the portable test is `reconstructed/map/test_map_clear.py` (6).
- **Private validators rerun** (`run_validators.py --private --jobs 2`, `MU_RECOVERY_INTEGRATION=1`,
  `MU_SNAPSHOT_DIR=~/Documents/MTM/mu-mac-tools/native/scratch`, `MU_SECTION3=<pinned main-01ced000.bin>`,
  `MU_GAME_ROOT=<installed client>`):
  - Pass: validate_teleport_clear, validate_map, validate_map_polish, validate_session_map_overlay,
    validate_names, validate_audio, validate_audio_voices, validate_audio_music, validate_audio_combat,
    validate_audio_domains, validate_audio_items, validate_audio_charsel.
  - `validate_audio_callers` fails to link on origin/main as well: its hand-written source list lacks the object
    worlds that the RENDER-WORLDS lanes added (`mu_kardamahal_create`, ...). None of its files changed here.
- **Tests:**
  - `native/tests/test_native_names.py` 12/12, private GfxRoute and GfxTravel included.
  - `test_native_audio.py` 15 (1 private skip); the other audio suites (charsel, combat, cues, domain_world,
    domains, items) ok.
- **Headless app-plan journey** (installed plan with this build, field session, Volum 9):
  - `skill_casts` 1, `kills` 1, `drops` 1, `space_picks` 1, pickups 1.
  - Audio peak 31,656, RMS 4,606, 0 full-scale samples.
  - Travel 0 → 3 → 2 with `travel_plates_removed` 4 and `stale_plates` 0.

## Limits

- Same-world numbered teleports (a Move to the current map): the client clears there too, and the server re-sends
  the viewport. Native keeps the demo actors and plates as the stand-in for that re-send.
- The ClearCharacters tail (buffs, parts, effects, joints) is compared as calls. Native has no per-record
  counterpart, since its unload frees those parts. `0x00fcf496`'s singleton (other players' entries) is called in
  order, but has no native data.
- FMOD Ex documents constant-power panning for mono sounds (about −3 dB per side). Native still feeds mono at full
  level: FMOD's mixer is outside the pinned captures, so this is unverified.
- The limiter is a native output-stage choice. FMOD's own output stage was not analysed.
- Kardamahal's music did not start in the native session (peak 24,139 either way), so a source that clips itself
  was measured offline only.
- The app was not reinstalled; the installed Preview still has both bugs until the next APP-REFRESH lane.

## Local files

- Renders: `~/Documents/MTM/mu-mac-tools/native/renders/play-fix-001/` (two PNGs, kept for the PR).
- Scratch deleted. No new input is needed by a later lane.
