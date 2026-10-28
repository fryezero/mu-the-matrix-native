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

Pending implementation validation and final locked gate. Exact counts will replace this paragraph.

## Limits and cleanup

NPC audio uses the latest complete viewport buff snapshot. Dynamic buff add/remove/expiry handlers are
not session routes, so their lifecycle is not claimed. Event packet state, remote magic results,
unmigrated domains, original RNG phase, music 43/44, the virtualised `0x01854279..0x018542c2` gap and
LIVE-PLAY FMOD/native log parity remain open. Ground-item sounds are left to SESSION-ITEMS-001a.

Temporary logs/reports are lane-scoped at `~/Documents/MTM/mu-mac-tools/native/scratch/audio-002d/`.
After merge, remove that directory, any lane render directory, build outputs, worktree and local branch.
No new private input is retained.
