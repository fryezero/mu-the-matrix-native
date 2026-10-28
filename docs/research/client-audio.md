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

With native audio enabled, set `MU_AUDIO_CUE_LOG=/absolute/path/audio.jsonl` before starting the native
client or audio tools.
Each host appends `open`/`close` boundaries and ordered JSONL records with `audio:1`, host-local `seq`,
`host` distinguishing overlapping engines, `time_ms` from its 40 ms audio frame clock, world, op, id, loop, result, cue sequence, handler, at_key and
session tick and registration source site. Scene music requests carry the pinned string-literal address
in `id` under `music_literal`/`stopmusic_literal`, so the shell can log track identity without filenames. For sound play, result 1 starts, 0 suppresses/fails, -1 is unresolved. Music/stop records
are requests, result 2 when resolved, not claims of an FMOD call or successful decoding. Registration
records put the source site in `site`; unrecovered records identify the missing input/routine in `id`.
Cue-loss records report the exact dropped count, including nonsound cues. Log-open failure fails audio
initialization. No paths, account data or runtime pointers appear in records. A future comparator must
expand requests through the verified SND/FMOD manager and align the independent frame/session clocks;
this log alone is not an original-versus-native FMOD comparison. No original FMOD log was captured here.

Eight native tests check handler-to-ring-to-PCM, shared adapter provenance, two independent readers,
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

Final local Mac gate after the viewport, B/C worlds and item rendering merges: 1,393 tests, 165 explicit skips, zero
failures; viewer/readers build and repository audit pass, 1,247 files, zero rejected. The final gate is
`native/scratch/audio-002/gate-items-release.log` under `mu-mac-tools`; the handoff gives the full path.

## AUDIO-002 part 2, 2026-10-28

The existing `codex/audio-002b` checkpoint was reviewed and completed after merging main `89c63ac`.
Only this worktree was built or edited. No original client, launcher or live service was used.

**Implemented.** Thirty source call sites have adapters into the character session ring. Twenty-nine can
emit `MU_CUE_SOUND`; the third NPC voice reports its missing buff input as described below.
An independent audio cursor consumes them without taking the window/effect readers' cues. Sound logs
retain the original call instruction in `site`, the owning routine in `handler`, cue sequence and
session tick. `at_key = -2` denotes the original null object, and `-3` denotes the ambient creature.
The verified SND_Play implementation ignores that pointer. The renderer and visual RNG are unchanged.

| Caller | Original routine and SND_Play sites | Sound ids / conditions |
|---|---|---|
| Walking, 10 sites | `0x013b1f61`: `0x013b200a`, `202f`, `2054`, `208c`, `20ab`, `20c7`, `20e6`, `2136`, `2146`, `2156`, all with prefix `0x013b` | Snow 10, grass 9, swim 11, bridge 1233, soil 8; existing action/manager/world/safe-zone/tile/terrain gates unchanged |
| NPC voices, 3 sites | `0x013b23f8`: `0x013b5402`, `0x013b542f`, `0x013b5494` | Models `0xa0b`/`0xa06` select 161/160 on signed random remainder 64/256 = 0; `0xa01` selects 160 for action 0, frame 5..10, buff `0x1b` absent |
| ReceiveTalk windows, 2 sites | `0x01280659`: `0x012811ca`, `0x012811d8` | 25 then 28, only after the reconstructed encrypted-input gate and valid result path |
| Ambient creatures, 5 sites | `0x00c9eb04`: `0x00c9fcd5`, `0x00c9fcfb`, `0x00c9fd2f`, `0x00c9fd74`; `0x00ca05b3`: `0x00ca1c80` | 12, 13, 14, 138, 15; existing random, distance and action gates unchanged |
| Aida objects | `0x00d6202f`: `0x00d622d1` | 584, worlds 33/54 |
| Kanturu objects, 5 sites | `0x00e74ae0`: `0x00e74c6e`, `0x00e74f29`, `0x00e74f57`, `0x00e75033`, `0x00e7507d` | 618, 616, 617, 619, 620, with the existing type cases and common-tail ordering, worlds 37/40 |
| Karutan object | `0x00e13a9e`: `0x00e13bd2` | 1445, type `0x87`, worlds 80/81 |
| Tormenta objects, 3 sites | `0x00e4c95e`: `0x00e4ca6a`, `0x00e4cb19`, `0x00e4cbc8` | 1409/1412/1411 for types 6/183/200 at distance <= 1300*scale / 450 / 800 |

