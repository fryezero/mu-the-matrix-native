# SESSION-CORE-001 handoff: the session core and the hero domain

Lane: transport-core. Branch `claude/session-core`. Plan row: `docs/design/native-port/plan.md` section C.
Contract: `docs/design/native-port/sketch/native/session/` and `sketch/MODULES.md`; the implemented sketch files (the core headers and sources, the hero domain, `session_domains.h.example`) were moved to their real paths (removed from `sketch/`); the other domains' sketches stay for stage 2.

## What changed

- `native/session/mu_session.h` (public): lifecycle, `mu_session_pump`, `mu_session_submit`, status with the
  derived protocol state, revisions, the cue reader, the place, the world port, the barrier
  (`mu_session_attach_world` / `_detach_world`), the simulation lease (`mu_session_sim_begin` / `_end`,
  `mu_session_step`), `MU_PINNED_BUILD`, the proof sources (`mu_proof_not_required` for the operator's
  account-only login).
- `mu_intent.h`: `mu_intent` over the GENERATED kinds and payloads (`build/gen/session_intents.h` from
  `domains/<d>.intents`), `mu_secret`. `mu_cue.h`: the cue types. `mu_journal.h` + `journal.c`: the journal
  (binary, versioned header with the client build digest; OPEN, FRAME in/out, INTENT, EVENT, SNAPSHOT records;
  reader with the build check; summary). `mu_session_seed.h`: `mu_session_open_seeded` (tools/tests only,
  `#error` without `-DMU_SESSION_SEED`). `mu_session_tools.h`: the dispatcher rows, intent routes and record
  zones for tools and validators.
- `session_internal.h`, `session.c` (lifecycle, pump, barrier, submit, status, world port, the no-world
  answers), `dispatch.c` (THE dispatcher from the generated route rows; the submit table), `cues.c` (the
  1024-cue ring, per-reader cursors, loss reports), `lease.c` (the lease and its audit over the domains'
  zone tables), `journal.c`.
- The hero domain, the first vertical slice: `domains/hero.h` (public `mu_session_hero`, `mu_session_money`,
  the bar's setExpData object, the speed text), `domains/hero_state.h` (CharacterAttribute, the stat machine,
  the hero CHARACTER record, money, the window/bar caches, the stat-request throttle), `domains/hero.c`,
  `domains/hero.intents` (ADD_STAT, MASTER_POINT), `ops/hero.ops` (8 routes, 2 intent routes).
  The verified `reconstructed/progress` handlers run unchanged: `mu_prg_recv_kill_exp`, `_levelup`, `_point`,
  `_master_levelup`, `_master_exp`, `_stats`, `_speed`, `_respawn`, plus `mu_prg_stat_button` /
  `mu_prg_stat_request` for the ADD_STAT intent; the env adapter turns their emit lines into cues and
  performs the state calls (`00a00f4a`, `00a00fb7`, `00c51256`, `00b40380`) where the handler makes them, as
  `core/mu_progress.c` did.
- `native/net/dispatch.seed.def`: the MU_STATIC rows of the sketch's dispatch.def (16 routes, 3 families).
  `native/net/dispatch.def` is NOT created: it belongs to the wire-research lane.
- `scripts/gen_domains.py`: joins `ops/*.ops` with the route table (dispatch.def when it exists, else the
  seed) and `ignore.def` (optional), generates `build/gen/{session_domains.h, domains_all.def,
  session_domains_state.h, ops_all.def, routes.def, bound_routes.def, session_intents.h,
  fixture_behaviors.def, gen_domains.json}` and fails on every rule of the sketch (see its docstring).
  `--no-checks` exists only for the negative build test.
- `scripts/audit_includes.py`: the include audit (rules in its docstring), run by `make test` through
  `native/tests/test_session_includes.py`.
- `native/Makefile` SESSION-CORE-001 block: the generator stamp, dev objects (`-DMU_SESSION_SEED
  -DMU_SESSION_AUDIT`, fixture included) -> `build/libmusession.a`, product objects (neither define, no
  fixture) -> `build/libmusession_product.a`.
- Tests: `native/tests/test_session_build.py` (10), `test_session_includes.py` (2), `test_session_core.py` (6),
  helpers in `test_session_support.py`.

