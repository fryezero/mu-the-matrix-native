# Module map: the native client over a server-authoritative session

Paths are relative to the repository root. "Owns" means "the only code that writes it".
"May call" lists who is allowed to include the module's headers; an include audit
(`scripts/audit_includes.py`, run by `make test`) turns every other include into a failure.

## The shape in one picture

```
             bytes                    frames                       state + cues              pixels / sound
 socket ──► native/net ──► native/session (dispatch ─► domains ─► reconstructed handlers) ──► views
 (or fixture loopback,        ▲                                 │                        native/world parts
  or replay)                  │ request bytes                   │ revisions, cues        native/gfx windows
                              └──────── domains ◄── mu_session_submit(intent) ◄───────────  native/client shell
```

One writer per piece of replicated state (the session); one entry for inbound bytes
(`mu_session_pump`); one entry for outbound requests (`mu_session_submit`); one routing
table (`native/net/dispatch.def`, generated from the client's own jump table and verified under
Unicorn; `ops/<domain>.ops` rows only bind apply functions to its routes); one layout manifest
(`native/session/layout/*.def`) for every client record field the native code, the readers and the
validators touch.

## New modules

| Directory | Owns | Public header(s) | May call / include it |
|---|---|---|---|
| `native/net/` | sockets/links, the endpoint allowlist, the receive dechunk buffers, the two packet serials, the CryptoModule contexts (`g_enc`/`g_dec`), and the client's routing as data (`dispatch.def`, generated; `ignore.def`) | `mu_transport.h` (front ends: create, poll, flush, free) | `mu_transport.h`: front ends (`native/client`, tools). `mu_link.h`, `mu_conn.h`, `mu_crypto.h`: only `native/net`, `native/session`, `native/fixture` |
| `native/session/` | **all replicated game state**: phase, account and character list, hero records (CharacterAttribute, the stat machine, the hero CHARACTER's replicated part), money, inventory/equipment/warehouse, skills (book, stamps, keys, master, tree 4), quests (the whole `mu_quest_client`), map/place, the CharactersClient table (players, monsters, NPCs), the Items[] pool, party, trade, friends, messenger and mail, NPC talk/shop/vault state; the cue ring; revisions; the world-change barrier; the journal | `mu_session.h`, `mu_intent.h`, `mu_cue.h`, `mu_journal.h`, `domains/<d>.h` (through generated `session_domains.h`) | any view or front end: `native/client`, `native/world`, `native/gfx`, `native/charsel`, `native/login`, tools. `session_internal.h`, `domains/<d>_state.h`, `domains/<d>.c`, `ops/`: only `native/session` |
| `native/fixture/` | the fake service: its endpoints, the server side of each connection (with the mirror CryptoModule), behaviours (the former demo servers) and their simulated world | `mu_fixture.h`, `behavior.h` | tests, `native/tools`, `mu-world`/`mu-walk`, and dev builds of `mu-client`/`mu-shell`. **Never** the product `mu-client` (symbol test) |
| `native/world/` (rebuilt) | the loaded world: terrain, objects, environment, particles, effects, GL handles, the hero's **motion** (`mu_walk`), per-view caches, the GFx layer instance | `mu_world_rt.h`, `mu_input.h` | `native/client` (scene 6), `world/world_tool.c` (mu-world, mu-walk front ends) |
| `native/world/parts/` | each part's presentation state only | `world_part.h` (ops struct), `parts.def` (the one list) | only `native/world` |
| `native/gfx/windows/` | each window's view state (open, scroll, drag) | `mu_window_view.h` | only `native/gfx` and the world's gfx part |

## Changed modules

| Module | Change |
|---|---|
| `native/core/mu_protocol.{c,h}` | Unchanged code; added to `CORE_SRC` (`native/Makefile:46-58`) so game binaries link it. Rerun `verify-protocol-cbmc`. |
| `native/client/shell.c`, `main.c` | `host_call`'s network-shaped cases answer from the session (`client/shell_session.c` in this sketch); `g.protocol` derived each frame; loop order: transport poll, SDL input, `mu_shell_frame` (session pump at the client's queue-drain point), compose, transport flush. `world_gfx` no longer opened here. |
| `native/client/offline-session.*`, `demo-*.txt` | Moved to `native/fixture/behaviors/account.c` and `native/fixture/scenarios/`. |
| `native/world/main.c` (3,622 lines), `world_embed.*` | Split into `native/world/world_rt.c` + `parts/*.c` + `input.c` + `world_tool.c` (the mu-world/mu-walk CLI and their `--*-script` drivers, which now drive fixture scenarios and input scripts). `world_embed.*` and the `#define main` embed are deleted. |
| `native/charsel/charsel_embed.c` | Same treatment, smaller: a `mu_charsel_rt` module reading `mu_session_characters`; create/delete through intents. |
| `native/core/mu_combat`, `mu_npc`, `mu_progress`, `mu_map`, `mu_quest`, `mu_social*`, `mu_items`, `mu_world_players`, `mu_world_actors`, `mu_skill_demo`, `mu_skill_tree4`, `mu_mix` | Each loses its demo-server half (to `native/fixture/behaviors/`) and its replicated state (to a session domain). What stays is presentation and the verified client-side rules (attack actions, damage text layout, labels, name plates). |
| `native/gfx/mu_gfx_layer.c` | Keeps movie mechanics; loses `item items[48]`, `mu_gfx_hero` demo values, its Zen; per-window wiring moves into `windows/*.c`; `FILES[]` generated. |
| `native/app/` | `mu-nonet` leaves the product (kept as a test tool for fixture runs if wanted); `LaunchPlan` without feature flags or `DYLD_INSERT_LIBRARIES`; endpoint from configuration; Keychain-backed "remember account"; Developer ID signing. |
| `native/core/mu_lang.c`, `mu_world_helpers.c` (`imps[]`), `mu_world_pets.c` (`step_context current`), skill demo tables, `mu_perf` | Process globals become session or runtime fields so relog / server change without a restart is safe. |

