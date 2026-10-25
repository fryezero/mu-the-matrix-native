# The rest of the native port: a server-authoritative session core

## Problem

The native client plays the original scene flow and world, but no byte reaches a network. Every server answer
comes from a DEMO stand-in inside the subsystem that needs it, fed in one of three ways: plaintext bytes into a
handler, structs that skip the handler, or text files. The owner has now set the end state: log in to the real
Mu The Matrix service as the Windows client does, and keep the demo servers only as offline test fixtures.
Several things make the shape non-obvious:

- **Replicated state has no owner.** Zen sits in four counters (`mu_map.c:76`, `mu_social.c:70`,
  `mu_gfx_layer.c:2164`, `mu_quest.c:177`). The hero class comes from three sources. HP lives in combat, level in
  progress, the HUD's values in the GFx layer (three setters). The inventory exists only in the GL GFx layer, and
  quests exist only in GL builds. All of it is per world visit, so it resets at character select, and `mapsess`
  leaks. A "money changed" packet has nowhere to land.
- **The reconstructed handlers are the main asset, and they write their own state.** They take client-shaped
  records: `mu_prg_recv_levelup(env)` writes CharacterAttribute bytes at client offsets, `mu_rp_move_packet`
  writes a CHARACTER record and asks the world for PathFinding2, `mu_quest_receive` writes the whole quest client
  including its window-handler state, and `mu_npc_talk_result` returns a list of client calls. They must stay
  unchanged (Why row 1). So "decode to a typed event, then apply natively" would mean rewriting verified logic.
- **The scene manager's verified boundary is routine addresses and client records** (Why row 6). The network
  layer has to answer the same host calls and fill the same records.
- **One thread and a fixed tick order** (Why row 9). Frames must reach the handlers on the main thread, at the
  client's queue-drain point, in arrival order. The `on_step` order must hold.
- **The protection boundary.** The launcher session (localhost:55232, IGC.dll) and anything IGC adds to the
  traffic are opaque, and must stay out of the work. Session establishment is an external contract input
  (seam 1, BLOCKED).
- **Wiring cost.** A subsystem touches about 14 places, and a feature flag has to be synced across four layers.

## Usage (caller's view)

### What a front-end author reads

> A **session** is one login to the service. Open one when the login scene connects, and call
> `mu_session_pump` once per frame. Draw from what it holds and, when the player acts, submit an **intent**.
> You never see a packet. The session decides what bytes to send and what incoming bytes mean, and it is the
> only thing that changes game state. The world runtime is opened on a session and loads whatever world the
> session says the hero is in.

```c
/* native/client/main.c - the whole network story of the front end */
mu_endpoint service = settings.endpoint;                          /* from the operator contract */
mu_transport *net = dev_fixture ? mu_fixture_transport(fixture)   /* tests: wire-level fake server */
                                : mu_transport_sockets(&service, 1, err, sizeof err);
shell_cfg.session = (mu_session_config){.connect_server = service, .transport = net,
                                        .build = &MU_PINNED_BUILD, .proof = mu_proof_not_required(),
                                        .lang = lang, .game_root = root, .journal = journal};
mu_shell *shell = mu_shell_new(&shell_cfg, &platform, err, sizeof err);
for (;;) {
    uint32_t now = clock_ms();
    mu_transport_poll(net, now);          /* bytes in; nothing applied yet */
    pump_sdl(shell);                      /* input -> GFx -> router -> mu_session_submit */
    mu_shell_frame(shell, now);           /* mu_session_pump at the client's queue-drain point, then the scenes */
    compose(shell);                       /* views read const state */
    mu_transport_flush(net);              /* bytes out */
    sleep_ms(mu_shell_end_frame(shell));
}
```

### Call site: the scene shell answers the verified scene manager from the session

