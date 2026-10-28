# Fixture sessions

The dev tool `mu-session` feeds real plaintext frames from a synthetic fixture through transport,
dechunking, dispatch and the hero apply functions. A seeded session and a stub world port stand in for
login and rendering. The two hero scenarios exercise all eight bound hero routes today.

## Sub-features

- `fixture-all` discovers and runs every `native/fixture/scenarios/*.scn` with no shared list.
- `fixture-inbound` adds timed inbound frames through the existing server send path.
- `fixture-journal` preserves journals, route hits, expectations and unrecovered counts as JSON evidence.
- `fixture-reject` rejects crypto events and endpoints outside numeric loopback before running the tool.

## How to get to it (user POV)

- `$V/run-tool.sh "$RUN" NAME --fixture [SCENARIO] [--script 'T:inbound:HEX ...'] [--seed N]`.
- Omit SCENARIO to run every discovered file. Each `native/session/ops/<domain>.ops` needs at least one
  `<domain>-*.scn`; adding the domain's files is sufficient. New files must contain an inbound journey and
  expectations. Use `mu_fixture.h` for the scenario format.
- `tools/python/bin/python scripts/run_fixture_scenarios.py --report NEW_DIR` is the same suite used by CI.

## Driving it with run-tool.sh

Preconditions:

- `make -C native`, project Python, `V` and a fresh `RUN` from `new-run.sh`. No GL context is needed.

- **All scenarios.** Run `$V/run-tool.sh "$RUN" fixtures --fixture`. Exit 0, final row `summary: true`,
  `fixture: true`, `scenarios: 2`, `passed: 2`, `failed: 0`. Totals under `journal`: 17 `frames_in`,
  0 `unbound_frames`, 0 `undecodable_frames`, 2 `unrecovered_intents`, 2 `unsent_frames`.
  Each result has 0 unbound and undecodable frames, passed expectations, route hit counts and
  `unrecovered_by_intent: {"master_point": 1}`. These are today's baseline counts, not a completion claim
  for the unrecovered request body. Later milestones can track this map and the journal counters.
- **Inbound event.** Run `$V/run-tool.sh "$RUN" inbound --fixture native/fixture/scenarios/hero-progress.scn --script '60:inbound:c10c55941500000015000000'`.
  Exit 0; 14 inbound frames, including a `jnl: frame_in` row at tick 60, `apply: hero_speed`, `decode: ok`.
  Tick numbers are one-based fixture polls, not rendered frames. The event is a complete C1 speed answer.
  `$V/summary.py "$RUN/proof/inbound.stdout" journal.frames_in` gives 14;
  `--frames` lists inbound rows with route names and bytes, `--last` shows the injected speed answer.
- **Refusal.** Run `$V/run-tool.sh "$RUN" crypto-refused --fixture native/fixture/scenarios/hero-progress.scn --script '60:inbound:c303fe'`.
  Exit 1, `failed: 1`, an error requiring plaintext C1/C2, and no `command.json` or journal for the scenario.
- **Proof.** `proof/NAME/summary.json` has schema 1, the commit and binary SHA-256, totals and per-scenario
  results. Each scenario directory has its effective `scenario.scn`, `command.json`, `stdout.jsonl`,
  `stderr.log`, `exit.txt`, `session.mujnl` and `result.json` after a completed drive. `source_sha256` and
  `scenario_sha256` identify the original and effective scripts. `cleanup.sh "$RUN"` retains all proof.

## Gotchas

- Use a new NAME for each attempt. Existing report directories fail with exit 2 to prevent stale proof.
- Inbound HEX is contiguous and must contain exactly one complete C1/C2 frame fitting the fixture's
  239-character command limit. `--script` requires a single scenario. C3/C4 remains outside this recipe.
- The runner ends 20 ticks after the last timed line, including server-only lines and injected events.
- An unbound route fails the runner even if the scenario omits `expect unbound = 0`. Missing summaries,
  zero inbound frames, failed expectations, fixture errors and decode failures also fail it.
- Hero progress still refuses plaintext 0x16 and leaves two reports unsent. No crypto or live-service
  behavior is claimed. Reconstructed handler equality remains in the existing progress Unicorn evidence.
- New domain suites arrive with their migrations. The runner does not claim coverage of unmigrated domains.
