# SESSION-VIEWPORT-001 handoff

Branch `codex/session-viewport-001`, owned worktree `~/Documents/MTM/worktrees/session-viewport-001`.
Base `c93ed3c`; integrated main through #178/#179 at `5ebc2b6` and #180 at `952868f`. No original client or live service used.

## Result

- CharactersClient owns 400 records. C2 `0x12`, C1 `0x3d/0x14/0x17/0x3f sub 2` reach it through the fixture,
  receive/dechunk, decode and generated dispatcher. The discovered scenario has 5 inbound frames and
  zero unbound/undecodable frames, with creation, move, store-open, death and destroy state checks.
- `--players` server encoding and scheduling moved to `fixture/behaviors/characters.c` and the inert
  specification helpers in `fixture/characters_spec.c`. Core player code now renders/animates session
  copies and supplies movement services. Helpers consume the same equipment/record feed.
- One characters table walk owns player stepping at tick 21, after the existing actor lane and before
  NPC/quest/combat. Helpers retain tick 90. Render-selected rider poses also commit through a lease.
  Part state is cleared at close, including travel away from and back to a world without players.
- CHARACTER projection adapters use the generated manifest. Unknown/scene/string bytes remain untouched.
  The portable round trip tests every mapped member; lease checks include replicated and unused slots.
- Shared integration changes are limited to generated route seeds, lease exposure/capacity, fixture
  registration access, build dependencies and tests. Main's quest RNG rename, fixture accessor,
  loopback-only archive and generated test stubs were retained during the merge.

## Evidence

- New viewport family: 7,000 instruction cases, zero mismatches; 8/8 compiled mutants caught.
  Additional parser-boundary checks: 3,000. Full-handler field comparisons use explicit engine/table
  hosts; the complete create routine and excluded engine/table branches are not claimed verified.
- Unchanged players family: 4,768 cases, zero mismatches, 7/7 controls.
- Unchanged helpers family: 8,667 cases, zero mismatches, 11/11 controls. This includes the historical
  8,639 set plus 28 later class/state entries already documented in `validators.toml`.
- Portable characters checks cover real-frame state, helper slot, projection, malformed atomicity,
  lease misuse, full table capacity/overflow, and slot reuse/generation. Existing player, helper,
  social/travel and app no-network checks are retained.
- Synthetic render comparison: 120 frames against `5ebc2b6`, 35 intended changes after the death event;
  all 120 new-run hashes repeat exactly. The server scheduler no longer shares the client's visual RNG.
  Exact hashes and the source/evidence boundary are in the [finding](../research/client-session-viewport.md).

## Final local gate

`bash scripts/local-macos-ci.sh` after #180: **1,371 tests, 161 explicit skips, zero failures**.
The 38 suites include 600 native tests. Viewer and read-only reader builds pass; repository audit:
**1,218 files, zero rejected**. Five discovered scenarios pass with **42 inbound frames, zero
unbound/undecodable**, two unrecovered intents and three unsent requests retained from the existing
hero/quest bounds. The characters scenario contributes 5 frames, all five of its routes.

The new family also passes through `run_validators.py --private --only validate_viewport`: 7,000
instruction cases, 8/8 mutants. The final binaries repeat all 120 documented new render hashes.
Self-review against AGENTS.md and the milestone found no remaining defect in this bounded migration;
no independent review or live gameplay validation is claimed.

The gate log is `gate-final.log`; suite proof is retained in `release-suite/`. The suite records
`8a1e788` with dirty source because the final store-localization and charsel header-dependency fixes
were awaiting commit, along with the two untracked input symlinks. Those exact source fixes were
compiled and tested by this clean gate. A committed-tree fixture rerun is retained separately.

An earlier gate was interrupted by another lane and is not acceptance evidence. The incremental
#180 run exposed stale charsel objects; replacing its missing core-header dependency and cleaning the
build restored the object/effect tests. Fresh charsel: 11 tests, 2 private-data skips, pass.
The original localized store label lookup was preserved during final review.

## Local artifacts

Retained outside the disposable worktree:
`~/Documents/MTM/mu-mac-tools/native/scratch/session-viewport-001/` holds gate logs, `viewport.json`,
`players.json`, `helpers.json`, the synthetic hash driver/source backup, comparison logs and hashes.
`~/Documents/MTM/mu-mac-tools/native/renders/session-viewport-001/` holds baseline, after and repeat PNGs.
Only authored source, synthetic scenarios and reviewed summaries are committed. Input symlinks are not.

## Next and limits

VIEWPORT-MONSTER-001 can populate the same 400-entry table. The legacy world demo caches eight player
models; generic 400-character rendering and the monster/NPC actor migration remain that lane's work.
Account-owned session lifetime, wire crypto, recovered dispatch and replay remain separate milestones.
Static/inferred pet/muun/pose/effect branches and store-close/equipment-change routes are not upgraded by
this migration. See the finding for the precise original-instruction comparison domain.

## Integrated PR gate through #181

After Icarus main merge `5f6b0cf`, clean `bash scripts/local-macos-ci.sh` at `6e82547` passes
**1,373 tests, 162 explicit skips, zero failures**, viewer/readers and audit
**1,228 files, zero rejected**. All five discovered scenarios again carry 42 inbound frames with
zero unbound/undecodable; the two unrecovered intents and three unsent requests stay explicit.
This supersedes the earlier #180 gate for PR acceptance. `gate-main181.log` and
`release-suite-main181/` retain the proof. Its tracked source was committed; only input symlinks
made the suite's dirty flag true. No additional runtime changes were needed after this merge.
