# Client audio: FMOD boundary, sound table, music and volume (NATIVE-AUDIO-001)

Target: main.exe SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`, restored
text `2bd5f2e9...fc93724` (capture09) and second image section `c985e2e6...0a672f` (capture10). Labels:
**verified** means the client instructions ran in Unicorn and the authored C produced the same boundary
calls; **static** means an instruction reading that was not executed; **inferred** means a conclusion from
indirect evidence. Names are investigator choices.

## Audio stack

- **Static.** The client plays all audio through FMOD Ex. The 35 imports at IAT `0x01a7cac4..0x01a7cb4c`
  (thunks `0x018eb289 + 6k`) are stdcall methods with `this` on the stack. The IAT dump of the Wine run lists
  them without a module name (values `0x13f1xxxx`); no FMOD DLL is in the installation. Error strings from
  `fmod_errors.h` (FMOD Ex 4.x, e.g. `fmodex.irx`) sit at `0x01ab7c18..`.
- **Observed.** The Mac CrossOver trace `runtime/mac32/run12-loaddll.log` shows `dsound.dll`, `mmdevapi.dll`
  and `winecoreaudio.drv` loading at runtime. The client never calls DirectSound itself: the dxguid
  DirectSound GUIDs at `0x01af8e8c..` have no code references, and FMOD selects the DirectSound output
  (`setOutput(6)`).
- **Static.** A classic mmio WAV reader/writer class (vtable `0x01a8059c`, `0x00a6c69d..0x00a6cc98`, PCM
  only, "UnSupported Wave Format!") is linked but its constructor has no callers. WAV loading at runtime is
  FMOD's.
- **Inferred.** Method identities come from argument shapes, constants and the FMOD Ex 4.2x/4.3x example
  init sequence (5-argument `getDriverCaps`). Thunk order: Channel::stop, setCallback, setUserData,
  getUserData, Sound::release, System_Create, System::release, setOutput, getNumDrivers, getDriverInfo,
  getDriverCaps, setSoftwareFormat, setDSPBufferSize, setSpeakerMode, init, close, update, createStream,
  createSound, createChannelGroup, playSound, getMasterChannelGroup, Channel::setPaused, setPriority,
  setChannelGroup, setMode, ChannelGroup::release, setVolume, getVolume, setPaused, getPaused, setMute,
  getMute, stop, addGroup. `getMute`/`getPaused` write a one-byte C++ `bool`.

## Sound system (verified)

`0x010aad03` creates the system and picks the output: no driver gives NOSOUND (2), otherwise DirectSound
(6), then the driver's speaker mode, `setDSPBufferSize(1024, 10)` when caps contain HARDWARE_EMULATED, and
`setSoftwareFormat(48000, PCMFLOAT, 0, 0, LINEAR)` when the driver name contains "SigmaTel". `init(16, 0,
extra)` is retried once with stereo after `FMOD_ERR_OUTPUT_CREATEBUFFER` (0x3a). Three channel groups are
created under the master group: Music (0), Environment (1), Effect (2). The names come from a static
initializer `0x008dc54b`. **16 channels.**

Every file is opened with mode `0x08000029` (LOWMEM | HARDWARE | 2D | LOOP_OFF): there is **no 3D or
positional audio**. Sound effects are opened as streams (`createStream`), music as samples
(`createSound`). Opened files are shared through a cache keyed by path with a **`_stricmp` comparator**:
paths that differ only in case share one FMOD sound. The sound is released with its last owner, which also
drops the cache entry. Playing (`0x010aaffb`) starts paused, sets the group, sets priority = group index
(music 0, effects 2), sets `LOOP_NORMAL` when looping, then unpauses; any failure stops the channel.

## Sound table (verified behaviour, static extraction)

- `SND_Load 0x00a6ab76(id, path, channels, 3d)` registers an id once (`std::map` at `0x01d1e018`). The third
  and fourth arguments, pushed by every caller (classic MU's number of buffer copies per sound, 1..4, and its
  3D flag), are **never read**: there is one FMOD sound per file and no per-sound copies. A failed open
  registers nothing.
- `SND_Play 0x00a6ac96(id, object, loop)` plays at most **one instance per id**: while the entry's playing
  flag is set the call returns without touching FMOD. The object argument is never read, so there is no
  distance attenuation and no pan. The channel goes to the Effect group with the entry as user data and the
  end callback `0x00a6ae37`, which clears the playing flag on `CALLBACKTYPE_END`.
- `SND_Stop 0x00a6ad76` stops the entry's channel (second argument ignored). `SND_Remove 0x00a6add6`
  erases the entry. Per-map releases (static): NPC ids 160..209 (`0x018089d8`), monster ids 210..449 and
  764..793 (`0x0180b0aa`), re-registered by `OpenNpc 0x01808a40` and `OpenMonsterModel 0x0180b0f4`.
- `scripts/extract_audio_tables.py` decodes 1,514 of 1,515 SND_Load sites (one computed id in a loop at
  `0x01848102`): 1,366 ids, 1,318 distinct paths, 136 ids registered by more than one loader. The table
  stays local.
- `0x01848557` is a one-time rename of Korean-named sound and music files to their English names, not the
  table.

## Music (verified behaviour; table placement inferred)

Formats: `Data/Music` holds 64 MP3 and 4 Ogg Vorbis files, `Data/Sound` 1,358 WAV (PCM 8/16-bit at 6,116 to
55,400 Hz, one MS-ADPCM), 13 MP3 and 6 Ogg files; FMOD opens all of them by path.
`PlayMp3 0x0120f602(path)` does nothing when the current music has the same name by `_stricmp`; otherwise
it stops the Music group, releases the old sound, opens the new file with `createSound` and plays it looped
on the Music group. `StopMp3 0x0120f5a0(path)` stops and releases only when the name matches. Paths come
from a 76-entry array at `0x01cf1680` in the packed `.data` section, which no capture contains. Its 72
literals sit in order at `0x01af63ec`. Index use pins the placement: 0..39 follow the literal order; 40..42
repeat ImperialGuardianFort (worlds 70..74 managers); 43 is iDoppelganger; **44 is unresolved and unused**;
45.. continue with Karutan_A. Cross-checks: the ambient sound played next to each index (Nars, NixiesLake,
Labyrinth, Arenil, AsherAida, IgnisVolcano, Tarkan desert, TwistedKalutan, Aquila) and the BossWar routine
`0x00985660`, which uses 66..71.

The frame routine's block `0x0185280c..0x01854498` (**verified**) runs every 40 ms frame in scene 6. A
switch on the world starts ambient loops: Lorencia wind (rain too when raining, both stopped on the pub
tile), Dungeon and Deep Dungeon, Devias wind except tiles 3 and 10+, Noria wind plus a bird when
`rand() % 512 == 0`, tower, water for Atlans/Abyss, desert for Tarkan, heaven for Icarus, Karutan, Acheron,
Uruk Mountain fire/clean areas from the terrain attribute bits 0x800/0x1000, and the season worlds. Then
every loop and track that does not belong to the current world is stopped, and the field music is chosen:
Lorencia safe zone (Pub on tile 4, main theme otherwise), Devias safe zone (Church inside x 0xcd..0xd6,
y 0x0d..0x1f, Devias otherwise), Noria safe zone, Dungeon/Deep Dungeon, Atlans/Abyss, Icarus, Tarkan, Lost
Tower, Kalima 24..29 and 36, world 31 (huntingground), Aida 33, Kanturu 37, Elbeland 51, Swamp of Calmness 56/144.
Event worlds delegate to their own managers (Crywolf `0x00db3e26`, Kanturu `0x00e8e857`/`0x00e84474`,
Balgas `0x00d557af`, cursed temple, Raklion, Santa village, Imperial Guardian, Karutan, Acheron and
others); they are recorded, not reconstructed. `0x01854279..0x018542c2` jumps into protector-virtualised
code and stays unrecovered.

## Volume options (verified)

- `Data/Sound/Option.ini` is JSON (`ChannelMutes`, `ChannelVolumes` for Music/Environment/Effect,
  `MasterMute`, `MasterVolume`). It is loaded after init (`0x010ab7e0`) and applied (`0x010ab480`: master
  mute, master volume, then each group's mute and volume). Shutdown reads the groups back (`0x010ab506`) and
  writes the file (`0x010ab573`; doubles by `0x00943757` as `%#.16g` with jsoncpp-0.5 zero trimming,
  static). The installed file (music 0.4) round-trips byte for byte; the reader itself was not executed.
