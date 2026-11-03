# APP-REFRESH-002

Implementation handoff, 2026-10-29. Worktree `worktrees/app-refresh-002`, branch `claude/app-refresh-002`, built
from origin/main `52aa5c2` (#274). The owner asked to stop early, so this build does **not** include #275
(RENDER-ITEMS-002M) or #276 (RENDER-JOINTS-001). The steward was still gating both at build time. Offline only:
no original client, launcher, live read, account, network or protection work. No source change was needed.

## Installed state

- `~/Applications/Mu The Matrix Native Preview.app`: `MUNativeCommit` 52aa5c2, version 0.1 (1), real ABI-3 Ruffle
  from `scratch/polish/libmugfx.dylib`. Strict deep signature and `--check-bundle` pass.
- Rollback: `~/Documents/MTM/mu-mac-tools/native/rollback/app-refresh-002/`. It holds the APP-REFRESH-001 app
  (commit 89a6ed9) as a zip (11 MB) and `settings.json.before`. To roll back, unzip the app into `~/Applications`
  and restore `settings.json`.
- `settings.json` now selects `~/Library/Application Support/MuTheMatrixNative/APP-REFRESH-002/Native Data`.
  The APP-REFRESH-001 folder and the legacy `Native Data` folder are unchanged.

## Native Data inputs (staged in `scratch/app-refresh-002/stage`, imported by the app's own `--setup`)

Every component carries a `native-data.manifest` that `mu-native-data check` accepts against the installed
main.exe. The root manifest was written by setup.

- `lang/` (29): the 27 APP-REFRESH-001 tables (including enchant/legendary for the item glow colours), plus
  `mapeffects.tsv` and `muuneffects.tsv`. Those two were re-exported with `live_effect_table_to_plain.py` from
  RENDER-EFFECTS-008's `live/s2-lorencia-fxt.bin` and are byte-identical to its `plain-s2-lorencia` copies.
  The manifest was rewritten incrementally with that snapshot as input 3. The runtime reads `mapeffects.tsv`
  from `MU_LANG_DIR` (`mu_map_effects_load_default`). `muuneffects.tsv` has no native consumer yet.
- `objects/` (47 worlds, 94 files): APP-REFRESH-001's 16 worlds, plus DATA-ACQ-002's 31 worlds. Those 31 were
  re-exported with `live_objects_to_plain.py --installed ... --main-exe` from `data-acq-002/live/*-obj.bin` and
  are byte-identical to `data-acq-002/plain`. `79b-event-square` was skipped because world 79 comes from
  `79-loren-market`.
- `sound/audio-tables.tsv`: regenerated with the current `extract_audio_tables.py` (pinned captures), so the
  music rows match AUDIO-002D..F (76 music rows; 75 lines differ from APP-REFRESH-001's table). The
  `audio-002f/music-read` read is validator evidence (`MU_SNAPSHOT_DIR`), not a runtime input.
- `gfx/`: 179 movies converted by the bundled gfxconvert from the installed game.

## Smoke (isolated logs, settings and `--no-store`; `PATH=/nonexistent`)

- Installed app `--smoke --backend gl --frames 300`, with and without `--audio`: ok, reaches the world (4 -> 6),
  Apple M5, guard 0 connects/inet/lookups denied, plan notes empty.
- Worktree build, windowed (`--auto --hold 6 --input-script`, `shot:` captures):
  - Login and GFx character select work.
  - Lorencia: walk works, the Chaos Goblin NPC dialog opens, and numeric casts drain mana.
  - Inventory, character and options keys work, and chat text is sent.
  - The Warps window (M) lists rows, and the Help window opens with Ctrl+H ("installed rows loaded").
  - Deep Dungeon 3 (dragon-head fires visible) and Abyss of Atlans 2 (terrain and objects) were entered through
    session files whose `join` line places slot 1 at gates 563/618. The Warps rows need levels 770/925, above
    the demo hero's 400.
- Headless GL drive of the bundled client with the app plan: 1 kill, 1 drop, 1 Alt toggle. **Pickup was not
  completed** (`space_picks 0`): the Space presses came after the item had landed out of reach. No selected-skill
  cast was counted (the script's right-click missed the target).
- No crash or unexpected error in any run. Audio was enabled in smoke but not measured (no PCM peak recorded).

Screenshots (local, not committed): `~/Documents/MTM/mu-mac-tools/native/renders/app-refresh-002/`
`1-deep-dungeon-3-fires.png`, `2-abyss-atlans-2-terrain.png`, `3-help-window-ctrl-h.png`, `4-warps-window.png`,
`5-lorencia-field-cast.png`.

## Next steps

1. When #275 and #276 have merged, merge origin/main in this worktree. Rebuild with
   `nice -n 10 make -C native/app -j4 MUGFX_LIB=~/Documents/MTM/mu-mac-tools/native/scratch/polish/libmugfx.dylib`,
   back up the installed app again, then reinstall with `ditto`. The APP-REFRESH-002 Native Data can be kept;
   run `--setup` only if an input changed.
2. Finish the journey proofs: pickup (Space right after the drop lands, near the hero) and a selected-skill
   right-click on a monster. Do Move-panel click travel Lorencia -> Noria -> Devias (rows at 1280x800 points
   x≈103, y≈193 for Lorencia, y≈206 for Noria, y≈259 for Devias), and measure audio PCM.
3. Helpers are in `scratch/app-refresh-002/bin/` (`run.sh` for windowed app runs, `hl.py` for headless runs with
   the app plan). The session files are in `sess/`.

## Follow-ups (not fixed here)

- `MU_NATIVE_EXTRA_ARGS` splits on spaces, so `--script "..."` cannot be passed and only `--input-script FILE`
  works. This only affects diagnostics.
- Windowed runs print no `input_state`/`input_items` report (headless only).
