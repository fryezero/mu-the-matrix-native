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
- Event-world music managers, the virtualised frame gap, the 1,980 SND_Play call sites (which game events
  play which ids) and the monster/NPC registration order are not reconstructed.
- FMOD's own mixing, stealing and pan rules are unavailable; the engine's choices are listed above.