## Checks actually run

- `test_session_build.py` **10/10**: the real tree generates; every intent kind has a submit route; the 8 hero
  rows bind the seed's addresses (0x16 -> 0x01234c08 ... 0x55 0x94 -> 0x0122a13d); a copy compiles; a
  `native/net/dispatch.def` in the copy wins over the seed; **a duplicate ops row fails the build** - the
  generator exits 1 naming both rows and writes nothing, and with `--no-checks` the generated dispatcher does
  not compile (`duplicate case value`); an MU_OP with no route, an MU_OP and an MU_IGNORE on one route, an
  intent kind without MU_SUBMIT, two MU_SUBMIT owners of one kind (and, past the generator, an initializer
  override error), a domain with state but no ops file, two behaviours with one name - each fails.
- `test_session_includes.py` **2/2**: the repository passes; 6 planted violations (a world part including
  `mu_link.h`, a GFx window including `session_internal.h` and `hero_state.h`, a client file including
  `mu_protocol.h`, `behavior.h`, `ops_all.def`) are each reported; allowed includes are not.
- `test_session_core.py` **6/6** (through `mu-session` and the fixture, FIXTURE-001): the product library has no
  `mu_session_open_seeded`, `mu_dom_hero_seed`, `mu_fixture_*`/`mu_fx_*` symbol (the dev one has them);
  **every intent kind routed** (`mu-session routes`); **the barrier**: a respawn to map 2 applies, the two
  level-ups sent at fixture steps 4 and 5 apply at tick 12 when world 2 attaches, nothing applies in between,
  attaching world 5 does not release it, re-attaching world 2 is a no-op (one "attach world 2" event), and a
  same-world respawn moves the hero through `port.place_hero` with no barrier; **cue loss**: 60 level-ups
  (1560 cues) read late give exactly 1024 cues and `lost = 536` while the per-tick reader loses none; **the
  lease audit** aborts on a write to `hero.record+0x012 (class)` and to `+0x188` during a lease, naming the
  field and journaling it first, and passes writes to the motion zone `+0x180..+0x187`; **plaintext 0x16 yields
  the client's own report**: each refused 0x16 is followed in the journal by the outbound frame
  `c1 06 4d b1 a9 9c` = `C1 06 4D 02 00 16` after undoing XorData, with Send's first argument 1, unsent
  (`needs_crypto`), and no hero state changed.
- **The 11 progress Unicorn families rerun unchanged** (`MU_RECOVERY_INTEGRATION=1`,
  `scripts/validate_progress.py --cases 500 --only calc bar table button stats speed levelup point exp master
  master_exp --mutations`, pins `2bd5f2e9…3724` / `c985e2e6…a0672f`): **11 families, 8,003 cases, 0 mismatches,
  12/12 planted mistakes caught** (calc 500, bar 500, table 3003, button 500, stats 500, speed 500, levelup 500,
  point 500, exp 500, master 500, master_exp 500). Compatibility-environment evidence (captures from the Wine
  restore), as before. `reconstructed/progress` is unchanged on this branch.
- `make test` and `scripts/audit_repository.py`: see the PR description.

## Static readings used by the hero domain

