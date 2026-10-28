# World input

Physical SDL events and version-1 input files enter the same world router. The
[coverage table](../../../../docs/research/client-input.md) separates available native actions from
original windows that still have no migrated view/domain.

## Sub-features

- input-cast: numeric demo cast without GFx; bar selection with GFx.
- input-right: selected-skill right-click through the skill checks and combat adapter.
- input-pick: Space requests and completes a synthetic dropped item's pick-up.
- input-panels: keys reach existing views; unsupported panels report their recovered name and -1.
- input-ime: chat preedit, candidate digit and UTF-8 commit; candidate digit causes zero combat casts.

## How to get to it (user POV)

Enter the world in mu-client. Right-click an actor to cast the selected skill. Space picks a nearby
eligible item, Alt toggles labels. I/C/U/A/T/M/F/O reach inventory, character, imprint, master tree,
quests, move, friends and options. Ctrl+A/J reach the existing fourth/fifth-tree views. P/S use the
personal-store adapter with inventory open. Enter opens chat. The original candidate movie is not played;
macOS owns candidate selection.

## Driving it with run-tool.sh

Preconditions: the normal skill build/doctor steps passed. For combat proof, extend the new run's own
synthetic root using `test_native_items.write_items_world`. Its Player.bmd has the combat actions and its
Item.bmd contains a synthetic drop table. Put `actor 3 121 120 0 label spider` in `$RUN/placement.txt`.
For selected-skill/UI proof, use the authored `test_native_skill.write_lang` tables in `$RUN/lang`, add
`QUESTS` and `STRINGS` from `test_native_quest` as quests.tsv/queststrings.tsv, and write this skill demo:

```text
list 0 19 22 41 344 9 14
keys 0 19 41 22 344 -1 -1 9 14 -1 -1
```

`MU_INPUT_MOVIES` and `MU_INPUT_GFX_LIB` must name read-only, locally converted movies and a real compatible
libmugfx. Empty files and the stub library do not prove a rendered journey. The synthetic terrain/actor
assets remain the run's own files. Record those two private input paths and their digests in the proof.

- Right-click and pick-up: write `$RUN/input.txt` with the following schedule, then run the command below.
  At 640x480 the authored actor projects at 361,237. The final `input_state` has `skill_casts >= 1` and
  `pickups >= 1`; `input_items` has a kill/drop. Look at the frame PNGs and the cast/action log.

```text
10:enter 14:enter 30:enter
40:move:361,237 42:rdown:361,237 43:rup:361,237
200:key:32 250:key:32 300:key:32 350:key:32 380:key:32 395:key:18
```

```sh
MU_LANG_DIR="$RUN/lang" MU_SKILL_DEMO="$RUN/skill-demo.txt" MU_GFX_LIB="$MU_INPUT_GFX_LIB" \
MU_GFX_LOG="$RUN/proof/input.gfx.log" \
$V/run-tool.sh "$RUN" input mu-client --game-root "$RUN/root" --session "$RUN/session.txt" \
  --headless --backend gl --no-audio --no-store --width 640 --height 480 --frames 400 --every 15 \
  --combat --placement "$RUN/placement.txt" --gfx "$MU_INPUT_MOVIES" --input-script "$RUN/input.txt" \
  --out-dir "$RUN/proof/input"
```

- Numeric cast: omit `--gfx` and use a file containing the scene flow followed by
  `40:move:361,237 41:ldown:361,237 42:lup:361,237 45:key:49`. Check `input_state.casts > 0`.
- Panels: replace the post-join schedule with each available key twice, keeping the same preparation.
  Use `144:key:I 145:key:P 146:key:P 147:key:S 148:key:S 149:key:I` for the store precondition.
  Read each movie's SetVisible/open/close invokes in `MU_GFX_LOG` and inspect its captured frame.
  Run unavailable keys too and retain their named refusal; a refusal is coverage, not a working panel.
- IME: with the interface open and other panels closed, use
  `152:key:13 153:compose:1:%E4%B8%AD 154:key:49 155:text:%E4%B8%AD 156:key:13`.
  The chat open/commit events must be present; `input_state.casts` and `skill_casts` stay zero.

## Gotchas

- Files use the shared parser. Short inline `--script` schedules remain accepted, but the native-data
  path guard can reject a very long inline value as an overlong filename. Use `--input-script`.
- A key's positive consumed result alone does not prove a panel. Verify its view state, invokes and PNG.
- A bar digit selects a skill when GFx is present. Numeric casts without GFx retain the old demo policy.
- The skill record and learned/saved bar are separate fixtures. Missing either can cause a legitimate refusal.
- Frame indices are front-end iterations, not server WorldTime or a cross-client timing comparison.
- The original IME.swf, missing windows and authoritative mount/helper/shop controllers remain in the
  coverage table. This recipe never supplies their state or claims them as verified.
