# Fixture session verification, VERIFY-SESSION-001

## Verified scope

The portable full-stack suite runs the dev `mu-session` tool through its seeded session, the in-process
loopback transport, the existing plaintext dechunker and dispatcher, and the hero apply functions.
`scripts/run_fixture_scenarios.py` discovers every `native/fixture/scenarios/*.scn`. Each migrated
`native/session/ops/<domain>.ops` requires a `<domain>-*.scn`, enforced without a shared domain list.
Both `make test` and `scripts/local-macos-ci.sh` run every discovered scenario. The CI script retains a
separate report under `verify-runs/ci-fixtures-*/suite/` and now defaults to the documented project Python.

The existing hero-progress scenario exercises six hero routes. The added hero-master scenario exercises
the two master routes, using a synthetic third-class hero. Together they cover all eight bound hero apply
functions with 17 inbound C1 frames and 21 passing scenario expectations. Each scenario reports zero
unbound and undecodable frames. No runtime, fixture, dispatcher or reconstructed handler source changed.

## JSON and proof contract

Schema 1 reports include the current commit, dirty flag, binary digest, total and per-scenario journal
counts, route hits by connection/opcode/sub/handler/apply, and `unrecovered_by_intent`. Each scenario
retains its original and effective script digests, effective script, command, stdout, stderr, exit code,
binary journal and result. Output directories are exclusive so a rerun cannot reuse old proof.

The skill's `run-tool.sh RUN NAME --fixture [SCENARIO]` uses this runner. Its optional
`--script 'T:inbound:HEX ...'` validates complete C1/C2 frames and expands them into the fixture's existing
`at T send game HEX` commands in a local copy. The original scenario stays unchanged. Tick numbers are
one-based fixture steps. A script requires one scenario. The runner derives duration from every timed
line, including server-only commands, avoiding the tool's client-line-only default duration.

Inbound journal events pass through as JSON rows, tagged with the scenario. A final `summary: true` row
contains `journal` totals and per-scenario `results`; `summary.py --frames` and `--last` also understand
inbound rows. Existing scene and walk frame formats retain their behavior.

The runner independently fails on any unbound route, decode failure, absent/malformed summary, missing
inbound journey, differing journal counts, failed expectation, fixture error, refused link or non-fixture
transport. Numeric endpoints must be loopback. Crypto script events fail before starting the tool.
Timeouts fail and retain the attempt's stdout, stderr and exit marker.

## Remaining work counts

| Scenario | Inbound frames | Unbound | Undecodable | Unrecovered intents | Unsent frames |
|---|---|---|---|---|---|
| hero-progress | 13 | 0 | 0 | 1, master_point | 2 |
| hero-master | 4 | 0 | 0 | 1, master_point | 0 |

These are stable scenario-specific observations for later milestones to reduce. The suite does not
invent a request body or hide an unrecovered count to reach zero. The unsent frames are the existing
plaintext 0x16 refusal reports requiring the encrypted send path. That path remains outside this task.

## Checks and evidence boundary

- Eight portable runner tests cover file discovery, new-domain coverage, inbound validation, scheduling,
  endpoint restrictions, route counts and deliberately corrupted/missing evidence.
- Eight native end-to-end tests run every scenario and the skill helper, inject a speed answer through
  the real fixture, retain a readable journal after cleanup, and reject planted unbound routes, wrong
  expectations, empty journeys, non-loopback scenarios, crypto events, stale outputs and timeouts.
- Reconstructed progress source is unchanged. Its prior original-instruction comparisons remain in
  [SESSION-CORE-001](../handoffs/SESSION-CORE-001.md). No new binary recovery or Unicorn equality is claimed.
- Actual full-gate and recipe results, revisions and local artifact locations are in the
  [milestone handoff](../handoffs/VERIFY-SESSION-001.md).

No live game, wire crypto, installed data, credentials or protection modules were used for this work.
The new runner creates no sockets listener; the existing gate still tests fixture TCP separately.
This is session evidence with a stub world port. Scene login, product-world integration, the binary-derived
dispatcher and original-instruction replay remain their respective milestones. Other domains add suites
with their migrations. The skill doctor no longer looks up the original game process by name.
