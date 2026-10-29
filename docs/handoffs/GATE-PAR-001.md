# GATE-PAR-001: a faster local gate, same tests

## What changed

- `Makefile`: the 38 `make test` discoveries moved, unchanged and in the same order, into one variable,
  `TEST_SUITES`. `test: all` now runs `$(PYTHON) scripts/run_test_suites.py $(TEST_SUITES)`. `make test` still
  builds first (`all`), runs the same suites and uses the same Python.
- `scripts/run_test_suites.py` (new):
  - `MU_GATE_JOBS=1` is the old behaviour: suites in Makefile order, output streamed, stop at the first failing
    suite.
  - Otherwise it runs a pool of `MU_GATE_JOBS` workers (default `min(4, cores/2)`, 4 on this Mac).
    `native/tests` is about 97% of `make test`'s time, so it runs as one work item per `test_*.py` module (the same
    discover start directory and import names) and its counts are summed back into one row. Sharding is refused if
    the directory ever holds a test package.
  - The longest items start first, using the durations of the last run (`verify-runs/test-suite-times.json`) or,
    on a first run, the built-in measured order.
  - Each item gets its own log in `verify-runs/test-suites-*/`, its own `TMPDIR` under `/tmp/mugate-*`, and a
    `make` shim on `PATH` that holds one lock for the length of each build. Two suites never build into
    `native/build` or `reconstructed/*` at once, and after `make all` those makes are no-ops.
  - It prints one row per suite (secs, ran, passed, skipped, failures, errors) and the totals. Every suite runs to
    the end. The exit status is non-zero if any suite failed, and each failing log's last 60 lines are printed.
  - A helper module named `test_*.py` with no tests (`test_session_support.py`) exits 5 when it runs alone. That
    counts as success for shards only, as it always did inside the whole discovery.
- `scripts/local-macos-ci.sh`: has the same arguments and is still the gate.
  - With `MU_GATE_JOBS=1` it runs the old steps, in order.
  - Otherwise, after `make test`, the fixture scenarios, `make native-viewer`, `make live-readers` and the audit run
    side by side. Each writes its own log in `verify-runs/ci-stages-*/`, and a failing stage prints its tail and
    fails the gate.
  - These four stages write disjoint outputs, and the native/tests suite has already built the viewer targets. The
    audit reads the git index.
- `tests/test_run_test_suites.py` (new, 8 tests) checks:
  - the `test:` recipe is exactly the runner call, no other discover line exists, and the `make -n test` arguments
    equal the runner's own list;
  - every directory holding tracked `test_*.py` files is in `TEST_SUITES`, except the one named exception
    (`reconstructed/players`, never in `make test`; adding it is its owner's change);
  - a deliberately failing synthetic suite fails the pool (exit 1, its log tail, exact summed counts) while the
    other suites still run;
  - `MU_GATE_JOBS=1` stops at the first failure;
  - sharding gives the same counts as one discovery;
  - the summary parser, and `MU_GATE_JOBS` validation.
- `tests/test_validators_manifest.py`: reads the suite list through `run_test_suites.makefile_suites()` instead of
  the old discover-line regex.
- `native/tests/test_fixture_hero.py`: the TCP round trip picks a free port, closes it and has `mu-session serve`
  bind it. That is a race with any concurrent process, so a failed listen now retries on a new port (up to 5 tries).
  This is the only fixed-port or picked-port pattern among the real-socket tests. `test_transport` already binds
  port 0, and its locks and process names are per-test.

## Measurements (same Mac, warm build, nice 10, other lanes running)

| run | gate wall | `make test` | peak load (1 min) | min free memory | swap |
|---|---|---|---|---|---|
| main `f7a1e338`, sequential (stage by stage) | 355 s | ~340 s | ~11 | 75% | 10 MB |
| branch, `MU_GATE_JOBS=1` | 352 s | 334 s | 16.7 | 75% | 10 MB |
| branch, parallel run 1 | 130 s | 108 s | 13.4 | 75% | 10 MB |
| branch, parallel run 2 | 120 s | 105 s | 11.4 | 75% | 10 MB |
| branch, parallel run 3 | 116 s | 100 s | 19.2 | 74% | 10 MB |

Load is machine-wide and includes other lanes. The pool's largest process had a 518 MB peak RSS, and the whole
`make test` took 346 s user + 44 s sys of CPU.

Slowest suites, sequential on main:

| suite | secs |
|---|---|
| native/tests | 324.3 |
| (audit stage) | 13.7 |
| reconstructed/model-codec | 3.9 |
| tests | 2.0 |
| reconstructed/path | 1.0 |
| reconstructed/price | 0.6 |
| reconstructed/objects | 0.6 |
| reconstructed/items | 0.6 |
| reconstructed/mix | 0.4 |
| reconstructed/ui | 0.3 |

The other 28 suites take ≤0.3 s each. Slowest `native/tests` modules in the pool: test_native_perf004 42–51 s,
test_native_shell 25–31, test_native_viewer 17–19, test_native_app 17–21, test_native_terrain 12–15,
test_native_stress 11–15, test_native_build_deps 10, test_native_combat 8–12, test_native_players 8–11 and
test_inventory_skin 11. The longest module (~45 s) is the new floor, so most of the remaining gate time is the
fixed stages and that module.

## Checks

- Counts: per-suite rows (ran/passed/skipped/failures/errors) of `MU_GATE_JOBS=1` and parallel run 3 are
  **identical for all 38 suites**: 1,708 tests, 1,489 passed, 219 skipped, 0 failures, 0 errors. Main had 1,700
  tests with 219 skipped; the +8 are the new runner tests.
- Three parallel gates in a row: 3/3 pass, no flakes. Each had 11/11 fixture scenarios and an audit of
  1,678 files with 0 rejected.
- Planted failures: `make test` with a failing `test_zz_planted.py` in `reconstructed/pets` exits 2 and prints the
  failing log tail. A planted `native/tests/test_zz_planted.py` is in the shard list automatically. Both files
  were removed.
- `test_transport` ran 4 copies at once for 10 rounds: 40/40 passed.

## Limits and next steps

- The previously observed `test_transport` allowlist failure did not reproduce. The test already uses port 0, and
  per-test lock paths and process names. Its "nothing reached the refused peer" check accepts on a real loopback
  listener for 0.2 s, so any stray loopback connect to that port from another process on the Mac would still fail
  it. The `connects_attempted == 0` counter is the in-process proof. If it recurs, capture its traceback.
- The default pool is 4 workers, as the milestone specified. That is above the brief's "--jobs 2 for parallel
  Python" note. `MU_GATE_JOBS=2` is the knob if the steward wants it.
- The build (`make all`) stays serial. On a warm tree it takes about 1 s; after a large merge it is the old cost.
- `reconstructed/players/test_remote_players.py` is not in `make test` (before or after). It is named as the one
  exception in `tests/test_run_test_suites.py`.
- No private validators belong to this milestone.
