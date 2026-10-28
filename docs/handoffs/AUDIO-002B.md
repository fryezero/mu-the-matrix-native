# AUDIO-002 part 2

Owned branch `codex/audio-002b`, worktree `~/Documents/MTM/worktrees/audio-002b`, base `a278d93`.
No original client, launcher or live service is used.

Claimed scope: native audio cue routing and log provenance; minimal character/actor/NPC call-site adapters;
audio validators/tests; this handoff, the audio finding and AUDIO-002 status rows. Combat files, music
43/44 and the virtualised frame gap are excluded.

The recovered implementation is checkpointed in `ef125e3` and `ad10513`, with main `0a85441` merged in
`11ce249`. Thirty original call sites have session cue adapters: ten walking, three NPC voice, two
ReceiveTalk/window, five creature ambience and ten world-object sites. Twenty-nine can emit sound with
the migrated inputs. The third NPC voice requires buff `0x1b`, absent from the viewport records, and emits
an explicit `MU_CUE_AUDIO_INPUT` instead. The selector is verified for both known buff values. See the
[caller table and evidence boundaries](../research/client-audio.md#audio-002-part-2-2026-10-28).

The independent character-session audio cursor drains the ring without consuming window/effect readers'
cues. The log now records original routine and call-site addresses, session tick and cue sequence. Actor
model registration follows cache order and survives viewport rebuilds. An audio-only MSVC random stream
preserves the visual RNG; its phase is a native choice. Standalone worlds without a character session keep
their direct audio facade.

## Verification

- New `validate_audio_callers`: 5,516 original-instruction cases, zero mismatches, 18/18 compiled mutants
  caught. Families: voice 2,182, ReceiveTalk 2,304, walking 610, objects 420. Twelve ambient mapping checks
  verify literal ids/sites statically, giving 5,528 checks total. The unchanged environment family supplies
  the creature decision-gate proof. Finite object distance neighbors are covered; the original NaN-distance
  CRT error path needs uncaptured state and is excluded explicitly.
- Fourteen cue tests with private instruction comparison enabled pass. Three additional synthetic-world
  tests pass, covering actual world-part routing, talk and voice provenance, 239 ordered Aida object requests
  over 240 ticks, and 42/42 audio-enabled/disabled frame hashes equal.
- Expanded existing audio comparison: 13,967/13,967 equal, 232/232 perturbations detected. The entire JSON
  report, including all five captured routine hashes, equals the recovered baseline report. Counts are
  frame 2,407, OpenWorld 277, manager 2,023, init 107 and settings 9,153.
- Full `bash scripts/local-macos-ci.sh` passes: 1,449 tests, 175 explicit skips, zero failures/errors; six
  fixture scenarios pass with 46 inbound frames, zero unbound and zero undecodable frames. The fixtures'
  two unrecovered intents and three unsent frames remain expected limitations. Viewer/readers builds and
  repository audit pass, 1,314 files audited, zero rejected. The first gate attempt hit transient ENOSPC in
  the macOS temp directory; the complete rerun uses a lane-scoped `TMPDIR` and passes without source changes.
- Manifest runner: seven families pass, zero failures/errors/skips. Unchanged part-1 event music
  70,980 + registration 2,988 + voices 2,182 = 76,150 instruction cases, zero mismatches, 22/22 compiled
  mutants. All three JSON reports equal the recovered checkpoint reports. Hero audio: 2,000 cases,
  zero mismatches, all fourteen negative controls detected, all eleven captured routine hashes unchanged.
  Environment: 400/400 cases, 80,520 steps, 94/94 branch probes, zero mismatches/stops, 12/12 mutants caught.
  The runner's smaller existing-audio corpus also passes 10,367 cases and 232 perturbations.

No existing validator body or expected render/PCM hash changed. The audio golden PCM remains
`207036b711a07277a68466d736760c9440bab5d325ede5f90ddc298f18232897`.

## Remaining work

Combat callers belong to SESSION-COMBAT-001. The migrated quest windows contain no reconstructed
SND_Play sites and retain part 1's adapter. Legacy progress/master-tree UI, CButton/credits/character-select
UI, ground-item and pet/raven callers await their owning session migrations. Music 43/44, the virtualised
`0x01854279..0x018542c2` gap, event packet inputs, original RNG phase and LIVE-PLAY FMOD parity remain open.
No whole-client sound parity is claimed.

All raw reports, local inputs and logs remain in
`~/Documents/MTM/mu-mac-tools/native/scratch/audio-002b/`; renders stay in the corresponding
`native/renders/audio-002b/` directory. No private inputs or local symlinks are published.
Gate log: `gate-scoped.log`; expanded audio report: `audio-expanded-current.json`; cue test log:
`cues-current-private.log`; manifest-driven original-instruction reports: `validated-current/`.