**Verified.** `validate_audio_callers.py` compiles the production selectors and cue adapters. It compares
ordered routine/site/id/null-object/loop decisions against the original instructions, including no-call
cases. Corpus: NPC voice fragments 2,182, full ReceiveTalk 2,304, PlayWalkSound 610, object handlers
420. That is **5,516 instruction cases, zero mismatches**. Twelve additional ambient id/site mapping
checks statically verify the literal push and SND_Play target, including seven unsupported ids.
The unchanged `validate_environment` family verifies the ambient decision gates. The validator's total
is **5,528 checks**, with **18/18 compiled mutants caught**, including wrong voice route/frame/buff,
talk gate/id/site order, terrain/world/site selection, ambient loop, object site/id/type/distance/order.
Object comparisons execute the four original handlers with finite synthetic geometry, scale 0.5/1/2,
distance boundary neighbors, seven world ids, type controls and ordered multiple sounds. The NaN-distance
probe stopped in the original CRT's uncaptured error path at `0x019bd00e`; it is excluded rather than
replaced with an inferred result. Full object motion and surrounding model services remain covered by
the existing object families, not by the new sound-only comparison.

**Native integration.** Model-open sound registration follows the migrated actor cache order and retains
one cache per audio host across viewport rebuilds. Source-site registration still uses the part-1
first-successful-load rule. An audio-only MSVC random stream supplies the two probabilistic NPC voices;
its phase is a native choice, not an observed original RNG state. The third voice's buff state is absent
from the migrated viewport records. It emits `MU_CUE_AUDIO_INPUT`, logged as `unrecovered` with input
`0x01295ade`, instead of assuming the buff is absent. Supplying a known buff value is verified by the
adapter tests, but no new replicated buff fields are invented here.

Fourteen focused cue tests pass with private comparison enabled. They cover real hero handler -> ring
-> PCM, independent readers, one-time drain, exact 26/1,050 cue loss, silent drain, registration order,
model cache reuse, provenance, explicit missing input, event invalidation, and object runtime distance
gating. Three synthetic-world tests cover installed world parts: NPC talk/voice/walking provenance,
239 Aida object requests after initial visibility setup over 240 ticks, and **42/42 frame hashes equal**
with audio enabled/disabled in Lorencia and Aida. The initial visibility warmup is preserved.
The native audio golden PCM remains
`207036b711a07277a68466d736760c9440bab5d325ede5f90ddc298f18232897`.
No existing validator body, expected render hash or PCM hash was changed.

**Scope inventory.** The migrated quest windows have no reconstructed SND_Play sites; part 1's shared
adapter remains installed. ReceiveTalk's two window sounds are covered above. The legacy CButton,
credits and character-select UI, legacy progress/master-tree windows, ground-item pickup sounds and
pet/raven callers have no migrated owning session here. Their future domain migrations must use the
same ring contract; they are not included in the 30-site count. Standalone worlds without a character
session retain the direct facade. Per-frame music/ambient managers remain in their part-1 host path.
Combat stays with SESSION-COMBAT-001. Music 43/44, `0x01854279..0x018542c2`, event packet inputs,
original RNG phase and LIVE-PLAY FMOD parity remain open. No whole-client audio parity is claimed.

Final local Mac gate: 1,453 tests, 176 explicit skips, zero failures/errors; six fixture scenarios pass,
viewer/readers builds and repository audit pass, 1,328 files, zero rejected. Seven manifest-driven
instruction validators pass with no skips. Unchanged reruns: expanded audio 13,967 cases and 232/232
perturbations, part 1 76,150 cases and 22/22 compiled mutants, hero audio 2,000 cases and all fourteen
negative controls, environment 400 cases, 94/94 probes and 12/12 mutants. All comparisons have zero
mismatches. Expanded audio and all three part-1 JSON reports equal the recovered baseline reports;
all existing captured routine hashes and expected render/PCM hashes remain unchanged. Exact commands,
fixture limits and log paths are recorded in [the part-2 handoff](../handoffs/AUDIO-002B.md).
All raw reports, local inputs and logs remain outside the published tree.

## AUDIO-002 part 3, 2026-10-28

