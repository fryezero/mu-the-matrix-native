# VIEWPORT-MONSTER-001 handoff

Owned branch `codex/viewport-monster-001`, worktree `~/Documents/MTM/worktrees/viewport-monster-001`.
Started at merged SESSION-VIEWPORT-001 PR #183, `54ae63f`.

The same CharactersClient now accepts C2 `0x13`, backed by the one static seed row at `0x0122c426`.
The `monsters` fixture owns placement/wander policy and emits real plaintext frames. Actors and NPCs
render session records and share the single tick-21 leased character loop. The old renderer placement
parser and wander decisions are gone. Cache identity changes rebuild models/effects and GL textures.

Evidence: **1,000 handler + 963 bounded creation cases, zero mismatches; 8/8 compiled mistakes caught**,
plus 3,000 authored parser-boundary checks. The exact original-code/host boundary, unavailable classes,
32-actor cache limit, and temporary unmigrated combat motion bridge are in
[the finding](../research/client-viewport-monsters.md).

NATIVE-WORLD-002 synthetic world: all **120 frame hashes unchanged** from `54ae63f`, with all 120
repeating exactly. Spider movement, Smith model/light and Maple effect stay unchanged.
The monster fixture scenario contributes **4 inbound frames, zero unbound/undecodable**.

## Final acceptance

Integrated main #184/#185 and #188 through `07e5816`. The fixed runtime tree `633d55e` passes
`bash scripts/local-macos-ci.sh`: **1,401 tests in 38 suites, 167 explicit skips, zero failures**,
including 617 native tests. Viewer and read-only reader builds pass. Repository audit:
**1,266 files, zero rejected**. The acceptance log is `gate-release.log`; earlier interrupted or
failed gates are not acceptance evidence.

All six discovered fixture suites pass with **46 inbound frames, zero unbound/undecodable**.
The existing two unrecovered intents and three unsent requests remain explicit. The monster scenario
contributes four frames. `gate-fixture-summary.json` retains the compact suite report.

Unchanged original-instruction regressions: players **4,768 cases / 7 controls**, helpers
**8,667 / 11**, actors **22,542 / 3**, all zero mismatches and all controls caught. Their reconstructed
sources are unchanged from #183. The helpers total includes the historical 8,639 plus 28 later entries.
The new family passes through `run_validators.py --private --only validate_viewport_monsters` with
**1,963 cases, zero mismatches, 8/8 mutants**. Reports are in `regressions/`, `helpers/` and
`new-family-final/`.

Five targeted monster tests cover mixed records, malformed atomicity, 400 slots/overflow/reuse,
loopback lifecycle and the private original-code check. The portable run passes four with one
explicit private skip. The lifecycle check destroys Maple and its effect, then recreates the same
key as Smith, using public fixture/session interfaces. The reserved tick-20 hook stays inert;
world-order tests now pin stepping inside the shared characters loop. The shared fixture defers its
player behavior once during actor-cache initialization, preserving the first rendered player tick.
The include audit passes without private world/test includes.

All 120 synthetic world hashes remain unchanged after #188 as well. Cache rebuilds intentionally
restart presentation animation/effects when viewport identities change. A refused asset clears the
cache, so obsolete actors/effects cannot remain visible. Self-review against AGENTS.md and the
milestone found no remaining defect within the documented scope. No independent review or live
service validation is claimed.

The final follow-up commit records evidence only. Gate fixture reports mark the worktree dirty due
to the two untracked input symlinks; tracked runtime source was committed for the acceptance run.
The committed-tree fixture suite is rerun after those symlinks are removed.
Artifacts are retained outside the disposable worktree under the scratch/renders directories named
in the finding. No original client or live service was used; no wire crypto or dispatch generator.