```c
case 0x0121c055u:                                   /* connect (scene.c:194) */
    if (!s->session) s->session = mu_session_open(&s->cfg.session, s->status, sizeof s->status);
    return s->session != NULL;
case MU_SCENE_NET_SEND:                             /* one record id, two sends: join (scene.c:260) or tail (:125) */
    if (s->last_routine == 0x009a13f4u)             /* the join follows the CharactersClient lookup */
        mu_session_submit(s->session, &(mu_intent){.kind = MU_INTENT_JOIN, .u.join = {s->g.selected_hero}});
    else                                            /* the tail follows 0x00ac9be9, in every scene */
        mu_session_submit(s->session, &(mu_intent){.kind = MU_INTENT_KEEPALIVE});
    return 0;
/* each frame, before mu_scenemgr_dispatch: */
mu_session_status st; mu_session_status_get(s->session, &st);
s->g.protocol = st.protocol_state;                  /* derived, never set by the host */
if (st.phase == MU_PHASE_IN_WORLD && waiting_for_join) mu_scenemgr_start_loading(&s->host, &s->g, 1);
```

### Call site: a GFx window is a view plus intents

```c
static void inventory_sync(void *self, struct mu_gfx_movie *m, const mu_session *s)
{   /* runs only when MU_DOMAIN_INVENTORY or MU_DOMAIN_HERO changed; running it twice pushes the same values */
    const mu_inventory *inv = mu_session_inventory(s);
    for (int i = 0; i < inv->count; ++i) gfx_set_cell(m, &inv->cells[i]);
    gfx_set_money(m, mu_session_money(s));          /* the only Zen there is */
}
static int inventory_callback(void *self, struct mu_gfx_movie *m, mu_session *s, const char *name, const char *args)
{
    mu_intent in = {.kind = MU_INTENT_MOVE_ITEM, .u.move_item = {MU_STORE_INVENTORY, from, MU_STORE_INVENTORY, to}};
    mu_submit r = mu_session_submit(s, &in);
    if (r.status == MU_SUBMIT_REFUSED) gfx_notice(m, r.notice);       /* the client's own local refusal */
    if (r.status == MU_SUBMIT_UNRECOVERED) gfx_dev_banner(m, "item move request not reconstructed");
    return 1;   /* the item moves when the server's answer changes the inventory revision */
}
```

### Call site: a world part ticks session records under a lease and replays cues

```c
static void characters_tick(mu_world_rt *rt, void *self, mu_sim *sim)    /* MoveCharacters, client order */
{
    for (int32_t i = 0; i < sim->character_count; ++i)
        if (sim->used[i] && i != sim->hero_index)
            mu_rp_move_step(&sim->characters[i], &rt->rp_env, &calls);   /* verified, unchanged */
}
static void combat_frame(mu_world_rt *rt, void *self, float dt)
{
    mu_cue cue[64]; uint32_t lost;
    size_t n = mu_session_cues(rt->session, &((combat_part *)self)->cues, cue, 64, &lost);
    for (size_t i = 0; i < n; ++i)
        if (cue[i].kind == MU_CUE_DAMAGE) spawn_damage_text(self, &cue[i].u.damage);
}
```

### Call site: a domain author wires one more server packet

```c
/* native/net/dispatch.def, generated from the client's jump table (the author does not edit it):
 *   MU_ROUTE(0xA0, 0x06, 0x01250b05u, MU_VERIFIED)
 * native/session/ops/hero.ops: the one row the author writes */
MU_OP(0xA0, 0x06, hero_levelup)

/* native/session/domains/hero.c */
mu_apply hero_levelup(mu_session *s, const mu_frame *f)
{
    mu_prg_env env; hero_env(s, &env);             /* session records in, engine calls out as cues */
    mu_prg_recv_levelup(&env, f->bytes);           /* the verified handler, unchanged */
    mu_session_touch(s, MU_DOMAIN_HERO);
    return MU_APPLY_DONE;
}
```

### Call site: tests and gate-3 evidence use the same session

```python
run = run_fixture("mu-shell", scenario="native/fixture/scenarios/lorencia-walk.scn",
                  script="40:click:monster 80:key:1 120:key:space", frames=400)
assert run["scene"] == 6 and run["journal"]["unbound_frames"] == 0 and run["journal"]["c3_frames"] > 0
# private: every inbound frame re-run through the ORIGINAL dispatcher, seeded from the native records
oracle = replay_oracle(run["journal_path"], TEXT, DATA, Path("native/build/gen/layout.json"))
# private, gate 3: the owner's recorded original-client stream replayed into a native session,
# every record compared field by field with live-readers/memread snapshots at the same WorldTime
report = compare_session(Path("verify-runs/live-0001/session.mujnl"), live_snapshots,
                         Path("native/build/gen/layout.json"))
```