`native/core/mu_combat_audio.h` adapts 36 distinct original SND_Play sites into
`MU_CUE_SOUND`. `mu_combat` emits into its character session even when audio is
disabled. The existing independent character audio cursor drains after combat's
pre-tick and tick, so effects/windows keep their readers and enabling audio does
not replay history. A standalone combat host without a session retains its callback.
No reconstructed audio, combat or skill-effect routine is changed.

| Original service | Sites and sound selection | Evidence |
|---|---|---|
| SetPlayerShock `0x0138f92f` | Skeleton `0x0138fbda`, model slots `0x0138fc68`, player class/transform/RNG `0x0138fcc5`, `0x0138fcf5`, `0x0138fd2b`; model `0x7e2` supplemental `0x86` at `0x0138fe5e` | Original service comparison; supplemental fragment skips the five intervening particle iterations, retaining the model/voice gate and sound order. Missing model/slot returns before the supplemental sound. |
| SetPlayerDie `0x01393a61` | World voice `0x01394351`, model slot `0x013943e5`, player class `0x0139441e`, `0x0139442f`, `0x01394440`, transformed extra `0x01394464` | Original service comparison, once-only voice marker retained. Remote players previously discarded the selected sounds. |
| SetPlayerAttack `0x01392bde` | Model slot `0x01393917`; bow/crossbow/staff/sword `0x01393939`, `0x0139395b`, `0x013939a3`, `0x013939eb`, `0x01393a3f` | Player service comparison and bounded monster tail. World `0x49`, voice marker, missing model and missing slot gates compared. |
| Magic receive `0x01253a92` | Buff/heal `0x01255962`; melee skills 19..23 use `0x01255f1c`, `0x01255f4b`, `0x01255f7a`, `0x01255fa9`, `0x01256011` | Bounded sound fragments, including the caster-class `0x4d` buff suppression. Dispatch, encrypted packet bodies and full receive timing are excluded. |
| MoveCharacter `0x013a763e` | Eleven end/area sites: `0x013a954d`, `0x013abb36`, `0x013abc4b`, `0x013ac92e`, `0x013ad00b`, `0x013afe5c`, `0x013b0099`, `0x013b0101`, `0x013b03eb`, `0x013b063e`, `0x013b0e08` | Bounded sound fragments. Twisting Slash's special-state-3 suppression compared. Energy Ball's missing `0x76` playback is restored. |
| CreateEffect `0x013c0f19` | Tornado `0x582` at `0x013c42ee`, within 800 units of the hero | Existing complete effect-create instruction family, including distance/random-position gates, plus compiled sound provenance adapter. Previously the native combat effect callback discarded this event. |

The target text SHA-256 is
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`,
base `0x00401000`. Image data SHA-256 is
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`,
base `0x01a7c000`. Only authored adapters, synthetic tests and this summary are published.

The native JSONL cue log retains schema `audio:1`. New combat rows contain the
original routine in `handler`, the exact SND_Play instruction in `site`, the
session sequence/tick and `at_key`: hero `-1`, actual remote player/monster key,
or effect object `-3`. Audio object pointers do not enter the log. The remote
player's independent combat-result reader emits hit and swing cues once; death
uses the existing animation/voice marker. New remote/monster attack audio uses
separate MSVC streams, preserving visual RNG. The original random phase is unavailable.

`validate_audio_combat.py` compares 19,548 cases: player services 6,000,
monster services 6,000, skill fragments 684, monster attack tail 864 and effect
creation 6,000. Original service gates and sound ids are checked by the unchanged
service families; the new compiled adapter is compared with original sound-call
return addresses. Planted adapter mistakes cover ids, sites, buff/special-world
conditions, model slots and supplemental voice gates. The local handoff records
final mutation and gate results.

The native timing/context remains bounded by SESSION-COMBAT-001. Hero skill
fragments use the existing ordinary-player context and special state 0; authoritative
event/buff state and remote magic-result presentation are still absent. Remote
weapon kinds use the existing item-table adapter, with its documented synthetic
fallback when the table is absent. Remote transformed hit/attack contexts emit
`MU_CUE_AUDIO_INPUT` for `0x0139f3db` instead of guessing their model predicate.
Special monster bodies and transformed death effects retain their earlier limits.
This is not full-client sound parity. Music 43/44, the virtualised gap and
LIVE-PLAY's original FMOD/native log comparison remain open. No live client was used.


## AUDIO-002 part 4, 2026-10-28

