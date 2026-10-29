# DATA-ACQ-002: guided live captures on the owner's client, 2026-10-28

[Finding, per-world numbers and limits](../research/client-world-captures-2.md);
[provenance JSON](../research/client-world-captures-2.json) (every capture file's SHA-256, counts, comparison
numbers, music-read hashes).

- Branch `claude/data-acq-002`, worktree `~/Documents/MTM/worktrees/data-acq-002`, from origin/main `147005d`.
- Four live sessions under the shared game lock (17:21–17:53, each ≤ 15 minutes), Nighty on MTM-1. Travel only by
  the Warps window; no walk, fight, NPC, shop, trade or item action; ended in Lorencia; client and launcher closed,
  lock removed after each session. Read-only memory reads and window-only shots.
- The CrossOver bottle `MuMatrix32` no longer exists; the owner's free-runtime prefix of `Mu The Matrix.app` was used
  (details in the finding). Its `LauncherOption.if` was changed to the 1722 × 1048 window for each session from a
  rollback copy and restored byte for byte. Fast x87 refused to patch on this macOS (plain Rosetta).
- Session 1 entered at Tormenta Island 134,66 under attack (the owner's last spot) and was closed at once.

## Result

- **32 arrival captures in 31 worlds**: 27 of the 48 factory classes (Vulcanus 63, Loren Market 79 twice with
  Event Square, Acheron 91, Ferea 112, Nixies Lake 113, Deep Dungeon 116–120, Swamp of Darkness 122, Kubera Mine 123,
  Abyss of Atlans 128–130, Scorched Canyon 131, Red Smoke Icarus 132, Temple of Arnil 133, Gray Aida 134,
  Old Kethotum 135, Burning Kethotum 136, Kanturu Underground 137, Ignis Volcano 138, Bloody Tarkan 140,
  Twisted Karutan 142, Kardamahal 143, Swamp of Destruction 144) and the built-in worlds 6, 38, 40, 56.
- **Skipped, not reachable by warp**: Santa Village 62, Duel Arena 64, world 82, Uruk Mountain 100, 69–72, the Arca
  class 92/96/101/111, 95, 110, 114, 115, 121, 139 (not in the Warps window), 145 (needs level 1650). "Loren Deep"
  refused (castle owners/union only). Recorded per class in `world-handler-coverage.json` (`capture`).
- Native comparison: camera within 0.007 in all; far plane equal except Vulcanus (live 3700, native 3257.8);
  primary terrain light exactly equal in 31/32 (Kubera Mine differs); range is the dominant static-field difference;
  Abyss 2/3 draw no native terrain (no tile textures in their folders).
- **Music 43/44**: both words hold `0x01af6848` = `data\music\iDoppelganger.mp3`; all 76 entries follow the static
  literal order. `0x06fba808` = `0x6973754d` at server select.

## Inputs for later lanes (local, never commit)

Under `~/Documents/MTM/mu-mac-tools/native/scratch/data-acq-002/`:

- `live/<capture>-obj.bin`, `-glob.bin`, `-light.bin`, `-mem-01cf15fc.bin` (world pair), `-mem-01cf15ec.bin`
  (weather), `-mem-06fce370.bin` (WorldTime), `-time.txt` and one window shot `<capture>.png` (3444 × 2160, Retina,
  title bar 32 points) for the 32 captures listed in the JSON (`capture` names, e.g. `63-vulcanus`, `79-loren-market`,
  `79b-event-square`, `123-kubera`, `6-arena`).
- `plain/EncTerrain<world+1>.plain` and `.hidden`: the plaintexts for `--objects-dir` (world 79 from `79-loren-market`).
- `tour.json`: the fidelity-tour manifest (game root = the free-runtime prefix's `C:\MuTheMatrix`, title bar 32).
  Rerun with `tools/python/bin/python scripts/fidelity_tour.py run <scratch>/tour.json --binary native/build/mu-world`
  (renders go to `~/Documents/MTM/mu-mac-tools/native/renders/data-acq-002/tour`, deleted after this lane).
- `live/music/`: the music array, the 4-byte read, the pointed strings and `names.txt`.
- `bin/`: the free-runtime session scripts (`login.sh`, `warp.sh` by Warps-row index, `cap.sh`, `batch.sh`,
  `music.sh`, `quit.sh`), for a later capture lane under the same rules.

## Follow-ups this enables

- RENDER-WORLDS for the captured classes with all three primary methods missing: 91, 112, 113, 116–120, 122, 123,
  128–138, 140, 142–144 now have a populated original capture and an image/object/light baseline. The
  largest object populations: Kanturu Underground 12,679, Temple of Arnil 9,402, Swamp of Destruction 8,988,
  Deep Dungeon 5 8,494.
- RENDER-WORLDS-G (Vulcanus, 0 field differences; far plane 3700 missing natively; bone texture and brazier fire)
  and RENDER-WORLDS-I (Loren Market) can rerun their image checks against `63-vulcanus` and `79-loren-market`.
  G's Santa Village, H's Duel Arena/world 82 and I's Uruk Mountain still have no capture.
- Native terrain: Abyss of Atlans 2/3 texture-folder mapping; Kubera Mine primary light.
- AUDIO: done by AUDIO-002F (merged #243), which consumed this read: index 44 = iDoppelganger in
  `client-audio.md` and the Doppelganger music manager. No other audio state was read.
- Not acquired: effect/particle/joint/sprite pools, RNG phase, emitter-window or weather transitions.

## Checks

See the PR for the gate. New portable test `tests/test_world_captures_2.py` (4 tests);
`scripts/world_handler_coverage.py` passes with the regenerated view (48 classes, 288 addresses).
