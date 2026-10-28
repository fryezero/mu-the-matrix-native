# AUDIO-002 part 1 handoff

Branch `codex/audio-002`, own worktree from main `5ebc2b6`. No original client, launcher or live service used.

## Implementation and evidence

- All 15 recovered frame-delegated event music managers execute through the native host. Explicit known bits
  prevent guessed Crywolf, Kanturu, temple or Raklion state. Travel clears those bits. 70,980 instruction
  comparisons, zero mismatches; 15/15 compiled mutants caught.
- Ordered monster/NPC SND_Load calls, including the early monster model switch. 601 monster types and 146
  NPC model types, preloaded/unloaded, worlds 0/39: 2,988 comparisons, zero mismatches, 4/4 compiled mutants.
  The independent original opener runs require all machine checks, including defined reads and return/SEH.
  A synthetic mesh-flag array supplies the NPC model `+0x34` read; no captured model bytes are needed.
- Three reachable NPC voice fragments: 2,182 comparisons, zero mismatches, 3/3 compiled mutants. Whole
  MoveCharacter effects, motion and the later NPC domain lifecycle are excluded from this claim.
- Total new instruction checks: **76,150**, zero mismatches, **22/22** compiled mutants. Manifest rows and
  owning private tests are added for all three validators. Source sites, inputs and limitations are in
  [the audio finding](../research/client-audio.md#audio-002-part-1-2026-10-27).
- Existing audio families rerun unchanged at `--random 2000`: 13,967 cases/scripts, zero mismatches,
  232/232 world-perturbation controls. Existing hero audio at `--cases 600`: 2,000 comparisons, zero
  mismatches, every negative-control variant detected. No old validator or hash assertion changed.
- The hero receive-handler adapter uses a shared typed sound adapter, also installed ahead of the quest
  window-log adapter. Current reconstructed quests have **no** SND_Play sites. Tests do not invent an
  original quest sound; synthetic log input checks the shared adapter. Independent session audio cursors
  are installed in headless and GFx quest/session consumers. Window/effect cursors keep their own reads.
- Eight native tests prove hero handler -> ring -> decoded PCM, one-time replay, provenance, independent
  readers, exactly 26 lost cues out of 1,050, duplicate suppression, silent drain, registration by site,
  event input invalidation and log-open refusal. Four portable tests cover the event/NPC boundaries. The shell logs scene music by pinned literal identity.
  Self-review covered the task scope and repository standards; no independent review is claimed.
- Native logs: `MU_AUDIO_CUE_LOG=/absolute/path/audio.jsonl`, JSONL schema `audio:1`. Open/close delimit
  each host; `host` distinguishes overlapping hosts and `seq` is host-local. Sound decisions carry cue sequence, handler, at_key and session tick.
  Frame time advances 40 ms per audio tick. Requests, unresolved inputs and ring loss are explicit.
  These are audio decisions, not a captured FMOD import log. The finding documents result codes.
- The TSV extractor adds optional source-site provenance. Explicit registration requires a newly extracted
  TSV. Its first-successful-load behavior is tested with reversed TSV order and different synthetic PCM.

## Gate and artifacts

The baseline local Mac gate passed 1,362 tests. The checkpoint gate first caught two manifest ownership
checks because the private test built validator names dynamically; the tests now name each script explicitly.
The first integrated gate exposed a pre-existing Makefile typo: character-select runtime objects depended
on undefined `CORE_HDR`, so they retained the old `mu_objects` layout after the world-lane merge.
Two existing tests reproduced zero retained objects. Changing that prerequisite to `HEADERS` rebuilt the
objects and both tests passed unchanged. `make -n -W core/mu_objects.h` confirms header changes now
schedule the rebuild. The parallel Icarus lane independently merged the same fix, so it is now also
in main. No character-select runtime behavior changed.
Final `bash scripts/local-macos-ci.sh` at source head `f55fbda`, after main `54ae63f` and the B/C world
lanes: **1,388 tests, 164 explicit skips, zero failures**. Viewer/read-only readers build; audit:
**1,238 files, zero rejected**. All discovered fixture scenarios pass. `gate-viewport-release.log` is the
final release record. Earlier passing gates are retained too. Existing GFx fixture initializer warnings
are unchanged from baseline; strict production builds pass. No hosted workflows ran.

The existing native audio render remains SHA-256
`207036b711a07277a68466d736760c9440bab5d325ede5f90ddc298f18232897`.
All existing render/hash expectations are unchanged. Four synthetic 40-frame world PNGs are byte-identical
with cue logging off/on; the enabled run records 3,447 audio decisions and 45 play requests. Renders are
retained under `~/Documents/MTM/mu-mac-tools/native/renders/audio-002/`. No new draw pass is introduced.
Reports and logs stay outside the worktree at
`~/Documents/MTM/mu-mac-tools/native/scratch/audio-002/`, including `unicorn/`, the existing-family reports,
`test-cues.log` and gate logs. Only authored code, synthetic tests and reviewed summaries are committed.

## Remaining work

1. Domain migrations call the event state API and the ordered model-registration/NPC voice APIs at their
   verified tick points. This lane does not change the actors/characters lifecycle. The legacy world
   `mu_progress` demo still has its documented separate facade; migrating its state is not AUDIO-002.
2. Convert the other domains' SND_Play sites when they migrate, using `audio_cue.h` and an independent
   `mu_session_audio_drain` cursor. The session owns effects; audio never writes replicated state.
3. In a separate live-capture task under the game lock: read `0x01cf1680` for `0x130` bytes and
   `0x06fba808` for 4 bytes. Index-43/44 words are `0x01cf172c`/`0x01cf1730`; read each nonnull pointed
   filename to NUL with a 512-byte bound, local evidence only. No such read was performed here.
4. `0x01854279..0x018542c2` remains out of reach. LIVE-PLAY's original FMOD log/native comparison is
   still open and must align frame time with session ticks. No live or whole-client audio parity claimed.