**Verified, bounded.** The existing monster/NPC viewport snapshot retains all buff keys. The world audio
hook now reads that session-owned snapshot for model `0xa01`, rather than passing unknown. The original
key lookup `0x01295ade`, the voice fragment `0x013b543c..0x013b549c` and AddBuff's world restriction
`0x0128723b` run in the new comparison. Buff key `0x1b` suppresses sound 160 at `0x013b5494`;
action 0 and frames 5 through 10 are required when it is absent. The table-existence answer is checked with the original getter on the pinned skill snapshot. Unrelated
visual effects and insertion are hosts; the MSVC map is synthetic and its lookup executes as original
instructions. This uses the latest complete viewport snapshot. Dynamic add/remove/expiry handlers
are not migrated and are not inferred from a packet list. Unknown snapshots still emit missing input.
No per-tick allocation or replicated-state write is added.

**Verified.** SESSION-SKILL-001's Master environment now binds its previously discarded event callback.
`OnClickBtnSkillSlot 0x00bb22e1` plays sound 25 at `0x00bb23d1` after finding a slot and before checking
points/prerequisites. The callback emits a typed sound with explicit original routine/site and null-object
key `-2`. Invalid slots, unsupported events and learn requests do not acquire sound cues. The session
reader supplies cue sequence and tick to the unchanged native log.

`validate_audio_domains.py` executes 1,944 NPC cases, including real buff-map lookup, world restrictions,
empty/present/absent/duplicate keys, action and finite/nonfinite frame edges. It also runs 600 complete
Master click/confirmation cases through the unchanged original/reconstructed caller comparison, recording
SND_Play return addresses independently. Total: **2,544 cases, zero mismatches, 7/7 compiled mutants**.
The unchanged viewport family separately verifies the existing buff-record parser.

**Static scope audit.** The same validator follows intraprocedural branches in 24 migrated quest
receive/callback roots. None contains a direct SND_Play call. Reconstructed quests still have no sound
call to route; ReceiveTalk's two earlier sites remain in part 2. This does not assert silence of every
transitive helper or GFx movie. Existing quest instruction families are rerun unchanged.

The caller subtotal advances from **66 adapters / 65 sound-capable sites to 73 / 73**. This adds seven
distinct original sites and supplies the input for the existing NPC site; the earlier hero receive sound
and per-frame/event manager paths are outside this subtotal. SESSION-COMBAT-001 still has no remote
magic-result output, and SESSION-GLOBALS-001 adds ownership rather than new replicated inputs.
Event inputs, remote magic results, other domains, music 43/44, the virtualised gap, original RNG phase
and LIVE-PLAY's original FMOD/native comparison remain open. No live client or launcher was used.
Final checks and cleanup are recorded in [the part-4 handoff](../handoffs/AUDIO-002D.md).


### Ground-item extension after SESSION-ITEMS-001a

The orchestrator added ground-item scope after PR #224 merged at `3a61d99`. Six CreateItem sites are
**verified** against the complete unchanged caller family: zen `0x016daafd` selects 31, jewels
`0x016dadde` select 69, special item `0x016dae04` selects 723, two special ranges use distinct
`0x016dae36` / `0x016dae5f` sites for sound 90, and ordinary items use `0x016dae76` for sound 30.
Original routine: `0x016daa27`. `validate_audio_items` compares 3,000 cases with zero mismatches and
catches all 8 compiled mutants, including missing-record/drop gates and the two sound-90 branches.
It preserves the existing caller validator's explicitly documented compare repair at its runtime-patched
branch; the opaque destination remains outside the comparison. Together with NPC/Master this is
**5,544 new part-4 cases, zero mismatches, 15/15 compiled mutants**.

The session emits drop cues at viewport arrival. A borrowed static-record getter preserves CreateItem's
record-presence gate. Closing the view clears it; detached arrivals report missing input and are never
replayed on attachment. The presenter suppresses its old direct audio path for session items; standalone
tools retain that facade. Item-only sessions have their own cursor; shared character sessions retain one
reader. Tests cover all six sites, actual native voices, duplicate-id suppression, silent drain, missing
records, non-drop viewports, detachment/rebind and deletion.

The verified delete/despawn handler has no sound call. Requests remain silent. Successful pickup-answer
sites `0x01242b81`, `0x01242ba6`, `0x01242bbf` require the unrecorded answer route/decode and stay open.
The existing 4,000-case session-item comparison verifies those bounded instructions but does not supply
that route. No pickup success, inventory insertion or zen credit is inferred from a fixture delete.