## Shape

### Data structures first

**The session stores the client's own records, and hands out typed views.** Where a verified handler writes a
record (CharacterAttribute, the stat machine, the hero CHARACTER's replicated part, the CharactersClient table of
`mu_rp_character`, the Items[] pool of `mu_gi_item`, `mu_quest_client`, `mu_party`, `mu_trade`,
`mu_social_messages`, the skill structs), the session stores exactly that type, at session lifetime, and passes it
to the handler. Views get derived domain types (`mu_hero_stats`, `mu_viewport_view`, `mu_session_money`) or const
pointers to reconstructed record types. They never get raw bytes or frames. There are three reasons. The verified
code stays unchanged, because its arguments are what it was proved with. Nothing keeps a second copy, because the
view is computed from the record. And because every domain is in client layout, `memread` captures of the original
compare field by field with the native session at a matching WorldTime, which is the gate-3 evidence that has
never existed (per *single source of truth*: derive, don't sync).

Trace of the dominant access patterns:

- *Packet for character key K.* A linear scan of 400 entries by the client's own lookup rule. The client does the
  same, so slot choice, and with it the memread index, matches. No map is needed.
- *Every tick over all characters, every frame for rendering and picking.* An array walk over `used[]`.
- *A render cache per character.* Keyed by `(index, generation)`, so a reused slot cannot inherit a mesh.
- *Ground item by key.* The key is the pool slot (keys of 1000 or more become 0, `ground_items.h`), so this is
  direct indexing.
- *"Did my window's data change?"* One `uint32_t` revision per domain.
- *"What just happened?"* A cue ring with one cursor per reader.

**Three write channels, and only session code behind them** (per *one owner per piece of state*):

| Channel | When | What it writes |
|---|---|---|
| `mu_session_pump` → dispatcher → apply functions | once per frame, at the queue-drain point | replicated state, cues, answers the client sends from inside handlers |
| `mu_session_submit` | input and tick phases, never during pump | pending-request flags and throttles, plus request bytes to the transport |
| `mu_sim` lease (`sim_begin`/`sim_end`) | inside each 40 ms logic step | motion and animation fields of CharactersClient and Items[] only. Debug builds snapshot the replicated fields and abort on a change, using the zone column of the layout manifest, which also generates the journal dump and the projection adapters |

On "two actors write — what happens?": CharactersClient really has two writers in the original too (handlers and
MoveCharacters, serialized on the UI thread). Here they are serialized by phase. The lease makes that serialization
explicit, and the audit enforces the field split. The hero's *motion* has one writer, the world's `mu_walk`. Server
placements reach it through `port.place_hero`, which runs world code, and handlers read it through
`port.hero_motion`. Window UI state belongs to each view. Nothing is written by two parties without a defined
phase.

**Change propagation is derived and idempotent.** Views compare revisions and re-read, and re-reading is harmless.
Cues are one-shot and cosmetic, and state never depends on whether a cue was seen; a reader that falls behind gets
`lost` and keeps going. The world loads `mu_session_place().world` and travels when that differs from the loaded
world, so running travel twice is a no-op. `mu_session_attach_world` for the world already attached is a no-op.
Pumping during the barrier applies nothing. A second JOIN while joining is `NOT_NOW`. A crash loses nothing, because
the server is authoritative; the next launch is a new login.

### The flow through the signatures

```text
mu_transport_poll ─ link bytes ─► mu_session_pump
   └─ mu_net_next: mu_recv_push/drain (verified) ─► mu_decode (0x01221b94: C3/C4 Decrypt, serial) ─► mu_frame
   └─ mu_session_dispatch (generated from ops/*.ops; routes = the client's jump table, checked)
        └─ <domain>_apply(s, frame) ─► env adapter ─► reconstructed handler(record, bytes, env)
             ├─ record writes = domain state ─► mu_session_touch(domain) ─► views re-read
             ├─ engine calls ─► cues ─► views replay
             └─ MU_APPLY_WORLD_CHANGE ─► barrier until mu_session_attach_world(port for that world)
mu_world_rt_input / window callbacks / shell ─► mu_intent ─► mu_session_submit
   └─ <domain>_submit: the client's local checks ─► reconstructed request builder ─► mu_packet (verified)
        ─► mu_net_send (0x00d51e8c wrap: serial, g_enc) ─► mu_transport_flush
```

### Load-bearing decisions

1. **One dispatcher; the routing is generated from the binary.** `scripts/gen_dispatch.py` reads the 254-entry
   jump table `0x0128e59d` and every sub-dispatcher from the restored text and writes the checked-in
   `native/net/dispatch.def` (families with their C1/C2 sub offsets, routes with the client handler address);
   `validate_dispatch.py` runs `0x01287ead` under Unicorn with stubbed handlers and requires the table to match
   row for row. A domain's `ops/<d>.ops` row only binds an apply function to a route, so no author restates an
   address or an offset. The build fails when a row names no route or two rows bind one; a route with no row is
   *unbound*: counted per client address in every journal, listed by `--coverage`, fatal under `--strict`. The
   remaining network work is therefore a derived list, not a hand-kept one (per *encode lessons in structure*).
   Client record offsets get the same treatment: one layout manifest (`native/session/layout/*.def`) generates
   the accessors, the projection adapters' field tables, the lease audit, the journal dump and the `layout.json`
   that `memread`, the replay oracle and the validators read; overlapping declarations fail the build.
2. **No invented bytes, visible as a type.** `MU_SUBMIT_UNRECOVERED` and `MU_CUE_UNHANDLED` exist so that views can
   be written against intents whose builders, or frames whose bodies, are not recovered yet. Each such gap is
   journaled in every run, so the remaining work shows up as counts, not as silent demo behaviour (evidence rule).
3. **World-change barrier.** After a join answer or a cross-map teleport, application pauses until the world
   runtime attaches the matching world port. This reproduces the client's blocking load: the message pump waits.
   It also guarantees that handlers needing PathFinding2 or terrain height never run without the right world.
4. **The transport is the only path to a socket.** Three implementations sit behind one interface: sockets with an
   allowlist, fixture loopback, and replay. The allowlist admits the configured connect server and whatever
   endpoints the session learns from F4 03 or a room answer. It replaces the `mu-nonet` dyld guard, which is
   incompatible with hardened runtime and notarization (gate 5). A symbol test keeps fixture code out of the
   product.
5. **The demo servers become wire-level fixtures.** `native/fixture` speaks C1–C4 through the same `mu_conn` code
   in the server role, with a mirror CryptoModule, and its behaviours are the former demo servers. A behaviour may
   only emit layouts that have a dispatcher row. The fixture also listens on TCP, so the signed app binary can be
   tested black-box (gate 5) with no fixture code inside it.
6. **Session establishment is a plug-in point, not code.** The login encoder fills each field of the
   reconstructed login body by provenance: user (from `mu_secret`), build (pinned bytes from the restored text), or
   launcher (`mu_login_proof_source`). The repository ships only `mu_proof_not_required()` and
   `mu_proof_unavailable()`, and the latter closes with `MU_CLOSE_NEEDS_OPERATOR_CONTRACT`. Nothing forges, replays
   or analyses launcher or IGC material.
7. **The world is a runtime over the session, not a copy of it.** `world/main.c` becomes `mu_world_rt` plus
   `parts.def`, one row per subsystem with the client's tick order and draw order. `mu-world`, `mu-walk` and
   `mu-client` become thin front ends. Feature flags disappear from the product, because the server decides what
   exists. Quests, inventory and HUD now survive character select, and they exist in headless builds, because they
   live in the session.
8. **One input router in the world** (`mu_world_rt_input`). It applies GFx first refusal, then the key scan, panel
   bindings, hotkeys and finally walk/attack, and its outputs are intents. The cast, pick-up and right-click paths
   that `mu-client` could not reach become reachable.

### Interface depth

The mutating public surface is `open`, `close`, `pump`, `submit`, `attach_world`/`detach_world` and the lease, with
the read surface as revisions, cues and per-domain getters. Behind it sit transport selection, dechunking, the
CryptoModule with rekeying, serials, the connect-to-game-server hop, the chat connection, the decode stage,
dispatch, sub-dispatch by head family, every handler's env adaptation (GlobalText, item queries, buffs, the world
port, the projection adapters), call-list-to-cue translation, request builders, client throttles and local
refusals, the barrier, the journal and redaction. A view author learns three verbs: read a domain, replay cues,
submit an intent. Wire and transport types (`mu_frame`, `mu_packet`, `mu_conn`, heads, opcodes, channels) cannot be
included from outside `native/session`, `native/net` and `native/fixture`; the include audit fails the build
otherwise (per *importable internals*).

