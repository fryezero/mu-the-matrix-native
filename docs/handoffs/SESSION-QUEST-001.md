# SESSION-QUEST-001 handoff

Branch `codex/session-quest-001`, isolated worktree created from `707b82c`. No original client or live service used.

## Implementation

- `session/domains/quest*` owns the entire reconstructed `mu_quest_client`, its tables, guide, classic,
  tracker, windows, throttles and maps. `ops/quest.ops` binds 19 quest routes. Verified reconstructed
  code is unchanged. Static route addresses were added to the seed table, pending NET-DISPATCH.
- `QUEST_WINDOW` handles window actions and callbacks; `QUEST_CONTEXT` supplies the context still owned
  by unmigrated hero/map/inventory views. Quest replicated state has one feed, dispatched inbound frames.
- The log sink preserves Send's encryption argument, sends requests through the existing packet builder
  and journals them. Other effect lines become ordered, chunked window cues, preserving long JSON.
  The GFx window consumes them and submits intents. Host font/name/path services bind without resetting state.
- All demo rules, queues, offers, rewards and kill accounting moved out of core into `fixture/behaviors/quest.c`.
  Its independent server model never writes the session's client. The old core API is a dev-tool facade.
  World tools link a fixture variant without TCP serving, preserving the offline app's no-network imports.
  The fixture RNG symbol was renamed because its previous name collided with the effects RNG when linked.
- `world/parts/gfx.c` keeps tick 40 and runs quests in headless `mu-walk` too. With `MU_LANG_DIR`, it loads
  static quest data; `MU_QUEST_SCENARIO` selects a fixture script. Without it, the legacy demo text supplies
  guide/classic login replies. Headless reporting gained a quest summary at report position 150.
- Two discovered quest scenarios, with authored synthetic tables, cover all 17 decodable routes and state
  updates while the world is detached. `quest-data` resolves scenario-relative paths, then working-directory
  paths for suite overlays. F6 70/71 tests live separately because they must report undecodable frames.

## Checks

- Unchanged manifest-driven Unicorn suites: NATIVE-QUEST-001 **8,203** comparisons, **6/6** mutants;
  NATIVE-QUEST-002 **7,004**, **5/5**; POLISH quest answers/constructor **2,001**, **2/2**.
  Total **17,208 comparisons, zero mismatches, 13/13 planted mistakes caught**.
- Native quest tests cover frame-driven accept/progress/complete/give-up, opaque list refusal, guide/classic
  states, delayed resume after map load, failed-load cancellation, and character-select persistence.
  The persistence test explicitly models the account phase transition, detaches the world, applies progress,
  rebinds host services and returns to world on the same session. The account wire flow is not claimed.
- Headless `mu-walk` runs the quest fixture and retains quest 7 at state 2/count 3. Separate journal tests
  retain both opaque frame bodies, report `body_undecoded`, and count exactly two undecodable frames.
- Four discovered scenarios total **37 inbound frames**, **zero unbound/undecodable**, with all eight hero
  and 17 decodable quest routes. Three unsent encrypted requests and two unrecovered master-point intents
  remain explicit. The new quest progress scenario has one unsent complete request.
- Release gate at `6bde129`, integrated through main `fecdddd`: **1,354 tests, 157 explicit skips,
  zero failures**; viewer and read-only reader builds pass. Audit: **1,186 files, zero rejected**.
  The final gate is `gate-release.log`; its four-scenario proof is copied to `release-suite/` in scratch.
  The suite's dirty flag comes from the two untracked local input symlinks; tracked source was clean.
- A 559-byte window cue was reassembled byte-for-byte against the reconstructed log; nonfinite window
  input was refused. Product archive inspection found no quest seed or fixture definitions.
- Self-review covered standards and milestone behavior; no independent review is claimed. GFx code builds
  in the local app gate, but a private Ruffle quest-movie recipe was not rerun. Synthetic software renders
  were inspected; the existing render/hash assertions pass. Late static-table binding preserves the seeded
  class and level, and the isolated layout test now stubs the generated domain list.

## Changes and limits

F6 70/71 are retained in the journal as `body_undecoded`, without applying their decoded handlers. The
three bytes at `0x06fca280` were not read or recovered. The previous demo's bypass of that layer is removed,
so NPC quest-list browsing is intentionally unavailable until those bytes are captured in a separate task.

Encrypted quest requests remain journaled as unsent until NET-DECODE supplies the wrap. Fixtures explicitly
supply replies for those paths; this is not an encrypted request round-trip claim. No crypto, live service,
real reward insertion or new original-instruction behavior was implemented. Account/session ownership in
`mu-client` is still SESSION-ACCOUNT: this milestone proves state retention on an existing session, not
persistence across a destroyed login, process restart or a different selected character.

Existing render/hash tests are retained. Quest data has no new draw pass. Intended differences are the new
headless quest summary, frame/cue journaling, opaque NPC lists and crypto-dependent requests staying unsent.
The historical NPC-list demo screenshots are no longer an end-to-end acceptance claim. POLISH's unrelated
joint renderer is unchanged; its existing tests stay in the gate.

## Evidence

Reports and scratch are retained outside the worktree under
`~/Documents/MTM/mu-mac-tools/native/scratch/session-quest-001/`, including `unicorn/`, fixture suites and gates.
The integrated layout audit uses scalar-only quest zones, excluding host pointers from journals; repeated
quest fixture journals are byte-identical. Its zone capacity includes the pinned 484 quest records.
Renders are under `~/Documents/MTM/mu-mac-tools/native/renders/session-quest-001/`.
Only authored source and synthetic tables/scenarios are committed.

Operational note: a process-selection error stopped the gate in the separate `session-viewport-001` lane.
No source files were edited there; that lane's interrupted gate needs rerunning by its owner.
