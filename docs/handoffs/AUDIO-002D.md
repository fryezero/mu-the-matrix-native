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

The part-2/3 caller inventory advances from 66 adapters / 65 sound-capable sites to 67 / 67.
One new distinct original site is added, and the existing NPC site `0x013b5494` becomes sound-capable.
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

Final integrated gate and quest/environment totals are pending the merge lock.

## Limits and cleanup

NPC audio uses the latest complete viewport buff snapshot. Dynamic buff add/remove/expiry handlers are
not session routes, so their lifecycle is not claimed. Event packet state, remote magic results,
unmigrated domains, original RNG phase, music 43/44, the virtualised `0x01854279..0x018542c2` gap and
LIVE-PLAY FMOD/native log parity remain open. Ground-item sounds are left to SESSION-ITEMS-001a.

Temporary logs/reports are lane-scoped at `~/Documents/MTM/mu-mac-tools/native/scratch/audio-002d/`.
After merge, remove that directory, any lane render directory, build outputs, worktree and local branch.
No new private input is retained.
