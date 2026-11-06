# APP-POLISH-005

Claude Opus 5.5 lane, 2026-11-06. Branch `claude/app-polish-005`, worktree `~/Documents/MTM/worktrees/app-polish-005`,
from main `7e6a9292`, merged `c1f91c27` (#312) and `9e1a0ce6` (#313 RENDER-EFFECTS-016). Offline only: no live
client, network, login, memory write or installed-app change. The installed Native Preview, the Wine play app and the
staged Wine app were not touched.

## What a player can do now

Select **Windleaf** (slot 2, Elf, level 320) in the offline demo. She arrives in the Lorencia field (182,128) with a
bow (Bow02). Hotkey **1** is Triple Shot and hotkey **2** is skill 2044, *Raining Arrow of Saturation*. Press 2 to select
it (the original onSelectSkill path through the bar). Then right-click a monster. The cast goes through the client's
checks (stat check `0x0109228f`, usability `0x010918c7`, IsSkillReady, mana/AG `0x01091692`). After that,
RENDER-EFFECTS-014/015's local ground volley runs: the 0x70a rain lands as 0x70c with its rings, stones and terrain
decals. No request is sent.

## Changes

- **Offline session** (`native/client/offline-session.{c,h}`): two new line types.
  - `skills FILE`: the learned skills and saved hotkeys per class, in the skills fixture's `list`/`keys` format.
  - `hero SLOT str= agi= vit= ene= cmd= [points=]`: the join stats (0x55 0x57) at the list entry's level.
  - Lines are checked: every stat once, 0..65535, slots 0..9, one line per slot.
- **Bundled data**:
  - new `native/client/demo-skills.txt`;
  - `demo-session.txt` gains `skills`, `hero 2 str=22 agi=1302 vit=20 ene=15 cmd=0 points=318`, and Windleaf's
    join moves from Devias 197,48 to the Lorencia field 182,128 (the demo monsters belong to Lorencia; a right-click
    cast needs one in reach);
  - the app bundles demo-skills.txt.
- **Hand-off to the fixture**: `shell.c` → `mu_world_rt_options` (`skill_demo`, `hero_stats`, `hero_points`) →
  `world_rt_skills_fixture_lines` (`parts/skills.c`, used by the actors/characters/skills fixture scenarios) →
  `skills_demo.h` (`at 1 skills file`, `use progress … level= points= str= …`).
  - `behaviors/progress.c` accepts `str/agi/vit/ene/cmd` (default: the class start stats).
  - Without a skills/hero line the lines are byte-identical to before (tested).
- **Equipment for the usability check** (`world_rt.c`, `world_gfx.c`, `world_gfx_skill.c`): the bar's env used to
  hold a demo sword (kind 1) for every hero. It now gets the chosen character's weapons from Item.bmd: model path →
  model index → record code and kind B (+0x251) in the record's own equipment slot. mu-world without equipment keeps
  the demo sword.
- **Report** (`input.c`, `main.c`): mu-client prints one line
  `{"effects":true,"skills","sounds","effects_created","max_live_0x70a","max_live_0x70c","max_live_rings",
  "decals","decal_quads","unsupported"}`.
  - `sounds` is mu-world's combat `sounds` counter (effect/skill sound cues).
  - The maxima are sampled every frame by the combat part's frame hook.
  - The line is printed headless and windowed, with or without an input script.

## Profile choice (evidence: [client-skills §14](../research/client-skills.md#14-the-offline-elfs-ground-skill-app-polish-005-2026-11-06))

The original's tables decide the choice:
- 2044's class map is Elf only;
- its record asks agility 1302 (stat check), a bow or crossbow plus arrows (weapon 5), mana 19 and AG 8.

Skill **2045 has no Skill(Kor) record** in this client, so it is unreachable through the bar (an absent record fails
the stat check); only 2044 is offered.

The profile reuses the existing demo Elf (Windleaf, 320, Bow02 = item 0x801, kind B 8, slot 0, in the arrow table).
Her stats follow the fixture's own DEMO rules: Elf start 22/25/20/15 and five points per level, so 1,595 points at
level 320, with 1,277 of them on agility. A test checks this arithmetic. No check, formula, damage or combat rule
changed. The Dark Knight path is unchanged (skill 19 right-click cast still ok).

No Unicorn comparison was added: no original routine was ported. The checks are the verified ones of
NATIVE-SKILL-002 and SESSION-SKILL-001; this lane supplies fixture data and the existing Item.bmd fields
(kind B, slot: verified in client-item-attributes).

## Proofs (own build, final code `f2b847ed`)

Bundled session, Windleaf. Flow: login → character select row 2 → key 2 → right-click.

| Run | Cast | Effects | Max live 0x70a / 0x70c / rings | Decal calls (tiles) | Sound cues | Unsupported |
|---|---|---|---|---|---|---|
| Headless, 220 frames, GL 1504×936, wandering demo monsters, click on the Budge Dragon | `skill 2044 at actor 10: ok` | 121 | 1 / 11 / 66 | 1,524 (56,348) | 2 | 0 |
| Windowed (mu-client window, 22 s, 431 frames), still-placement copy, click on the Bull Fighter | `skill 2044 at actor 8: ok` | 121 | 1 / 11 / 66 | 1,504 (55,880) | 2 | 0 |
| Before this lane (same flow at `f917b16a` without the hero line: private test) | `requirements` (refused) | 0 | 0 / 0 / 0 | 0 | 0 | – |

- These numbers agree with APP-REFRESH-006's mu-world 2044/Bow01 scene: 121 effects, 11 / 66 maxima, 2 cues.
- Unsupported is now 0 because #313 (RENDER-EFFECTS-016) supports 0x70c's Fire06 stones.
- Decal calls count every drawn frame (mu-world sampled every 5th frame), so they are not comparable one to one.
- The windowed run used a scratch copy of the bundled placement with `wander` removed: the monsters wander on
  wall-clock steps, so a frame-scripted click in a window cannot hit them reliably. The demo monsters were not changed.
- The cast went through `mu_skill_book_cast` (`skill_casts` 1, refused 0) and the rest of the run is unchanged.

**Window-only PNGs** (client framebuffer captures through the `shot:` action, local, never committed):
`~/Documents/MTM/mu-mac-tools/native/renders/app-polish-005/`:
- `1-hotkey2-selected.png`: hotkey 2 selected on the bar;
- `2-rain.png`: frame 125, the rain;
- `3-rings-decals.png`: frame 150, landing rings and crater decals.

## Checks (TEST BUDGET; no lane gate)

| Check | Result | Wall time |
|---|---|---|
| `nice -n 10 make -j4` (top level, at `f2b847ed`) | ok | 13.7 s (incremental) |
| 15 unit modules at `f2b847ed` with private env (`test_app_polish5` new, `test_native_app`, `test_session_skills`, `test_native_shell`, `test_fixture_hero`, `test_session_core`, `test_layout_session`, `test_fixture_scenarios`, `test_input_router`, `test_native_gfx3`, `test_native_skill`, `test_world_parts`, `test_native_combat`, `test_app_polish2`, `test_app_polish`) | 150 tests, 0 failures, 7 skipped (5 need an in-tree mugfx build, 2 test_native_skill installed-table cases) | 165.6 s |
| `test_app_polish5` alone (4 portable + 2 private mu-client runs) | 6/6 | 33 s |
| Byte-identity sweep, DATA-ACQ-002's 32 tours, default draw: base main `9e1a0ce6` vs `f2b847ed` | 64 PNG + 64 object/light dumps byte-identical; the 32 native.jsonl files identical after normalising the output path | 48.7 s + 48.9 s |
| `validate_session_party`, `validate_app_polish2` (no mutants, cached) at `f2b847ed` | 200 + 1,028 cases, 0 mismatches | 0.8 s + 2.8 s |
| `scripts/audit_repository.py` (4 new files) | 1,969 staged files, 0 rejected | 19.3 s |
| Headless / windowed proofs | above | 11.6 s / 22.8 s |

- **Steward validators:** `validate_session_party`, `validate_app_polish2` (no mutants), ran at `f2b847ed`.
  - Env: `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`, `MU_SECTION3`, `MU_EVIDENCE_DIR`.
  - TEST-SPEED-004 had not merged. `--list-affected origin/main` picked 103 rows, 91 of them only because their
    scripts quote "native"/"client".
  - Rows that build or read the changed sources: `validate_session_party` builds `mu-session` (fixture progress.c);
    `validate_app_polish2` reads functions of `world_gfx.c` (the extracted ones did not change).
  - The gen_domains rows: `gen_domains.py` reads only behaviour names, which did not change.
  - The render_effects/worlds rows quote `reconstructed/combat`'s combat.c, not `parts/combat.c`.
  - No row compiles `native/client` or `native/world`.
  - No mutants were needed: no validator or validated routine changed.
- **Unit-module selection (6b grep):** `skills_demo`, `use progress`, `mu_world_rt_options` hosts (built by
  `make -C native`), `wg_skill`, `demo-session`, `parts/*`, `input.c`, `requirements`.
- **Private test env:** `MU_NATIVE_DATA_DIR` = APP-REFRESH-006 Native Data (read-only), `MU_GFX_LIB` = scratch
  libmugfx.
- **Load:** several steps started at load 10–14. Two short steps started at 16–20 without waiting: the first
  test_app_polish5 run and the first windowed attempt.

## Limits

- HP on the HUD reads 1100 for Windleaf, from the world's combat HP input (APP-POLISH-003's DK value). The Elf's
  progress maxima are DEMO formulas. This lane adds no vitals profile for other classes.
- Arrows: the usability env's arrow query has no inventory feed, so it answers 1 (the existing default).
- Combat arrows use `bow_item` 0 (Bow01). Bow02 has the same arrow model case (`0x12e6/0x12e7`), so nothing looks
  different.
- Not compared with an original-client capture of 2044.

## For APP-REFRESH-007

- The bundled session now sends Windleaf to the Lorencia field with 2044 on hotkey 2.
- After a reinstall, check: character select row 2 → key 2 → right-click a monster near 182,128.
- Read the client log's `{"effects": …}` line for sound cues and ground-skill counts.
- Native Data can stay as it is (no export input changed).

## Cleanup

Scratch `native/scratch/app-polish-005` (helpers `hl.sh`/`runw.sh`, runs, tours) and the base worktree
`worktrees/app-polish-005-base` are deleted after the ready line. The three PNGs stay under `renders/app-polish-005`.
The worktree stays until the steward merges.