Target: restored text capture09 (`2bd5f2e9…3724`, base `0x00401000`); method: Capstone disassembly.
- The 0x16 handler's refusal path `0x01234c31..0x01234cc1` (observation): `cmp [ebp+0xc], 0` (the encrypted
  argument); Init `0x00d51b91`; Begin(`0xC1`, `0x4D`); three AddData(&b, 1, 1) for `02`, `00`, `16` (encode flag
  1: XorData on each byte); Send(1, 0). So the report is built as `C1 06 4D` + XorData(`02 00 16`) and sent on
  the encrypted path (see NET-LINK-001's reading of the wrap). The reconstruction's `report[5]` gives the
  bytes; the flags and Send's arguments come from this reading.
- The stat request `0x00b48aca` (observation): Begin(`0xC1`, `0x01`), `0x0095c204(0)` and `0x0095c204(stat)`
  (each AddData(&b, 1, 1)), Send(0, 0): a plain C1 frame `C1 05 01` + XorData(`00 STAT`).
- Coverage: these two builders only. Unresolved: whether every other request builder encodes every data byte
  (the fixture assumes so when it undoes XorData; true for the builders reconstructed so far).

## Deviations from the sketch

1. **Hooking `mu-walk --progress` / `mu-world --progress` to the session is not done (decided by the
   orchestrator).** The world lane is splitting `native/world/main.c` into a module (WORLD-RT-001) right now,
   and this lane may not edit `native/world/**` or `native/core/mu_progress.c`. Hooking the walk to the session
   is a stage-2 step after WORLD-RT-001. The slice is proven through `mu-session` and the fixture instead; the
   plan row's "`mu-walk --progress` hashes and renders identical" therefore has nothing to compare yet
   (`mu-walk` is untouched and still runs its demo).
2. The plaintext 0x16 report is not on the wire: the client sends it with Send(1, 0), the encrypted path, so
   it needs the C3 wrap (NET-DECODE-001). The session builds it with the verified builder and journals it as
   an unsent outbound frame; the fixture does not receive it until then. (The sketch expected the fixture to
   see it.)
3. Only the hero domain exists, so: the place lives in the session core (`s->place`) until the map domain;
   phase changes bump no revision (there is no account domain; views read the status each frame); the lease
   carries the hero CHARACTER record with its tile as the motion zone (`mu_sim.hero_record`), while
   `characters` / `ground` stay NULL until the viewport and ground domains; character lookups by key find
   nothing (no CharactersClient yet), the client's answer for a key outside the viewport, so the 0x16
   monster part, the damage cue and the death call do not fire.
4. Held frames are not copied into a 512-frame array: while the barrier waits, the session stops pulling, so
   the frames stay in the connection's dechunk queue, its ring and the transport (the kernel beyond). No
   capacity rule is invented; NET-DISPATCH-001 recovers the client's queue capacity.
5. The intent kinds are only those of the domains present (ADD_STAT, MASTER_POINT); kind 0 is `MU_INTENT_NONE`.
   MASTER_POINT is routed to a submit that returns `MU_SUBMIT_UNRECOVERED` (no request body is reconstructed).
6. Cues: `MU_CUE_CALL` (a client routine with no typed cue yet: window refreshes, the death routine) and a
   `json` field on window cues (the setExpData object) were added.
7. `mu_journal_summary` gained `undecodable_frames`, `unsent_frames`, `snapshots`; records an apply makes are
   written after the inbound frame's own record. Layout digest in the header is zero until LAYOUT-001.
8. `mu_session_tools.h` (routes, intent routes, zone views) is new: the tool and the tests need the routing as
   data, and `session_internal.h` is closed to them.
9. The env adapter's in-world windows (`0x0095c50b`, `0x0095c5da`, `0x009a19ae`) and the speed row's format
   fallback `"%d / %d"` (GlobalText `0x10be` when no Lang table is loaded) repeat the demo's choices; with
   `cfg.lang` NULL other GlobalText lookups give "".
10. Submit refuses (`MU_SUBMIT_NOT_NOW`) instead of asserting while pumping; lease misuse aborts only in
    audit builds.
11. `gen_domains.py` lives in `scripts/` (the brief), not `native/session/` (one sketch comment).

## Artifacts

- `native/build/gen/` (generated lists, ignored), `native/build/libmusession.a`, `libmusession_product.a`.
- Validator report: session scratchpad `validate_progress.json` (not committed).

## Open items

- LAYOUT-001 (the next milestone of this lane): the layout manifest, `layout.json`, the zone column that
  should generate the hero zone table now written by hand in `domains/hero.c`.
- `--coverage` / `--strict` (NET-DISPATCH-001): unbound frames are journaled per client address and counted;
  nothing is fatal yet.
- The account flow (SESSION-ACCOUNT-001): `mu_session_open` connects to the connect server and sits in
  CONNECTING; only seeded sessions reach IN_WORLD today.
- Equipment, buffs and the master tree in CalculateAll (`mu_prg_env.item_*`, `has_buff`): SESSION-HERO-002.

## Next step

Stage 2, after WORLD-RT-001: give `mu-walk` / `mu-world --progress` a seeded session over the fixture
(the world part reads `mu_session_hero` and replays the cues) and delete the demo half of
`core/mu_progress.c`; first in this lane, LAYOUT-001.
