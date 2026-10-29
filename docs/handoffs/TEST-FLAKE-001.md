# TEST-FLAKE-001: the allowlist test without a timing window

## Root cause (verified)

`native/tests/test_transport.py::Transport::test_allowlist_refuses_before_connect` failed in parallel gates with:

```
  File ".../native/tests/test_transport.py", line 185, in test_allowlist_refuses_before_connect
    with self.assertRaises(socket.timeout):   # nothing ever reached the refused peer
AssertionError: TimeoutError not raised
```

The test checked "nothing reached the refused peer" by calling `accept()` on that peer's loopback listener for 0.2 s.
Another process did connect: **the T3 Code app (the agent host) probes every new 127.0.0.1 listener about every
3 s** with `GET / HTTP/1.1` (identified with `lsof` on the accepted connection's source port: `T3 Code`, pid
1889). Whenever a probe cycle fell inside the 0.2 s window, `accept()` returned the probe and the test failed. The
transport was not at fault. Its refusal path is synchronous and in-process, and `connects_attempted` stayed 0 in
every failing run.

- Reproduced with no other load, in one process: 4 failures in 60 runs at runs 6, 21, 36 and 51. That is one every 15 runs ≈
  3 s at 0.2 s per run. With four workers in parallel, all four failed at the same run numbers, since one probe
  cycle catches every listener. Under the stress below, the old test failed 20/300.
- Why it looked like a GATE-PAR-001 flake: the gate's agents run under T3 Code. Running the test alone takes about 1 s, so
  it rarely overlaps a probe; a whole gate runs it while probes keep coming. It was not caused by ports, TIME_WAIT,
  a shared listener, or connection order. Ports are per-process (`bind(0)`) and the lock paths are private.

## What changed

- `native/tests/connect_spy.c` (new, test-only) records the calls a process makes at the socket boundary
  (`getaddrinfo` with its port, `socket` with its family, and `connect`/`connectx` with the destination port) and passes each
  one through unchanged. macOS uses dyld `__interpose`; Linux uses `LD_PRELOAD` with `dlsym(RTLD_NEXT)`. It is built
  as `native/build/libmuconnectspy.{dylib,so}` by `native/Makefile` (`all`).
- `test_allowlist_refuses_before_connect`: the in-process checks are unchanged: state `MU_LINK_REFUSED`, the
  write is refused, counters (1, 0, 0), and the allowed link connects. The 0.2 s accept is replaced by `probe()`,
  which runs the same scenario in a child interpreter with the spy inserted (`DYLD_INSERT_LIBRARIES`/`LD_PRELOAD`)
  and checks `allowlist_violations()`:
  - the refused open makes **no** socket-boundary call at all: no lookup, no `socket`, no `connect`. That is
    stronger than the old check, which only proved that no connection was accepted within 0.2 s;
  - positive control: the allowed open made exactly `getaddrinfo(port)`, `socket(AF_INET)` and `connect(port)`.
    So the spy is live, and if an interpreter ignores dyld insertion (e.g. a SIP-protected `/usr/bin/python3`)
    the test fails and says so instead of passing.
  The only wait left is the bounded `accept()` of the allowed connection, which must arrive. No check relies on a
  window staying empty.
- New negative control, `test_allowlist_check_catches_refusal_after_connect`: it builds two mutant `libmunet`s
  (clang `-O0`, in the test's temp dir) from `transport_sockets.c`, with the allowlist check moved:
  - after `connect()`, with `connects_attempted` decremented so the in-process counters still read right
    (1, 1, 1). Only the socket boundary shows the bug, and the check reports `['connect', <refused port>]`;
  - after `getaddrinfo()` and before `socket()`. The check reports the lookup.
  Both mutants fail `allowlist_violations()` with exactly one finding; the real library has none.

## Checks

- Before the fix, under the same stress, the old test (from origin/main) failed 20/300 with the traceback above.
- After the fix, during the same 90 s, with 2 loops of `test_fixture_hero` (serve/connect loopback load) in the
  background: 4 workers × 150 runs of `test_allowlist_refuses_before_connect` = **600/600 pass**, plus 60/60 runs
  of the whole `test_transport` module (12 tests each). An earlier pass of 4 × 60 + 30 modules also had 0
  failures.
- Spy not inserted (variable name mangled on purpose): both allowlist tests fail with "the allowed open made
  [] ... is DYLD_INSERT_LIBRARIES honoured". This was reverted.
- Full gate `nice -n 10 bash scripts/local-macos-ci.sh` (after merging origin/main 3021799a): 38 suites,
  1,754 tests, 1,524 passed, 230 skipped, 0 failures, 0 errors; fixtures, viewer, live-readers ok; audit 1,743
  files, 0 rejected.

## Sweep of other native/tests socket windows

Only `test_transport.py` and `test_fixture_hero.py` open sockets.

- `test_fixture_hero.py::test_tcp_round_trip_over_the_sockets_transport`: the same cause could hit it, with a
  narrower window. `mu-session serve` (native/fixture/fixture.c) accepts the **first** connection and closes its
  listener. A T3 probe that lands in the few milliseconds between `fixture_listening` and the test's
  `mu-session connect` would be taken as the client. Not fixed: 0/160 failures in 4 parallel workers, and the fix
  belongs in fixture.c (another lane's file). Possible fixes: serve keeps listening and drops a peer whose first
  bytes are not a C1–C4 frame, or the test passes serve a pre-bound listening fd. The free-port pick before serve
  binds already retries (GATE-PAR-001).
- `test_transport.py`, the two client-process lock tests: they `time.sleep(0.2)` after `Popen`, but this is not a
  socket window. `Popen` returns after the child's exec, so its argv is already visible, and the sleep only adds
  time. Left as is.
- The other `test_transport` waits are bounded condition polls (5 s deadlines for OPEN, frames, the receive guard), not
  windows that must stay empty.

## Limits

- The spy sees calls made through the C library, not raw `syscall()` (the transport never makes raw calls).
- The child-interpreter check needs an interpreter that honours dyld insertion. The gate's `tools/python` (Homebrew
  3.12, ad-hoc signed, no hardened runtime) does, and the positive control fails loudly if one doesn't.
- No private validators belong to this milestone. Local scratch (`mu-mac-tools/native/scratch/test-flake-001/`) was
  deleted; no later lane needs inputs from it.
