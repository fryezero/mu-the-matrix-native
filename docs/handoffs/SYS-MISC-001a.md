# SYS-MISC-001a WIP handoff

Branch `codex/sys-misc-001a`, worktree `~/Documents/MTM/worktrees/sys-misc-001a`,
base `origin/main` at `7d813a9`. Scope claim: issue #208.

Status: **blocked, no PR or merge**. No windows are complete. No runtime/feed hooks,
session state, seed routes or GFx window registry changed. The first checkpoint is
`6cc4bc1`; the following WIP commit adds the validated arithmetic and these notes.

## Completed bounded work

- `reconstructed/misc/misc.{h,c}`: BossHPUI state initialization, palette mapping,
  maximum-to-segment unit, segment gauge and layered colour arithmetic.
- `scripts/validate_misc.py`, registered in `scripts/validators.toml`: 5 families,
  2,500 original-instruction comparisons, zero mismatches, 6/6 compiled mutants caught.
  Both native bar offsets are covered. The CRT ceil/conversion is modeled and the
  maximum-unit write is a bounded interior slice. See the module README for boundaries.
- `native/tests/test_misc.py`: four portable tests and one opt-in private check.
  The private-enabled focused run passes 5/5, including 200 instruction comparisons
  and six mutants. Registered runner: 1 pass, zero failures/errors/skips.
- Static window/controller and movie-contract findings in
  [client-misc-windows.md](../research/client-misc-windows.md).

## Why the complete milestone cannot be claimed

Existing seed/findings evidence does not bind the missing authoritative monster/boss
HP feed or the MonsterInfo/DamageCount native handlers/builders. F3 damage does not
supply remote current/max HP. There is no authorized evidence for inventing those
routes or synthesizing replicated HP from damage events.

MonsterInfo's movie API has no level field. DamageCount is a Stop/OK/Cancel text dialog.
CommandWindow/QuickCommand call into social/item actions and target/world guards.
DivideWindow is excluded because its item independence is not established. These
contracts must be resolved before a faithful session/domain migration can satisfy the
requested acceptance. Missing evidence is listed precisely in the finding; movie
metadata and static readings have not been presented as instruction comparisons.

Resume with scoped offline native handler/caller evidence plus route provenance for
those feeds, and a decision on the intended DamageCount behavior. Then implement the
misc domain/ops/intents, fixture behavior/scenario, window views and representative
renders, with the owning social/item seams. The validated math is ready to consume.
Macro/AutomaticMacro, SeasonPass, Artifact/Pet/Muun and DeathPenaltyExpRecovery remain
outside this slice. No live client, crypto/decode stage or keyed transform was used.

## Local state and checks

The main checkout was neither edited nor built. No merge lock was acquired because
there is no releasable implementation or final merge sequence. No hosted workflow.
The worktree and branch are kept to resume. Generated builds, private movie exports,
disassembly scratch and transient reports are removed after the final WIP checkpoint;
only the existing evidence/Python input symlinks remain. No new private input is needed.

Final WIP regression gate on runtime commit `a6171e4` passed:
`bash scripts/local-macos-ci.sh`, **1,521 tests in 38 suites, 188 explicit skips,
zero failures**. Native viewer and read-only reader builds passed. Publication audit:
**1,440 staged files, zero rejected**. All **8/8 existing fixture scenarios pass,
67 inbound frames, zero unbound/undecodable**, with the existing 2 unrecovered intents
and 6 unsent frames. These regressions do not add misc fixture acceptance. The suite's
dirty flag includes local input symlinks and the subsequent evidence-only doc update.
No golden/render hashes or reconstructed production sources were changed.

A local self-review checked the C arithmetic, instruction boundaries, compiled-mutant
comparisons, staged paths and scope claims. No independent review is claimed.