- **OpenWorld overrides the music volume on every world load**: `0x018290be..0x018293a6` sets the Music
  group to 1.0 for 57 listed worlds (events and season maps) and 0.4 for all others.
- The options window mutes the Music group from its music check box and sets the Effect group to
  `level / 9.0f` from its slider (0..9), or 0 when effects are switched off; reading back uses
  `(int)(volume * 9 + 0.5)`. Group gains multiply with the master group; a mute silences.
- **Static.** Nothing plays on the Environment group: `0x010aaffb` is called only from SND_Play (Effect) and
  PlayMp3 (Music).

## Verification

`scripts/validate_audio.py` (`--random 2000`) runs the client code over the pinned captures with a
recording FMOD stand-in; modelled parts are listed in its docstring.

| Check | Client code | Result |
|---|---|---|
| frame | `0x0185280c..0x01854279` and `0x018542c2..0x01854498` | 2,407/2,407 cases, 169,621 events, 167 worlds |
| sensitivity | C given a different world | 232/232 detected |
| openworld | `0x018290be..0x018293a6` | 277/277 worlds |
| manager | SND_*, callback, PlayMp3/StopMp3, create/play/cache/settings | 2,023/2,023 scripts, 79,176 FMOD calls |
| init | `0x010aad03` with scripted drivers and failures | 107/107 scripts, 1,446 calls |
| settings | UI conversions `0x00f2fc2e`, `0x00f2fe04`, `0x00c764bd` | 9,153/9,153 |