## Reconstructed boundaries that change (exactly)

**None of the `reconstructed/*` sources change.** Every boundary the session needs already exists as an argument,
an env/host callback or a recorded call list, so the verified families keep running unchanged:

1. `reconstructed/quest`: `mu_quest_send` (`quest_ui.c:963-971`) and the window invokes write formatted lines into
   `mu_quest_log`, whose existing `sink` callback (`quest.h:234-237`) delivers each line as it is logged. The
   session's quest adapter parses `send ...`, `invoke ...`, `notice ...`, `msgbox ...` lines into requests and cues.
   The quest host's `path_reset`/`path_start`/`send_move` (`quest.h:258-263`) go to the world port and the map
   domain's WALK intent.

What changes is the native caller side: the inputs these entry points get (session records instead of per-visit demo
copies) and where their outputs go (cues and the transport instead of demo servers and logs). The project's main
asset, the families' equality with the client's instructions, is untouched; each migration milestone reruns its
families to show that.

Everything else is adapted from the outside:

- `reconstructed/progress` `mu_prg_env.emit` (one line per call) is already a sink: parsed into cues by the hero
  domain.
- `reconstructed/players` `mu_rp_env` services are filled from the world port; `mu_rp_calls` become cues.
- `reconstructed/npc` `mu_talk_output` call lists become `MU_CUE_WINDOW` cues through `mu_npc_talk_window`.
- `reconstructed/social` `mu_social_packet {channel, send0, send1, data}` is wrapped into `mu_packet` by the
  social domain (`channel`/`send0`/`send1` decide C1/C3 and the connection).
- `reconstructed/scene` keeps `MU_SCENE_NET_SEND` as one record id for two sends; the shell tells the join
  (after `0x009a13f4`) from the tail (after `0x00ac9be9`) by the preceding call record and answers with intents.
- `reconstructed/items` `mu_gi_viewport_parse` gets its first caller (ground domain); `mu_gi_host` from the port.

## State ownership, field by field where it is not obvious