### Where this direction strains, said plainly

1. **The handlers fuse decode, state write and engine calls.** Typed server *events* cannot be the input of apply
   without re-deriving verified logic. In this shape the typed events are the *outputs*: revisions over typed
   state, plus cues. The frame stays private to the session. I think this is the right compromise, but it means
   the "typed server event" layer is thinner than a greenfield design would have.
2. **One client record mixes replicated and simulated fields** (CHARACTER: equipment and hp next to path and
   action). The session owns the record, and the world gets write access to motion only, through the lease. The
   field split is a table and a debug audit, not a type, because the C struct is the reconstructed one and cannot be
   split without touching `reconstructed/players`.
3. **The hero record is split by zone.** Replicated hero bytes live in the session; motion lives in `mu_walk`.
   Handlers that read the hero's tile get it through the port, refreshed right before the call. This is the one
   place where a record is assembled from two owners at a call boundary.
4. **Reconstructed families chose different projections of the same client record.** Progress uses 0x400-byte
   CHARACTER buffers; players uses `mu_rp_character`. The session's canonical type for characters is
   `mu_rp_character`. A projection adapter builds a byte view for the progress lookups (`env->character`) and
   writes back what the handler wrote, driven by the same generated field table. It is a marshalling step, contained
   to one file, with a round-trip test.
