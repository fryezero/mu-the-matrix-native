# Scene flow: title, login, character select, world

`mu-client` plays the client's scene states offline: the title (ten startup frames), the login scene with
the server list and the OFFLINE DEMO panel, the character select, the loading screen and the world. Enter
and Esc move between them exactly as the client's SceneFlag values 2 -> 3 -> 5 -> 4 -> 6 and 6 -> 5 do.

## Sub-features

- `flow-title` the title shows its ten frames and hands over to the login scene by itself.
- `flow-login` choose a group and a server, type account and password (Tab switches fields), Enter logs in;
  the offline session accepts any input; Esc returns to the servers, Esc again quits.
- `flow-select` Left/Right (or 1-5) choose a character, Enter plays, Esc returns to the servers.
- `flow-world` loading, then the world with the chosen character at the session's join tile; Esc returns to
  character select; Enter from there enters the world again.
- `flow-auto` the whole journey without a script (`--auto`).
- `flow-window` the same flow in a real SDL window with a screenshot.

## How to get to it (user POV)

- Start `mu-client --game-root ROOT --session SESSION`; the title plays unattended.
- Login: click a server group button, then a server button, type, press Enter. Shortcut: Enter with no
  server chosen picks the first open server and shows the panel.
- Character select: Right/Left (or a digit) then Enter; Esc goes back to the servers.
- World: Esc returns to character select; Enter there re-enters the world.

## Driving it with run-tool.sh

Preconditions:

- `RUN` from `new-run.sh`, `doctor.sh "$RUN"` OK, `V=.claude/skills/verify-mu-native/scripts`.
- Every headless command below carries the same base:
  `--game-root "$RUN/root" --session "$RUN/session.txt" --headless --backend gl --no-audio --no-store --width 320 --height 240`.
  Write it out each time; do not bundle it in a shell variable (zsh does not split `$VAR` into words).

- **Whole flow.** Let it play. Run
  `$V/run-tool.sh "$RUN" flow mu-client --game-root "$RUN/root" --session "$RUN/session.txt" --headless --backend gl --no-audio --no-store --width 320 --height 240 --frames 300 --every 25 --out-dir "$RUN/proof/flow" --auto`.
  Exit 0. `$V/summary.py "$RUN/proof/flow.stdout" transitions visits logins server hero_slot hero_class world presents`
  gives exactly seven transitions in this order: `2 -> 3 ... title done`, `3 -> 5 ... login accepted (offline
  session), character list requested`, `5 -> 4 ... Enter: join answered by the offline session`, `4 -> 6 ...
  loading done`, `6 -> 5 ... Esc: back to character select`, `5 -> 4 ...`, `4 -> 6 ...`; `visits` `{"3": 1, "5": 2, "6": 2}`;
  `logins` 1; `server` `[0, 0]`; `hero_slot` 1 and `hero_class` 34 (0x22 Bravo, because `--auto` presses Right once);
  `world` 0; `presents` 12 (ten title frames and two loading frames). stderr lists each `frame N (scene S): ACTION`.
- **Scripted login and slot 0.** Enter three times. Run
  `$V/run-tool.sh "$RUN" flow-slot0 mu-client --game-root "$RUN/root" --session "$RUN/session.txt" --headless --backend gl --no-audio --no-store --width 320 --height 240 --frames 80 --script "10:enter 14:enter 30:enter"`.
  `transitions` are the first four of the list above; `hero_slot` 0, `hero_class` 0 (Alpha).
- **Login needs input.** One Enter only. Run
  `$V/run-tool.sh "$RUN" flow-panel mu-client --game-root "$RUN/root" --session "$RUN/session.txt" --headless --backend gl --no-audio --no-store --width 320 --height 240 --frames 40 --script "10:enter"`.
  Summary `scene` 3, `logins` 0, `server` `[0, 0]`: the panel is shown, nobody is logged in.
- **Esc in character select.** Run
  `$V/run-tool.sh "$RUN" flow-esc mu-client --game-root "$RUN/root" --session "$RUN/session.txt" --headless --backend gl --no-audio --no-store --width 320 --height 240 --frames 60 --script "10:enter 14:enter 30:esc"`.
  `transitions` end with `5 -> 3`; `protocol` 0.
- **Esc twice at login quits.** Run
  `$V/run-tool.sh "$RUN" flow-quit mu-client --game-root "$RUN/root" --session "$RUN/session.txt" --headless --backend gl --no-audio --no-store --width 320 --height 240 --frames 200 --script "10:esc 20:esc"`.
  Summary `frames` below 30 and `scene` 3.
- **Real window.** Drive the window for a few seconds and capture it. Run
  `$V/run-tool.sh "$RUN" flow-window mu-client --game-root "$RUN/root" --session "$RUN/session.txt" --no-audio --no-store --width 640 --height 400 --seconds 6 --title "verify-mu-native" --out-dir "$RUN/proof/flow-window" --script "10:enter 14:enter 30:enter 60:shot:world"`.
  A window titled verify-mu-native appears and closes by itself; stderr has the scene changes and
  `capture .../flow-window/world.png (W x H)`; stdout is one row `{"frames": N, "seconds": ~6, "scene": 6, ...}`
  with N above 60; `world.png` exists.
- **Proof.** `ls "$RUN/proof/flow"` has `frame-0000-s2-present01..10.png`, `frame-NNNN-s3-frame.png`, `-s5-`,
  `-s4-` and `-s6-` files. Open the s3 frame after Enter (the OFFLINE DEMO LOGIN panel with Server, Account,
  Password lines), an s6 frame (the OFFLINE DEMO banner, "world: click to walk, wheel zooms, Esc returns to
  character select", the hero name Bravo or Alpha over noise-textured ground). The listing of
  `~/Library/Application Support/MuTheMatrixNative` is unchanged.

## Gotchas

- Exit 2 with the usage text on stderr means the argument list reached the program wrong: a variable that
  held several flags was not split (zsh), or a flag is missing its value. Spell the arguments out.
- World 95 (the client's 0x5e) is the login backdrop; without it the login stays black and `status` says
  `login world: world 0x5e ... missing or undecodable`. `make-root.py` writes it.
- Interface textures (`lo_back_*`, `MU_TITLE`, `FontInput`, the logos) are missing on the synthetic root:
  dozens of `texture 0x.... ...: missing` lines on stderr are expected, and the title frames show only the
  webzen logo.
- Script frame numbers are the headless frame counter. An action only takes effect in the scene that is
  active at that frame (e.g. `30:enter` must land in scene 5); read the stderr line `frame N (scene S): ACTION`.
- A windowed run advances with the display, not the virtual clock; the frame rate drops when other GL work
  runs on the Mac at the same time. If stdout shows fewer frames than the last scripted frame, the `shot:`
  never happened: run it alone or raise `--seconds`.
- Headless GL needs the offscreen context the doctor checks; `--backend soft` has none of that.
- The character-select frame on the synthetic root is nearly black apart from the banner: `Player.bmd` is a
  skeleton without meshes and there are no class part models.
- `--auto` in the GFx character list (converted movies and libmugfx) clicks rows instead of pressing Right;
  the synthetic root has no movies, so the legacy list is used.
- Without `--no-store` a windowed run writes offline-created characters to
  `~/Library/Application Support/MuTheMatrixNative/offline-characters.txt`.
- The window `shot:` capture is drawable-sized (Retina: 1280 x 960 for a 640 x 400 window).
- The windowed program does not create `--out-dir`; `run-tool.sh` does. A bare `mu-client` invocation
  reports `cannot write .../world.png` when the directory is missing.
