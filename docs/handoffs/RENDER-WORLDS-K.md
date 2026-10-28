# RENDER-WORLDS-K

## Implemented scope

Built-in Lost Tower visual sprites and hero-driven push helper, Tarkan lamp/plume producers,
Icarus type-10 Bone01 flare producer, and the Atlans switch inventory correction.
[Finding and full fourteen-view scoreboard](../research/client-worlds-k.md).
No factory class is added. No live game, launcher, new capture or running-client read was used.

Base `3a61d99`, branch `codex/render-worlds-k`. Checkpoint `b741954` was pushed during reconstruction.
Owned files are the new built-in visual source, its narrow shared header/dispatch integration,
hero-action world-part adapter, native host and instruction tests, validator row and documentation.
Raklion/Karutan per-world files, item/mesh/scene/audio/effect/particle/joint implementations are untouched.

## Verified before final integration

- Five instruction families, 1,200 cases each: **6,000 equal, zero mismatches/stops**.
- **18/18 compiled production-C mutants** detected, with zero stopped mutant cases.
- Registered G/H/I/K: **24,000 equal**, zero mismatches/stops, **83/83 mutants**, four passes and no skips/errors.
- Synthetic native host exercises current-pose names and world positions, two origins, absent models,
  one-shot Tarkan plumes, the exact Icarus particle request and Lost Tower's real movement callback.
  Separate bounded-log test preserves state/RNG at capacities 0, 1 and 64.
- Fourteen-view before/after: only Lost Tower's first/final PNGs change. **26/26 unaffected PNG,
  14/14 OBJECT and 14/14 light hashes** match. All camera/object/light comparison scores are unchanged.
  Icarus's request counter changes 0 to 46 as expected. The three surviving original-image errors stay
  Dungeon **2.019 → 2.019**, Icarus **26.897 → 26.897**, Kanturu **4.006 → 4.006**.
  Other eleven original PNGs are absent, so their image error is unavailable.

The original Lost Tower type-23 transform input is unwritten. The comparison treats the transform as a
recording engine boundary and native uses the bone origin. Exact stack-dependent output is unverified.
Atlans checks the original switch landing and common RNG/model prefix; common event/factory hooks are
outside that family. Scalar trig/sqrt and pose services retain the documented validator boundaries.
No independent reviewer was delegated; this implementation agent reviewed source and test assertions.

The preflight `bash scripts/local-macos-ci.sh` passes **1,558 tests across 38 discovery runs**,
with **194 explicit skips**, zero failures/errors, all **9 fixture scenarios**, viewer/readers builds
and an audit of **1,503 files, zero rejected**. Readers were built but never run.
This is the pre-J gate; the final latest-main result below must supersede it.

## Integration still pending

J merge `26018b4f` and item H are integrated in `d7853c0`, pushed. Shared dispatch and top-document
conflicts retain both implementations. The post-J registered G/H/I/J/K run passes **30,000 instruction
cases, zero mismatches/stops, 113/113 compiled mutants**, five passes and no errors/skips.
The production world-host discovery passes 10 tests with one explicit private skip.

A fresh clean build of J-main `26018b4f` was made by detaching this owned worktree, rendering, returning
to K and clean-rebuilding. No other checkout was built or edited. Against that baseline, only Lost Tower's
two PNGs change; **26/26 unaffected PNG, 14/14 OBJECT and 14/14 light hashes** match. Against K's earlier
pre-J tour, exactly J's documented three Karutan artifacts differ: final PNG, OBJECT body-light copies
and frame-light dump. J's intended differences are preserved, not scored as a K regression.
PERF-004 acquired the merge lock before K's first attempt; K has not merged or started its final gate
while that lock is held.
Acquire the shared merge lock for the final latest-main/full-Mac-gate/PR/merge sequence.
EFFECTS-003 owns particle consumers `0x7ef7/0`, `0x7f5a/4/6/7/8` and sprite registrations
`0x7f84`, `0x7f38`, `0x8021`; missing consumers retain today's unsupported behavior.
Original loader sites and exact arguments were sent to that lane. If unmerged at the final gate,
these exact consumer/asset lists remain open rather than being claimed as drawing.

## Reproduction and cleanup

Use the repo Python for `scripts/validate_worlds_k.py --cases 1200 --mutations --output <local-json>`
or the `validate_worlds_k` row in `scripts/run_validators.py`. The production host is
`native/tests/test_native_worlds_k.py`; authored fixture data contains no client bytes.

Local logs/reports live under `~/Documents/MTM/mu-mac-tools/native/scratch/render-worlds-k/` and
renders under the sibling `renders/render-worlds-k/`. Bulk PNGs were deleted once hashed/scored;
only representative Lost Tower/Tarkan/Icarus endpoints were retained during development.
After merge remove both whole task folders, all worktree builds/temporary outputs, input links,
worktree and local branch. No new local input needs retention. Committed docs and the PR hold results.

Remaining exact-fidelity inputs: missing original PNGs, synchronized clock/RNG/effect pools, the type-23
transform input, earlier Aida reset history and Elbeland speeds. The other 37 uncaptured factory classes
remain outside K and require DATA-ACQ-002.

## Hidden Tarkan producers

A later lifecycle audit found that MoveObject hides Tarkan type 63 before rendering. The native host now
poses this lamp even when its mesh is hidden, so Bone02 comes from the current object rather than suppressing
the sprite request. Type 60 is also exempt from imported hidden sidecars until its first visual burst.
Authored native assertions cover both startup state and the hidden lamp's exact world position.
Removing either host clause in a separately compiled native mutant is detected: **2/2 host controls**,
followed by a restored production host pass. These are additional to the 18 instruction-compared mutants.
The first ad-hoc mutant attempt exposed same-second make caching; the final checks explicitly remove the
owned runtime object, archive and host executable before each compile, including restoration.
The final post-EFFECTS-003 tour and gate must cover these host fixes; the earlier tour counts above predate them.

An offline installed-model check also confirms all **9 named-bone requirements across 5 models**:
Lost Tower types 19/20/23, Tarkan type 63 and Icarus type 10. This checks the loaded asset names,
not original animation phase. No client process was touched, and the small inspector is deleted with scratch.

Static downstream limit: Tarkan type 83's `0x419/0x41a` requests use the existing Stone01/Stone02
lifecycle in `reconstructed/combat/skill_fx.c`. The combat renderer loads both models, but the separate
world-particle host's `fx_model_files` has no slots for them and `draw_models` skips missing slots.
The remaining work is that world-host model binding, not reconstruction of a missing stone lifecycle.
K emits and compares the original calls without adding effect/particle files.