Pinned body digests are in the report. Never-written stack slots read by `push m32` (MSVC empty tag
objects) are permitted; the STL-heavy checks treat the zero-filled stack as defined, while uncaptured
globals and heap bytes stay strict. Frees are no-ops in the bump allocator.

## Native module

`native/core/mu_audio.c` implements the FMOD table with an offline-decoding software mixer; the
reconstructed logic runs on it unchanged. WAV (PCM 8/16/24/32, float, MS-ADPCM, IMA-ADPCM) decodes through
`mu_wav.c`; all 1,358 installed WAV files decode. MP3/OGG decode through AudioToolbox on macOS. Engine
choices (not client facts): mono feeds both channels at full level, linear interpolation, end callbacks at
`System::update`, and the oldest least important voice is stolen beyond 16. `native/build/mu-audio`
lists the table, decodes files and renders scripts; `mu-audio-live` plays scripts through SDL2. Local
renders: `~/Documents/mu-mac-tools/native/renders/audio/`.

## Gaps and next steps

- A fixed-scope capture of `0x01cf1680..0x01cf17b0` (and `0x06fba808`) would settle music indices 43/44.
- AUDIO-002 part 1 below reconstructs the frame-delegated event music managers, ordered monster/NPC
  registrations and three NPC voice fragments. The virtualised frame gap and other domains' SND_Play
  sites remain open.
- FMOD's own mixing, stealing and pan rules are unavailable; the engine's choices are listed above.

## AUDIO-002 part 1, 2026-10-27

Target and capture pins are the same as NATIVE-AUDIO-001 above. All new execution evidence is from the
existing Wine-restored captures, with synthetic state. No original client, launcher or live service ran.

**Verified event music.** `mu_event_music` reconstructs all 15 managers delegated to by the recovered frame
block. Their call order, play/stop choices and boundaries match 70,980 instruction cases, 4,732 per manager.
The comparison executes the original world predicates; the string lifetime, music pointer array and Kanturu
singleton getter are modelled. The 15 compiled planted mistakes are all caught, including wrong world/index,
reordered stops, a stop invented for Santa, the Raklion byte equality and a call invented in the empty manager.

| Client routine | Inputs and decision |
|---|---|
| `0x00db3e26` | Crywolf, world 34; byte `0x01ec90af` phases, result `0x01cf0e78`; music 17-20, result sounds 582/583 |
| `0x00e8e857` | Kanturu battle, world 39; singleton `0x009a6ef3` field `+0x7c`; music 24-26 |
| `0x00e84474` | Kanturu worlds 38/137; music 23 |
| `0x00d557af` | Balgas worlds 41/42; music 27/28 |
| `0x00db7501` | Cursed temple object field `+0x14`; music 29/30; getter `0x00db747f` delegates here |
| `0x00e9e9c5` | Raklion world 57 and boss world 58; object byte `+0x24` equals 1; music 34/35 |
| `0x00e42ad0`, `0x00e92fc8` | Santa world 62, music 36, no stop branch; duel world 63, music 38 |
| `0x00dd306c`, `0x00dd8891`, `0x00dde543`, `0x00de5467` | Imperial Guardian worlds 69, 70, 71, 72-74; indices 39-42; no stop branches |
| `0x00e6dd22` | Empty body in this capture |
| `0x00e189e4`, `0x00d73c38` | Karutan worlds 80/81, indices 45/46; Acheron worlds 91/92, index 47 |

The native host expands the existing delegate event in place. The old frame family remains unchanged and
still compares its delegate boundaries. The event state API has explicit known bits; the four state-dependent
managers report unrecovered input until their owning domain supplies it. World changes clear those bits.
The decisions are implemented; receiving those event states from service packets remains with the event lanes.

**Verified registration order.** `audio_registration_static.py` lifts ordered SND_Load sites from the constant
monster switches, the earlier model switch and NPC cases. `audio_registration.inc` contains only authored
call sequences with ids, source sites and legacy arguments. It contains no filenames or captured bytes.
The independent validator executes full OpenMonsterModel `0x0180b0f4..0x0181f25c` and OpenNpc
`0x01808a40..0x0180ae1e`, with the existing actor machine's model/file/string services. It compares every
sound call's site and arguments, rather than sorting ids. Result: 2,404 monster and 584 NPC cases, zero
mismatches; all four compiled mutants caught. Cases cover 601 monster types and 146 NPC model types,
worlds 0/39 and preloaded exits. A synthetic texture-flag array supplies OpenNpc's model `+0x34` read;
the first validator attempt lacked that array and stopped on model 2646. The corrected run requires all
machine checks, including return, defined reads and restored registers/SEH, before comparing calls.

