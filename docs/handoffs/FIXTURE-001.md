# FIXTURE-001 handoff: the loopback fixture server and mu-session

Lane: transport-core. Branch `claude/session-core`. Plan row: `docs/design/native-port/plan.md` section C.
Contract: `docs/design/native-port/sketch/native/fixture/` and `sketch/native/tools/mu_session.c`; the implemented sketch files were moved to their real paths (removed from `sketch/`). `scenarios/lorencia-walk.scn` stays in the sketch (its behaviours do not exist yet).

## What changed

- `native/fixture/mu_fixture.h`, `behavior.h`, `fixture.c`: the fixture server. Scenario parsing; the server
  side of each link (the verified dechunker `mu_recv`, then `mu_send_xor_decode` over every byte after the
  opcode: the client's XorData undone); behaviours called with each request in the client's layout; timed
  commands; the loopback transport through `mu_transport_wrap` (the scenario's endpoints are its allowlist:
  any other endpoint is `MU_LINK_REFUSED`; a link opens at the next step, like a connect completing); the TCP
  listener `mu_fixture_serve` (loopback addresses only, one client); services `mu_fx_send` (answers through
  the verified `mu_packet` builder), `mu_fx_rand` (xorshift32 from the scenario seed), `mu_fx_now`,
  `mu_fx_step`, and the `key=value` argument helpers.
- `native/fixture/behaviors/progress.c`: the demo server of `native/core/mu_progress.c`, **copied, not moved**
  (`mu_progress.c` is unchanged): the DEMO rules (kill experience, points per level, the per-class maxima,
  start stats and speed divisors, a point accepted while points remain) verbatim; the level thresholds from
  the client's own table `mu_prg_exp_table`. It keeps the server's own view of the hero (level, experience
  within the level, stats, points) and answers with frames: `join` (0x55 0x57, 0x55 0x94), `kill CLASS [KEY]`
  and `kill random` (0x16, then A0 06 when the server's experience reaches next), `levelup`, `master`
  (A0 22 + A0 60), `respawn map= x= y= dir= money=` (A0 30), and the client's stat request (A0 11, 0x55 0x57,
  for agility 0x55 0x94). Answers are due `latency` steps later.
- `native/fixture/scenarios/hero-progress.scn`: the slice's scenario (13 expectations).
- `native/tools/mu_session.c` -> `build/mu-session`: `routes`, `behaviors`, `fixture SCENARIO` (a headless
  seeded session against the in-process fixture: JSON rows per client action and per journal record, the
  hero, the status, cue counts, the fixture report, the transport counters, the expectations, the journal
  summary; exit 1 when an expectation fails), `connect SCENARIO --to HOST:PORT` (the same over the product
  sockets transport, client lock included; loopback only), `serve SCENARIO --port N` (the fixture on
  127.0.0.1), `journal FILE`, `replay` (reports the stub). The tool is the world tool of this slice: it seeds
  the session from the scenario's `join` line and attaches a stub world port (tile only).
- `native/Makefile` FIXTURE-001 block: `build/mu-session`.
- `native/tests/test_fixture_hero.py` (5 tests).

## Checks actually run

- `test_fixture_hero.py` **5/5**:
  - **the fixture's real C1 frames reach the hero domain** (transport -> dechunk -> dispatch -> `mu_prg_recv_*`):
    `hero-progress.scn` passes its 13 expectations; all 13 inbound frames are C1 on the game connection,
    decode `ok`, and each lands on the apply function and client handler its route names (0x55 0x57, 0x55 0x94,
    0x16, A0 06, A0 11, A0 30); 0 unbound, 0 undecodable; the fixture saw 2 requests, 0 undecodable;
  - **A0 06 and A0 11 update the hero**: level 2, 5 points, next 340, HP/MP 1102/200 and SD/AG maxima 55/25 (the
    demo server's values for a Dark Knight), then the vitality point: 4 points, HP max 1105, vitality 26;
  - the stat request leaves as `Send(0, 0)` through the verified builder and decodes (XorData undone) to
    `C1 05 01 00 02`;
  - **two seeds, two reproducible journals**: ten `kill random` lines; seed 7 twice gives byte-identical journals,
    seed 8 a different one;
  - **TCP**: `mu-session serve` on a free 127.0.0.1 port and `mu-session connect` (the product sockets transport,
    lock file in a temp dir, a random process-name list) carry 0x55 0x57, 0x55 0x94 and A0 06; the hero
    reaches level 2; the server exits 0 when the client closes;
  - `connect --to 192.0.2.1:44405` is refused before any transport exists (exit 2).
- `test_session_core.py` (SESSION-CORE-001's behaviour checks) runs through this fixture: 6/6.
- `make test` and `scripts/audit_repository.py`: see the PR description.

## Deviations from the sketch

1. **C1/C2 only.** The mirror CryptoModule does not exist before NET-CRYPTO-001 / NET-DECODE-001: an encrypted
   request is counted as undecodable, `mu_fx_send(.., encrypted)` refuses, and the progress behaviour sends
   0x16 as C1 (`kill_head=c1`, the only accepted value) - which the client refuses with its 4D report. So
   until the crypto lane lands, kill experience never applies; level-ups come from the server's own count.
   The plan row's "C3 both directions" is not done.
2. `behavior.h` gained `on_command` (scenario commands `at TICK progress kill 12`): the sketch's kill comes from a
   combat behaviour, which does not exist before SESSION-COMBAT-001.
3. `mu_fixture.h` gained `mu_fixture_endpoint`, `mu_fixture_script_get` (the `join`, `at TICK client ...` and
   `expect` lines for the tool), `mu_fixture_behavior_names`, and the argument helpers; `mu_fixture_serve`
   takes a step interval and serves one client.
4. The scenario format is this lane's (documented in `mu_fixture.h`); the sketch's `lorencia-walk.scn` needs
   behaviours (account, players, ground, combat, npc, map) that arrive with their domains, so it is not
   moved into place.
5. The behaviour list is generated by `scripts/gen_domains.py` (into `build/gen/fixture_behaviors.def`), not a
   separate generator.
6. No `mu-fixture-server` binary: `mu-session serve` is the TCP fixture (FIXTURE-001's tool list in the brief
   names only `mu-session`).
7. The fixture undoes XorData over every byte after the opcode (true for the request builders reconstructed
   so far, see SESSION-CORE-001's static readings); a request with other encode flags would need its own rule.

## Artifacts

- `native/build/mu-session` (ignored). Journals of test runs live in temp dirs and are deleted.

## Open items

- C3/C4 in both directions (after NET-DECODE-001): the server half of the CryptoModule, 0x16 as C3, the 4D
  report on the wire.
- Behaviours for the other demo servers arrive with their domain migrations (stage 2).
- `mu-walk` / `mu-world` fed by the fixture: stage 2 after WORLD-RT-001 (see SESSION-CORE-001).

## Next step

VERIFY-SESSION-001 can run `mu-session fixture` scenarios in CI as they are; LAYOUT-001 is this lane's next
milestone.
