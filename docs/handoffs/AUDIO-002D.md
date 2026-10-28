# AUDIO-002 part 4

Lane `codex/audio-002d`, new worktree from `origin/main` at `cf81357`. Scope claimed in issue #222.
No original client, launcher, live service, new capture or hosted workflow used.

## Scope and input audit

- SESSION-QUEST-001 still exposes no reconstructed SND_Play calls. The new audio-domain validator
  statically walks 24 migrated quest receive/callback roots, following intraprocedural direct branches.
  This bounds the absence claim to those bodies; it does not prove silence in every transitive service.
  Existing quest instruction families are rerun separately. No invented quest sound is added.
- The migrated monster/NPC viewport already stores the complete latest buff list in
  `mu_characters_view.monsters`. Part 2's world hook always passed unknown instead. The audio hook now
  reads that snapshot, tests key 0x1b, and retains the original remote-buff world restriction. Unknown
  snapshots still report missing input. No replicated fields, packet routes or fixture policies are added.
- SESSION-SKILL-001 owns the Master environment but discarded its event callback. Its click's sound 25,
  original routine `0x00bb22e1`, site `0x00bb23d1`, now enters the session cue ring before affordability
  checks. Missing slots and learn requests remain silent. The bound callback follows the book across
  world detachment and rebinding.
- SESSION-COMBAT-001 provides damage, death and action outputs, not remote magic-result events.
  SESSION-GLOBALS-001 changes ownership, not that input contract. No remote magic sounds are guessed.

The part-2/3 caller inventory advances from 66 adapters / 65 sound-capable sites to 73 / 73.
Seven distinct original sites are added, and the existing NPC site `0x013b5494` becomes sound-capable.
The hero's earlier receive sound and per-frame/event manager paths are outside this caller subtotal.

## Checks

- Baseline local Mac gate: 1,550 tests, 192 explicit skips, zero failures; viewer/read-only readers
  build and publication audit pass. Readers were built, never run.
- New `validate_audio_domains`: 1,944 NPC plus 600 full Master click cases, **2,544 comparisons,
  zero mismatches, 7/7 compiled mutants caught**. Unknown inputs and unsupported events are checked too.
  Buff key 0x1b's table existence is verified by the original getter on the pinned skill snapshot.
  The NPC comparison runs AddBuff's world/eligibility gates and the real map lookup/voice fragment.
  Effects, map insertion and the already-verified static table answer are hosts; zero-filled stack tag
  slots follow the existing MSVC harness convention. This does not claim the whole buff subsystem.
- **26/26 focused private audio tests pass**, including viewport absence/presence, complete-snapshot
  replacement, destruction and key reuse, failed Master clicks, silent requests, independent readers,
  silent draining, log provenance and unchanged render hashes. The synthetic world Smith animation
  never reaches frame 5; the new frame-driven session test exercises the sound at frame 7.
- Expanded existing audio: **13,967/13,967 equal**, **232/232** world perturbations caught. The entire
  before/after JSON reports match, including five captured body hashes. The existing PCM golden stays
  `207036b711a07277a68466d736760c9440bab5d325ede5f90ddc298f18232897`.
  Existing 42 world plus 14 combat frame hashes agree with audio enabled/disabled. No hash expectation
  or old comparison body was changed.
- Part 1 unchanged: 76,150 cases, zero mismatches, 22/22 compiled mutants. Part 2 unchanged: 5,516
  instruction cases plus 12 static checks, zero mismatches, 18/18 mutants. Part 3 unchanged: 19,548
  cases, zero mismatches, 16/16 mutants. Hero audio: 2,000 cases, zero mismatches, all negative controls.
- The first private part-2 rerun could not link `mu_market_*` / `mu_uruk_*` after RENDER-WORLDS-I.
  Its compile list now includes those two production sources. The repaired runner passes all 5,528
  checks without changing comparisons or expectations. Manifest tests pass 17/17; include audit passes.

- Unchanged quests: 8,203 + 7,004 + 2,001 = **17,208 comparisons, zero mismatches, 13/13 mutants**.
  Environment: 400 cases, 80,520 steps, 94/94 branch probes, zero mismatches/stops, 12/12 mutants.
- The orchestrator expanded scope after SESSION-ITEMS-001a merged as PR #224, main `3a61d99`.
  It is integrated in `2bd66e8`. The only merge conflict was two appended validator rows; both remain.
  The earlier final gate was stopped when scope expanded and is not acceptance evidence.

## Ground-item extension

Six CreateItem `0x016daa27` sites now emit arrival-time session sounds: zen `0x016daafd` / 31,
 jewels `0x016dadde` / 69, special `0x016dae04` / 723, two special ranges `0x016dae36` and
 `0x016dae5f` / 90, and ordinary `0x016dae76` / 30. The two sound-90 sites retain distinct provenance.
Null-object zen uses key -2; other drops use the parsed ground slot. The drop flag and static-record
presence gate remain required. A borrowed read-only Item.bmd presence callback supplies that input;
closing its world clears the callback. Without that input the session records one explicit missing-input
cue per incoming drop and never replays it when a view attaches later. Rebinding an already-created item
also stays silent. The existing presenter keeps its stats and standalone sound facade.

The item-only world owns an independent audio cursor; shared character sessions use their existing
cursor, preventing duplicate playback. Disabled audio drains too. No per-frame allocation is added.
The delete/despawn handler has no SND_Play call, and pickup requests do not imply success.

`validate_audio_items` reuses the unchanged complete CreateItem original/reconstructed comparison,
then compares the compiled audio adapter against original SND_Play return addresses. **3,000 cases,
zero mismatches, 8/8 compiled mutants**. It retains the existing validator's documented compare repair
at the runtime-patched branch; the opaque target is not executed or reconstructed. The existing
session-item comparison also passes **4,000 cases, zero mismatches, 4/4 mutants**, including silent
delete/request paths and the still-unrouted pickup-answer tail. Total new part-4 instruction evidence:
**5,544 cases, zero mismatches, 15/15 compiled mutants**.

All **30/30 focused private audio tests** pass after the ground extension, including all six original
sites and five actual native voices, duplicate-id suppression, silent drain, known missing records,
non-drop flags, delete/request silence, and detached arrival without late replay. The item-only and
shared-character world paths both play once. Eight additional frame-hash pairs match, giving **64/64**
world/combat/item comparisons with audio enabled/disabled. Final integrated gate is pending.

## Limits and cleanup

NPC audio uses the latest complete viewport buff snapshot. Dynamic buff add/remove/expiry handlers are
not session routes, so their lifecycle is not claimed. Event packet state, remote magic results,
unmigrated domains, original RNG phase, music 43/44, the virtualised `0x01854279..0x018542c2` gap and
LIVE-PLAY FMOD/native log parity remain open. Pickup-success sounds at `0x01242b81`, `0x01242ba6` and `0x01242bbf` remain unrouted until the answer route/decode is recorded. No inventory or zen credit is invented.

Temporary logs/reports are lane-scoped at `~/Documents/MTM/mu-mac-tools/native/scratch/audio-002d/`.
After merge, remove that directory, any lane render directory, build outputs, worktree and local branch.
No new private input is retained.