The TSV extractor adds an optional seventh `site` column. Native registration resolves the exact site;
`SND_Load` keeps its existing first-successful-registration behavior. Tests reverse the two NPC paths for
id 160 in the TSV, register models in the opposite order, then check the actual PCM. Old TSVs remain
readable, but explicit per-model registration requires re-extraction with site provenance. Registration
APIs do not alter the still-unmigrated actor/model loader lane or invent monster viewport state.

**Verified NPC voice decisions.** Model cases `0xa0b`, `0xa06`, `0xa01` route at
`0x013b33ef..0x013b3410`. Fragments `0x013b53e4..0x013b540a`, `0x013b540f..0x013b5437` and
`0x013b543c..0x013b549c` choose sound 161 on signed rand remainder 64 = 0, sound 160 on remainder
256 = 0, and sound 160 for action 0/frame 5 through 10 with buff 0x1b absent. The bounded fragments,
not the whole MoveCharacter function, match 2,182 cases including negative random values, NaN and frame
edges; all three compiled mutants caught. Animation writes after the last fragment are excluded. The
selector is ready for the NPC/viewport lane; its character tick is not migrated here.

**Session cues and native log.** The hero's verified receive-handler sound already emitted MU_CUE_SOUND.
Its adapter now shares `domains/audio_cue.h` with quests. There are no SND_Play calls in the currently
reconstructed quest routines, so no new quest sound id is asserted. The quest sink recognizes the common
sound grammar before wrapping other lines as window cues. Independent audio cursors drain each attached
quest/session ring in both GFx and headless world tools, leaving window/effect readers untouched. These
rings can carry hero receive-handler cues too. The legacy `mu_progress` world demo remains a separate,
unmigrated tool facade as documented by SESSION-CORE-001; this task does not migrate that demo's state.

Set `MU_AUDIO_CUE_LOG=/absolute/path/audio.jsonl` before starting the native client or audio tools.
Each host appends `open`/`close` boundaries and ordered JSONL records with `audio:1`, host-local `seq`,
`time_ms` from its 40 ms audio frame clock, world, op, id, loop, result, cue sequence, handler, at_key and
session tick and registration source site. Scene music requests carry the pinned string-literal address
in `id` under `music_literal`/`stopmusic_literal`, so the shell can log track identity without filenames. For sound play, result 1 starts, 0 suppresses/fails, -1 is unresolved. Music/stop records
are requests, result 2 when resolved, not claims of an FMOD call or successful decoding. Registration
records put the source site in `site`; unrecovered records identify the missing input/routine in `id`.
Cue-loss records report the exact dropped count, including nonsound cues. Log-open failure fails audio
initialization. No paths, account data or runtime pointers appear in records. A future comparator must
expand requests through the verified SND/FMOD manager and align the independent frame/session clocks;
this log alone is not an original-versus-native FMOD comparison. No original FMOD log was captured here.

Seven native tests check handler-to-ring-to-PCM, shared adapter provenance, two independent readers,
once-only drain, exact 26/1,050 cue loss, suppression, silent drains, site order, explicit event state and
log-open refusal. Four additional portable checks cover event gates and NPC voice boundaries. Four synthetic world PNGs remain byte-identical with logging off/on, with 3,447 logged decisions
and 45 play requests in the enabled 40-frame run. The existing
native audio render hash remains `207036b711a07277a68466d736760c9440bab5d325ede5f90ddc298f18232897`.

**Unchanged families rerun.** Original audio: 2,407 frame cases, 277 OpenWorld cases, 2,023 manager scripts,
107 init scripts, 9,153 UI cases, all equal, with 232/232 world-perturbation controls detected. Hero audio:
600 walk, 600 trigger, 200 reset, 600 tile cases, zero mismatches; every existing negative-control variant
is detected. No old family or render/hash expectation was changed.

**Next exact read, not performed.** Under the game lock in a separately authorized live-capture task,
read `0x01cf1680` for `0x130` bytes, the 76 little-endian music pointers, and `0x06fba808` for 4 bytes.
The index-43/44 pointer words are specifically `0x01cf172c` and `0x01cf1730`. For each nonnull pointer,
read its NUL-terminated filename with a 512-byte bound and retain it only in local evidence. This settles
the inferred index-43 name and unresolved index 44. The virtualised gap `0x01854279..0x018542c2` remains
out of reach. The other domains' SND_Play sites, event packet state and model-lifecycle wiring remain
with their domain migrations; the later LIVE-PLAY FMOD comparison remains open.
