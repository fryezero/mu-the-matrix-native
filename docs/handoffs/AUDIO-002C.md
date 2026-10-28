# AUDIO-002 part 3

Implemented on branch `codex/audio-002c` from `9a827a4`, integrating `origin/main`
`40f34a9` under the merge lock in `c896551`. The only conflicts were the status/handoff
introductions; both lanes' entries are retained. No live client, launcher or service used.

Owned scope: audio adapters/log provenance, minimal combat/player/world sound callers,
synthetic tests, audio validator/manifest and the milestone documentation.
[Original sites and evidence boundaries](../research/client-audio.md#audio-002-part-3-2026-10-28).

## Result

Thirty-six distinct original SND_Play sites have session-ring adapters: player/monster
hurt and death, weapon swings/bow/crossbow, six receive-skill sites, eleven area/end-skill
sites and one effect-create site. Shared player/monster sites count once. The new log rows
use the existing `audio:1` handler/site/key/session-tick/cue-sequence fields.

Hero combat emits even with audio disabled and drains through the independent character
session reader. Remote players read combat results with a separate cursor for swings/hits;
their existing death selector now emits its previously discarded sounds. Monster attacks
now use their model sound slots. The existing effect callback now forwards the tornado's
`0x582` sound. Energy Ball's missing end sound `0x76` is restored. Model `0x7e2` also has
its supplemental hurt sound `0x86`, after the primary voice. New attack-voice streams
are independent of visual RNG. No reconstructed audio/combat/effect source or golden pin changes.

## Verification

- `validate_audio_combat.py --cases 6000 --mutations`: **19,548 cases, zero mismatches,
  16/16 compiled mistakes caught**. Player services 6,000; monster services 6,000;
  skill sound fragments 684; monster attack tail 864; effect creation 6,000.
  Original call return addresses independently supply the sound-site oracle. The
  supplemental monster fragment skips five intervening particle iterations, preserving
  its model/primary-voice/marker gates and sound order. Particle output/RNG is excluded.
  Whole skill dispatch/receive timing is not claimed by the fragment families.
- The integrated comparison JSON exactly equals the pre-merge comparison JSON.
- Existing audio: **13,967/13,967 equal**, **232/232** perturbations detected. Frame 2,407,
  OpenWorld 277, manager 2,023, init 107 and settings 9,153. All original routine hash pins retained.
- Seven existing manifest rows pass, zero failures/errors/skips: audio event managers,
  registration, voices, part-2 callers, hero audio, combat and skill effects. Audio part 1:
  76,150 cases, zero mismatches, 22/22 compiled mistakes; part 2: 5,528 checks,
  zero mismatches, 18/18 compiled mistakes. Hero audio: 2,000 cases, zero mismatches/stops.
  The runner's combat/effect smoke corpora also pass; their smaller counts are not presented
  as the historical expanded combat validation.
- **19/19 focused private tests pass**, including real world routing, remote hit/attack
  cursor isolation, transformed-input refusal, hero/remote death, casts, monster hurt/death,
  duplicate suppression and silent draining. The new and part-2 manifest rows both pass
  on the final integrated tree, zero failures/errors/skips.
- Both integrated Mac gates pass. The final gate reports: **1,516 tests, 187 expected skips**, zero failures;
  viewer/read-only reader builds and repository audit pass, 1,433 files, zero rejected.
  All **8 fixture scenarios** pass, **61 expectations, 67 inbound frames**, zero unbound
  and zero undecodable frames. Six unsent frames retain their documented boundaries.
  The complete gate was repeated after the validator dependency repair below. Its log
  is `gate-final.log`; behavior was checked at `c896551` plus that repair. Only release
  summaries were edited after the checks.
- The existing PCM golden remains
  `207036b711a07277a68466d736760c9440bab5d325ede5f90ddc298f18232897` and its regression test passes.
  Fourteen combat PNG hashes are identical with audio enabled/disabled. The existing
  42-frame part-2 audio/hash checks also pass. No frame/hash expectation was changed.

The private part-2 rerun after main integration initially failed to link the new
Duel Arena/world-82 object methods. `validate_audio_callers.py` now includes those two
production source dependencies. No comparison logic or expected result changed; its
entire pre/post-merge JSON report is identical. No hosted workflow ran.

## Limits and next work

This converts the bounded native combat/skill callers, not all 1,980 original sound sites.
SESSION-COMBAT timing and ordinary-player inputs remain in use. Authoritative event/buff
state, remote magic-result presentation and special monster bodies are still absent.
Hero skill audio uses ordinary caster class and special state 0. Remote weapon kinds use
the existing item-table adapter and synthetic fallback. Transformed remote hit/attack
contexts emit an explicit missing-input cue for `0x0139f3db`. Original RNG phase,
transformed death effects and the earlier body-service limits remain unresolved.

Other domains' callers, the part-2 NPC buff input, event packet state, music 43/44,
the virtualised `0x01854279..0x018542c2` gap and LIVE-PLAY original FMOD/native log parity
remain open. Encrypted casts remain unsent; no network or dispatch reconstruction was added.

Checkpoints `7bf67eb` and `39b429a` were pushed. Standards/spec review was performed locally;
no independent reviewer is claimed. Reports were lane-scoped under
`~/Documents/MTM/mu-mac-tools/native/scratch/audio-002c/`. After merge the scratch, generated
renders, build outputs, worktree and local branch are deleted. No new private input is retained.