| State | Owner | Writers (when) | Readers |
|---|---|---|---|
| Hero stats, level, exp, points (CharacterAttribute bytes) | session `hero` | apply (pump) | HUD/character window, skills usability, quest mirrors (refreshed per call) |
| Money (CharacterMachine +0x2d70) | session `hero.money` | apply | shop, mix, trade, warp cost check, quest reward text — one field instead of four |
| Hero class | session `hero.attr[+0x187]` / `hero.record[+0x12]` (two client fields, both written by the client's own handlers) | apply | shell (loading), skills, quests, progress — instead of three sources |
| Hero motion (tile, position, angle, action, path) | world `mu_walk` | world tick; server placements through `port.place_hero` (world code) | session handlers via `port.hero_motion` |
| Other characters (CharactersClient) | session `viewport` | apply: create/delete/equipment/hp/path; world tick through the `mu_sim` lease: motion only (audited) | actors/players/names/helpers parts, picking, combat targeting |
| Ground items (Items[]) | session `ground` | apply: create/remove; tick lease: sparkle/animation | items part (labels, render), pick-up input |
| Quest client incl. its window-handler state | session `quests` | apply; the quest windows' generated `MU_INTENT_WINDOW_QUEST_*` kinds; `mu_session_step(QUESTS)` at the quest-step tick position | quest GFx views |
| Which world is loaded | world runtime | travel, derived from `mu_session_place().world` | world parts |
| Window open/closed, drag, scroll | each window view | input/callbacks | that view |
| Protocol state `0x06fca2c4` | derived from session phase | nobody (copied into `g.protocol` each frame) | the verified scene manager |

## Generated lists (no hand-synced lists)

| Generated file | From | Fails the build when |
|---|---|---|
| `build/gen/session_domains.h`, `domains_all.def`, `session_domains_state.h` | `native/session/domains/*_state.h` + `*.h` | a domain has state but no ops file or vice versa |
| `native/net/dispatch.def` (checked in) | `scripts/gen_dispatch.py` over the restored text | `validate_dispatch.py` finds a route that differs from the original's routing under Unicorn |
| `build/gen/ops_all.def`, `bound_routes.def` | `native/session/ops/*.ops` joined with `dispatch.def` and `ignore.def` | an `MU_OP` names no route, two rows bind one route (duplicate `case`), an `MU_OP` and an `MU_IGNORE` share a route, two domains route one intent kind (initializer override), an intent kind has no route (unit test) |
| `build/gen/layout_<record>.h`, `layout.json` | `native/session/layout/*.def` | two files declare overlapping byte ranges of one record with different types or zones |
| `build/gen/windows.def`, `FILES[]`, slot enum, `MU_INTENT_WINDOW_<MOVIE>` kinds | `native/gfx/windows/*.c` meta lines | two files claim one movie |
| fixture behaviour list | `native/fixture/behaviors/*.c` | two behaviours share a name |

`native/world/parts.def` is hand-written on purpose: it is one list with two order columns that are client facts
(tick order, draw order), reviewed together. Its test pins both orders, first against today's `on_step` and draw
functions, then (WORLD-ORDER-001) against the call order of the reconstructed MoveMainScene/RenderMainScene.

## Call chains (each traceable in three files or fewer beyond generic plumbing)

- **Server says "level up":** `native/net/dispatch.def` route (A0 06 → `0x01250b05`) ← `ops/hero.ops` row → `domains/hero.c` `hero_levelup` →
  `reconstructed/progress` `mu_prg_recv_levelup`. The HUD: `native/gfx/windows/main.c` sync on `MU_DOMAIN_HERO`.
- **Player presses 1:** `native/world/input.c` → skills part `input` → `domains/skills.c` submit (builder) →
  `mu_session_send`.
- **Teleport to another map:** `domains/map.c` `map_teleport` returns `MU_APPLY_WORLD_CHANGE` (barrier) →
  `native/world/world_rt.c` sees `place.world` ≠ loaded world, travels, `mu_session_attach_world` (held frames apply).
