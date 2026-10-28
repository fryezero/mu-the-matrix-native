# AUDIO-002 part 6 (AUDIO-002F): the music table, indices 43/44 and the Doppelganger manager

Branch `claude/audio-002f`, worktree `~/Documents/MTM/worktrees/audio-002f`, from `origin/main` `2e0bfa1`.
No original client, launcher or live service was run by this lane; it uses DATA-ACQ-002's finished read.
[Finding](../research/client-audio.md#audio-002-part-6-2026-10-28).

## Input and provenance

DATA-ACQ-002 (branch `claude/data-acq-002`) read the music table during its live session s2 on 2026-10-28,
17:28 local time, under the shared game lock it held. Its helper `music.sh` ran the read-only `memread`
right after the client window "Mu The Matrix - Powered by IGCN" appeared and a 20 s server wait, before
login: the client was at its pre-login screen, not in a world. Reads: `0x01cf1680` for `0x130` bytes (76
pointers), `0x06fba808` for 4 bytes, and each of the 72 distinct pointed strings, 512 bytes each.

| Local file | SHA-256 |
|---|---|
| `m-01cf1680.bin` (pin `music_table_read`) | `8bb024c22ccd96aace4d6ce425d82a80c21de06a32d60e6f0b7cc498aaf87a57` |
| `m-06fba808.bin` (pin `music_group_word`) | `5c105296380d7a760bed89b1d6b61d829f8fc43bba392a3dc164e6b55400eab8` |
| `names.txt` (index, pointer, filename) | `f515356f22c73696fb27ff3624d340071e0ba33844b8a3c8570914e87759c1eb` |
| the 72 `s-<addr>.bin`, concatenated in name order | `54d93860e80bb83615e65c530715cf1be8475cc00cf7f5714f614dabc2aadec6` |

The copy kept for later lanes is `~/Documents/MTM/mu-mac-tools/native/scratch/audio-002f/music-read/`
(300 KB). The pins resolve it as `audio-002f/music-read/...` under `MU_SNAPSHOT_DIR`
(`~/Documents/MTM/mu-mac-tools/native/scratch`). No read bytes or filenames are committed.

## Result

- **Indices 43 and 44 both point to `0x01af6848`, `data\music\iDoppelganger.mp3`.** All 76 pointers equal
  the literal addresses that `extract_audio_tables.MUSIC_LAYOUT` names in the pinned image data, so the
  whole layout is now verified: 72 distinct literals in order from `0x01af63ec`; 40..42 repeat 39
  (ImperialGuardianFort) and 44 repeats 43. Index 44 was the only unresolved entry before.
- **`0x06fba808` is not music data.** It is the first of three 0x18-byte MSVC `std::string` objects that
  the static initializer `0x008dc54b` builds from "Music", "Environment" and "Effect" (`0x01ab9ac8`,
  `0x01ab9ad0`, `0x01ab9adc`); FMOD init indexes them at `0x010aaf81` (`group*0x18 + 0x06fba808`) to name
  the channel groups. The live word `Musi` is the inline buffer of the first string, matching
  `validate_audio`'s existing group-name model.
- **Index uses.** The 158 references to the array in the pinned text all use a constant index. 72 indices
  are used. Index 43 has one use, `0x00e3062b` in `0x00e305ee`. Indices 10, 14, 44 and 52 have none in
  the captured code.
- **Doppelganger manager `0x00e305ee`.** It reads singleton `0x00f2bb92`, its object at `+0x78`
  (`0x00f2c111`) and that object's dword `+0x44` (`0x00e308e2`), and calls PlayMp3(43) when it is
  nonzero. It has no world test, no stop branch, and does not use `this`. Nothing in the captures calls
  it: no direct call, jump, immediate or data pointer. Its caller and the world/scene conditions are
  **not recorded**. So the per-frame selection does not invent a call. `mu_event_music(0x00e305ee)`
  reconstructs the body. The new `MU_AUDIO_DOPPELGANGER` known bit and the `doppelganger` field carry the
  input, and unknown input reports UNRECOVERED. `mu_audio_host_event_manager` and the script commands
  `eventmusic <field> <value>` / `manager <address>` let the owning event domain, or a script, run it.

## Checks

- New `scripts/validate_audio_music.py --require-live --mutations`, which uses the read pins: **4,291
  cases, zero mismatches, 10/10 mutants caught**. Families: doppelganger 4,056 (169 worlds × 12 input
  values × 2 object placements, original body under Unicorn, body SHA-256
  `eec56a377b865142b28aaeea2ca440ef96cc7be09bf9bf92534e7bd8e11713e0`); sites 158; table 76; group word 1.
  The six compiled C mutants cover the wrong index (44), `== 1`, `> 0`, a byte test, an invented stop and
  an invented world gate. Four layout mutants cover 44 unresolved, 44 as the next literal, 43 repeating
  39, and 42 with its own literal. Without the snapshot, the two live families are reported as skipped.
  The manifest row requires them.
- Portable tests: two new reconstructed checks (unknown/known Doppelganger input, a layout that names
  all 76 indices) and one native render test (silent while unknown or zero, PCM once set, bad commands
  refused). The private installed-audio test now also requires 76 resolved music rows with no missing
  file.
- Installed game (`~/Library/Application Support/MuTheMatrix/prefix/drive_c/MuTheMatrix`): all 72
  distinct files exist, matched case-insensitively as FMOD on Windows opens them. 65 are in `Data/Music`,
  six in `Data/Sound/Bosswar/BGM` and one in `Data/Sound/AquilasTemple`. Three `Data/Music` files are
  never named by the table: `BlazeKethotum.mp3` (the table names the `.ogg`), `lose.mp3` and
  `victory.mp3`. The re-extracted local TSV lists 76/76 names equal to the live `names.txt`.
- Native audio log (`mu-audio render`, `MU_AUDIO_CUE_LOG`, installed root, 13 segments of 400 ms):
  Lorencia safe tile 4 Pub, tile 0 main_theme; Devias church area Church, elsewhere Devias; Atlans atlans;
  Crywolf phase 0 crywolf1st; worlds 69/70 ImperialGuardianFort (indices 39/40); Karutan 80 Karutan_A;
  world 65 with Doppelganger input 1 and `manager 0x00e305ee` iDoppelganger (43), with input 0 nothing;
  140 BloodTarkan; 145 AquilasSanctuary. Every resolved request has result 2. The owner's Option.ini mutes
  music, so that render is silent by design. With `--no-options`, iDoppelganger decodes and plays,
  peak 0.8385.
- Unchanged: `validate_audio_events` (70,980 cases, 15/15 mutants) and the rest of the audio tests.
- Full gate: see the PR body and the status line.

## Remaining work

- The caller of `0x00e305ee` and the Doppelganger event input (`+0x44` of the `0x00f2bb92` `+0x78`
  object) belong to the Doppelganger event domain (SYS-EVENTS). This lane does not guess them.
- Indices 10, 14 and 52 have no captured use. The virtualised gap `0x01854279..0x018542c2`, the other
  music sites outside the frame block (siege 12/13, devil square 50/51, BossWar 66..71 and others) and the
  LIVE-PLAY FMOD comparison remain open.