5. **Some UI-handler state is session state**: the quest client's windows, the stat window's copy, messenger rooms.
   The verified handlers write it together with replicated data, as the client's globals do. Windows over that
   state forward their events as their own generated intent kind (`MU_INTENT_WINDOW_QUEST_PROGRESS`, ...), routed
   like every other intent, and the session runs the reconstructed window handler. The session therefore carries
   some UI logic. It is the faithful choice, and the less pure one.
6. **Handlers need world services at apply time** (PathFinding2, terrain height, SetAction). Hence the world port.
   Without one, the session answers the way the client does with no world loaded, and the barrier prevents that
   from ever applying in-world frames.
7. **Bodies we do not have yet strand the fixture.** The monster viewport `0x13`, the account and join bodies,
   SendMove and the attack request are not reconstructed. Until each lands, its domain keeps its old demo path
   (one path per domain at any time, flipped by that domain's migration milestone). World tools seed a joined
   session from a scenario's `join` line through `mu_session_seed.h`, which is compiled out of the product.
8. **What it deliberately does not do:** no client-side game rule the client does not have, no prediction beyond
   the client's own local walk, no second thread, no offline mode in the product, and no emulation of the launcher
   or IGC.

## Synthesis decision

Three structurally distinct candidates were produced in parallel and screened against the design red flags:

1. **Server-authoritative session core** (this design's base).
2. **Re-host the original process image**: a sparse 32-bit client address space with every global at its
   original address, all state in client-layout records, `MU_HANDLER(va)`/`MU_SERVICE(va)` bindings generated from
   the client's own tables, and MoveMainScene/RenderMainScene reconstructed so tick order becomes evidence.
3. **Trace contract**: one Session Capture Format unifying the packet corpus, Native Data and gate-3 ground truth,
   with live and replay sources behind a four-verb link and the blocked handshake isolated in one stub.

**Base: candidate 1.** Scored criterion by criterion (live path, state ownership, registration cost, incremental
migration, gate verification, plan honesty), it came out 29/30 against 27 and 13; an independent cross-judge
reached the same order and the same base. It wins on what the next contributor sees. An agent adding a packet
copies one ops row and one apply function that calls the unchanged verified handler. Views cannot include
session internals, and writes happen only in apply functions and under the lease. Its invariants hold without
private evidence. Candidate 2's are enforced mainly by a private Unicorn oracle, because any code may write any
address of its image. Candidate 1 also migrates one domain at a time, keeps `mu-world`/`mu-walk`/`verify-mu-native`
working and changes no `reconstructed/*` source.

**Grafted from candidate 2:**
- the client's routing generated from the binary into a checked-in `dispatch.def`, with ops rows that only bind,
  plus the derived coverage report, `ignore.def` and `--strict`;
- one layout manifest generating every field table and the `layout.json` shared with the readers and validators
  (it replaces the hand-written `CHAR_FIELDS`);
- the replay oracle (VERIFY-REPLAY-001): every inbound frame re-run through the original `0x01287ead`, seeded from
  the session's client-layout records. Candidate 1's choice to store the handlers' own record types makes that
  seeding nearly free;
- MoveMainScene/RenderMainScene as evidence that checks `parts.def` (WORLD-ORDER-001), as a check, not a
  prerequisite;
- three findings: the 0x12 viewport pieces are static readings that need a family before binding; the
  `MU_SCENE_NET_SEND` record stands for two sends; and the offset conflicts that LAYOUT-PROBE-001 settles.

**Grafted from candidate 3:**
- the journal as the one recording format, with WorldTime stamps, INPUT records and C3/C4 ciphertext beside
  plaintext;
- a client-build digest guard on every recording and Native Data artifact;
- one owner-run capture act that yields both a recording and that user's Native Data (CAPTURE-KIT-001).

**Rejected:**
- candidate 2's image as the runtime state model: unconstrained writes, VA-keyed services for every
  Move*/Render* routine, drawing inside `idle`, and a structural re-host instead of per-domain migration;
- candidate 3's socket-handoff shim and its capture and replay of the launcher "envelope". Both would move
  launcher- or IGC-attested material into another client, which is the boundary this project does not cross;
- candidate 3's redistribution of decrypted Native Data to other users, re-framing C3 as C1 in replay (it changes
  handler behaviour: `0x16` refuses plaintext), its native hero struct, its hand-written subsystem list and its
  F1/F4-only sub-dispatch.

**Fixed in the base during synthesis:**
- The base told the join from the keepalive by scene number. The tail send is emitted in every scene
  (`scene.c:125-127`), so the shell now uses the preceding call record.
- A generic window-event intent with a second routing table by window id became generated per-window intent kinds.

## Tradeoffs accepted

- We accept storing client-layout records (and a field table plus an audit for the motion/replicated split) in
  exchange for the verified handlers running unchanged and every domain being comparable with live memory.
- We accept a session that is large in total (all domains, some UI-handler state), in exchange for one writer per
  piece of state and three files per call chain. Each domain is its own file set, so no single file grows with it.
- We accept generated lists (domains, ops rows, windows, behaviours) and a small generator script, in exchange for
  parallel agents never editing a shared list and duplicates failing the build.
- We accept a generated file checked into the tree (`native/net/dispatch.def`) in exchange for routing that no
  author can mistype; a client re-pin regenerates it with `--update`, and the diff is the re-pin's review.
- We accept that recordings come from a Wine-side relay whose effect on the protected client is unknown until
  CAPTURE-KIT-001 runs; if it perturbs the client, plaintext comes from the post-decode buffer instead.
- We accept that `parts.def` stays hand-written with two order columns. They are client facts that should be
  reviewed together, and a test pins them.
- We accept changing MoveCharacters into a single loop over the unified table, where today the native code runs
  separate actor and player steps at different positions. This is a fidelity improvement that changes existing
  headless hashes once; the run that changes them is recorded.
- We accept a transitional period in which domains not yet migrated keep their demo feed. We do not accept a period
  in which any domain has two feeds.
- We accept `mu_session_seed.h` (test and tool builds only) as the way world tools start in a world, in exchange
  for `mu-world`/`mu-walk` staying usable before the account bodies are recovered. The symbol test keeps it out of
  the product.
- We accept that the fixed cross-connection pump order (connect, game, chat) may differ from the client's true
  arrival interleaving. The chat domain is disjoint from the others, so the difference cannot be seen in state; it is
  recorded as an assumption.
- We accept that live login can be blocked indefinitely by the operator contract. Everything up to that point
  (crypto, decode, dispatch, fixtures, replay, the app) is evidence-available and does not wait for it.

## Alternatives considered

- **Subsystem-owned state with a central handler registry.** Each subsystem registers its opcodes and keeps its
  own state, so only the dispatcher is shared. The public surface stays small, but four writers of Zen and
  per-visit lifetimes remain, and a "money changed" packet still has four places to land. It hides less: every
  subsystem must know framing, layout per head and the barrier, and has to sync mirrors with the others.
  Rejected on split ownership.
- **An event-sourced session (decode to typed events, native reducers).** It would give the cleanest public types,
  but the reducers would restate what the verified handlers already do, a second implementation of each family
  that Unicorn does not check. Rejected because it spends the project's main asset.
- **The world owns CHARACTER records, the session owns only "facts".** This keeps motion and replicated fields
  apart by type. But `mu_rp_move_packet`, `mu_rp_viewport_apply` and ChangeCharacterExt write both at receive time,
  so those opcodes would have to be dispatched into the world. That makes two dispatchers and two owners of
  equipment and hp. Rejected on split ownership and two ways to receive.
- **One client-address-space arena behind the API** (the shell's fake regions, generalized: every handler pokes a
  big emulated memory). It would be maximally faithful, but it leaks client offsets to every reader. Rejected for
  the public surface. It is kept internally only where verified code already demands bytes (CharacterAttribute, the
  stat machine, the hero record).
- **Launcher handoff over its IPC.** The native client would talk to localhost:55232 the way `main.exe` does. That
  is impersonating the launcher session from our side, so it is out of scope unless the operator publishes that
  interface for third-party clients. It stays a possible `mu_login_proof_source` behind an operator contract.

## Open questions and risks

- What must a login present beyond account and password? Is it launcher or IGC material, a client serial, or a
  version? Will the operator grant a native-client allowance, or provide a sanctioned token source
  (NET-CONTRACT-001)? Without one, does the owner accept that the native client stops at
  `MU_CLOSE_NEEDS_OPERATOR_CONTRACT`?
- Does IGC.dll add traffic after the handshake (heartbeats, integrity reports)? If the server disconnects clients
  that do not send them, only the operator can decide what a native client sends instead. Is the owner prepared to
  ask?
- Where exactly does the client drain its packet queue (the caller of `0x01221b94`)? Are the serials reset on the
  connect-to-game-server hop? Which CryptoModule channel and key does each connection use, and is any key sent by
  the server? These are evidence-available, but they decide whether recorded C3/C4 can be decrypted offline.
- May the owner's own original-client traffic be captured on the Wine side (a `ws2_32` relay outside `main.exe`
  and IGC) for replay and comparison? Its effect on the protected client is unknown. Who approves, and under which
  live-test rules (rate, accounts, no automation that breaks service rules)?
- Native Data for other users: will the operator supply plaintext objects and Lang tables? If not, is a guided
  Wine-track acquisition with each user's own account acceptable as the product path?
- Version drift: if the live service moves past the pinned `main.exe`, does the project re-pin (rerun families,
  re-acquire Native Data, re-diff the jump table), or does it freeze on this build?
- The F6 `0x70/0x71` extra XOR needs 3 bytes at `0x06fca280` (third section, never captured). Is a scoped capture
  approved?
- Is "no offline mode in the product" the owner's intent, or should the signed app keep a labelled fixture mode
  for demonstrations?

## Next implementation step

Build the vertical slice that needs no unrecovered body. Add `native/session` (`mu_session.h`, `session.c`,
`dispatch.c`, `gen_domains.py`), the loopback `native/fixture` with the progress behaviour, and the hero domain.
Then switch `mu-walk --progress` from the demo queue to real C1 frames: `0x16` as plaintext C1 must produce the
client's own `C1 4D 02 00 16` report, and `A0 06/11` must update `mu_hero_stats`. Rerun the existing progress
families unchanged, and require the progress renders and hashes to be identical.
