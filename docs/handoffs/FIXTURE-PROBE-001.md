# FIXTURE-PROBE-001: `mu-session serve` screens stray connections

## Problem (verified)

TEST-FLAKE-001 found that the T3 Code app (the agents' host) sends `GET / HTTP/1.1` to every new 127.0.0.1
listener about every 3 s. `mu_fixture_serve` (`native/fixture/fixture.c`) served the **first** connection it
accepted and then closed its listener. A probe that landed between `fixture_listening` and the real client's
connect took the session, and the real client was then reset. The same thing could happen to anyone running the
fixture server while T3 Code or another local port scanner is open. This was seen live during this milestone: in one
run the server rejected a second `GET` peer that the test had not opened.

## What changed

- `screen_peer` (fixture.c) checks each accepted peer before serving it. The MU server speaks first, so a real
  client may stay silent, and the check is:
  - first byte `C1`–`C4` (a frame head): the peer is served. The byte is only peeked (`MSG_PEEK`), so the session
    reads the same bytes as before;
  - silent for `screen_ms` (default `MU_FIXTURE_SCREEN_MS` = 250 ms): served;
  - any other first byte (an HTTP request line), or a close or error before the first byte (a connect scan): the
    peer is a stray. It is closed, counted in the new `mu_fixture_report.rejected_peers`, and logged as
    `{"fixture_rejected": {"peer": N, "reason": "not a frame"|"closed"|"error", "first_byte": B}}`. The listener
    keeps accepting until the `--seconds` limit.
- The listen backlog goes from 1 to 8, so a real client can queue behind strays.
- `mu_fixture_serve` gains an `int screen_ms` parameter (its only caller is `mu-session serve`). The new flag
  `--screen-ms MS` sets it, and `--screen-ms -1` gives the old unscreened accept, used only by the control test.
  The final `{"fixture": ...}` line of `serve` adds `rejected_peers`.
- No change for real clients. The scenario, the step clock (which still starts at the accept that is served),
  framing, dechunking, the session checks and the `connect` side are all unchanged. A silent client starts up to
  250 ms later. A client that sends a frame first starts at once.

## Tests (`native/tests/test_fixture_hero.py`)

- `test_stray_connections_are_rejected_and_the_client_is_served` (new): the test opens a probe that sends
  `GET / HTTP/1.1` and stays open, then a connect-and-close scan, and then runs the real `mu-session connect`. The
  full round trip must pass (sockets transport, 1 link, hero level 2, the three expected frames). The probe must
  be closed by the fixture without any frame. The server log must contain `("not a frame", 0x47)` and
  `("closed", -1)`, and `rejected_peers` must equal the number of logged rejections, with 0 undecodable requests
  and no error.
- `test_unscreened_serve_hands_the_session_to_the_probe` (new control): the same probe against `--screen-ms -1`.
  The real client must **not** reach level 2, and `rejected_peers` is 0.
- `test_tcp_round_trip_over_the_sockets_transport`: unchanged in what it checks, and now shares the
  `serve`/`assert_round_trip` helpers. It asserts that `rejected_peers` equals the number of logged rejections and
  not that it is 0, because a real T3 probe can land during any run.
- The control against the real old code: the new stray test, run against `mu-session` built from origin/main
  34081544 (in a temporary detached worktree, since deleted), fails. The scan's connect is refused because the old
  server has already taken the probe and closed its listener. A probe-only variant also fails: `connect` exits 1
  with the hero at level 1. The new binary passes both.

## Checks

- Stress: 2 parallel workers × 50 runs of the whole `test_fixture_hero` module (7 tests each, every run with
  its own serve/connect pairs and the live T3 probes) = **100/100 module runs, 700 test runs, 0 failures**.
  Parallelism was capped at 2 by the brief's resource limit.
- Full gate `nice -n 10 bash scripts/local-macos-ci.sh`: see the PR body for the counts.

## Limits

- A stray that connects and stays **silent** for more than 250 ms with nothing sent is indistinguishable from a
  real MU client (the server speaks first). It is served and takes the session, as before. T3 Code's probe always
  sends its request line at once, and a connect scan closes, so both are caught. Test runs can pass a pre-bound
  listener if this ever matters.
- Screening is serial: a silent stray delays the next queued peer by up to 250 ms.
- No private validators belong to this milestone. Local scratch (`mu-mac-tools/native/scratch/fixture-probe-001/`)
  was deleted, and no later lane needs inputs from it.
