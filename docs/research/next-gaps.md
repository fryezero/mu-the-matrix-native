# Remaining offline native-client gaps, NEXT-GAPS-002

Evidence snapshot: main `c5b9d5ca9fbdfb53c40a3f571006af38d6f1cb1f` (PR #400, steward batch 118),
2026-11-15, plus the pushed branches of the lanes running that day at the commits named in the
source ledger. This replaces the NEXT-GAPS-001 snapshot of main `ff8e0543` (2026-11-09); what that
snapshot ranked is listed under [Superseded](#superseded-next-gaps-001-snapshot).

This is a dispatch list, not a completion percentage. Sizes and ranking are planning estimates.
The owner permits offline/static reconstruction and authored appearance fixtures. Owner direction of
2026-11-14: work on the port itself; no work on the installed Native Preview app, no Native Data
refresh, no README work. Network, account, server-state acquisition, character-power work and opaque
protection boundaries are excluded and are not ranked.

Counts come from text, CSV and JSON only: handoffs, research notes, census files and status lines.
No model extraction, render, benchmark, validator or original client ran. A count on a pushed branch
is marked **branch**; it is the lane's own claim until the merge steward merges it. Every count cites
its owning source and line range in the [source ledger](#source-ledger).

## Dispatch decision

Five families hold almost all the remaining visible work, in this order:

1. **Missing consumers.** Producers in three lane families (worlds, items, Muun) and the skill lanes
   already request 39 particle, joint, effect and sprite ids that no native consumer draws. Each is a
   counted refusal today. This is the only gap that several lanes share, so it ranks first.
2. **Actor caller services.** 109 of the 217 incomplete actor selectors (branch) stop on one of three
   uniform caller reasons.
3. **Skills outside the learned demo set.** 37 class-tree skills and 86 aliases have no cast admission.
4. **The hero's own draw.** Head slot, castle-world weapon override and scale writes are still not
   reproduced, and the hero is in every frame.
5. **Item bodies.** 92 of the 144 remaining bodies (branch) fall into three groups with one reader each.

UI windows, Muun visuals, the learned-skill leftovers and several single actor cases are at
diminishing returns and are listed so that they are not started.

S means a narrow caller or adapter, M one behaviour with reconstruction and native integration, and
L several behaviours or an unresolved selection. These are relative sizes, not measured durations.

## Counts with their denominators

| Area | Main `c5b9d5ca` | Pushed branch | Meaning and limit | Source |
|---|---|---|---|---|
| Item bodies | 1,480 / 1,674; 194 left (26 helper-count, 168 others) | 1,530 / 1,674; 144 left | Bounded RenderObjDraw bodies, not item effects or poses. Skins 17 / 17; links 18 targets / 24 types | N01 L17-21; N02 L16-19 |
| Item body shapes | 649 / 798 complete | 689 / 798 | Classifier shapes of the 1,691-type survey (1,674 bodies + 17 skins) | N01 L36-39; N02 L78-82 |
| Item-program particle census | 110 programs / 37 pairs, all supported | 5 new producers request 11 pairs: 3 supported, 8 missing | The frozen census does not include producers admitted after it | N03 L24-27; N02 L84-94 |
| Hero draw | Head slot computed, slot 0 not drawn; `0x009dadf1`, `0x0137ad93` and the rest of `0x01394f6f` not reproduced | Same; loader still starts at slot one | No row count exists. The seventeen-helm class-head mapping is the only enumerated set | S26 L134-136; N04 L3627-3640 |
| Wings and cloaks | Wing/armour cloth, NPC cloth and the fourth saved point of the two frozen wing programs delivered | n/a | Class 937 virtual-manager lifecycle and trailing effects not executed; guild/duel/buff gate inputs at rest | S30 L126-141; N05 L15-17 |
| Actors (fixture selector contexts) | 589 checked / 355 incomplete / 80 refused of 1,024 | 727 / 217 / 80 | Selectors include aliases and repeated defaults; not unique creatures. An opener alone never admits an actor | N06 L14-16, L125; N07 L12-15 |
| Learned-skill table | 11 P / 7 L / 11 M of 29 rows | 14 P / 6 L / 9 M | 14 DK + 14 Elf learned entries + ordinary attack. P bounded primary visual, L visible subset, M missing | N08 L19; N09 L17 |
| Skills outside the learned set | 14 DK + 23 Elf catalogue rows, all M; 46 DK + 40 Elf aliases, all M except 416/424 | 416/52 and 424/51 move L to P | Catalogue is 26 + 1 DK and 36 + 1 Elf entries by the stamp manager's filters | N10 L152-158, L171-207, L209-214 |
| Historical primary skill routes | 20 P / 3 L of 23 | n/a | Older denominator, kept separate | S20 L59-70; N10 L276-278 |
| World/skill consumer census | 25 pairs: 22 admitted / 3 refused | 12 further pairs admitted | Selected pairs only; neither denominator covers the original switch | N03 L26-27; N09 L74 |
| World methods | 144 / 144 primary methods across 48 classes | n/a | Reviewed bounded method annotations, not map fidelity | S15 L64-66 |
| Inline world type switches | All ten Kalima and fourteen tower types; 30, 41/42, 33, 38, 31, 9, 51, 56, 37/40, 11..17 delivered earlier | Census of every world's inner routine in progress, not published | 46/98 refused: 57 world-list additions and 48 registrations traced, no handler object | N11 L9-25, L116-125; N32; N12 L22-24 |
| Object picking | Action handlers 4/6 without OBB or MouseTarget input | Box write, segment test and pick: 3,000 cases, 23/23 mutants | No current live action row uses them | S31 L65-67; N12 L10-13 |
| Water | Kalima water wrapper runs with an absent manager (getter returns zero) | n/a | Manager simulation unreconstructed | N11 L11-13, L118-120 |
| Terrain | Remaining terrain rendering delivered | n/a | Only the authoritative Chaos stage, world `0x49` camera interpolation and cross-system random order remain | N13 L42-51 |
| UI windows | 28 bound of 134 movies; 13 provider-complete, 33 provider-missing, 30 state-dependent, 43 no route, 15 previously bound | MapName banner in progress; the 33 split 17 / 1 / 8 / 2 / 3 / 1 / 1 | Bound means a proved route and an empty authored provider, not complete controller behaviour | N14 L31, L264-270; C02; N15 L13-36 |
| HUD | HUD and sixteen task panels fit 640x480 | n/a | Not every NPC, trade, social or tooltip state is covered | N16 L3, L289-297 |
| Audio census | 1,434 classified / 546 unresolved of 1,980; 411 play boundaries | 1,464 / 516; 593 play boundaries; class sites 427 of 524 | 1,980 is a syntactic call-target scan, not a control-flow graph. Classified is not wired | N17 L22-31; N18 L25-39 |
| Audio refused groups | n/a | 97 class candidates in eight whole owners; 66 class-use sites | Whole-owner blockers: delegated 47, marker/service 47, prior action/stop 3 | N18 L44-54; N19 L1108-1113 |
| Muun | Eight kind-1 riders, 25 / 30 special mesh rows | 386-row census (378 kind 0, 8 kind 1); 379 base models load; 29 / 30 special branches | Adapter census, not 386 pixel proofs. Nine mesh rows and six assets unavailable | N20 L11-13, L30; N21 L9-27, L242-251 |
| Pets and mounts | 24 mount functor bodies recorded; class visuals for Shining Tail and Ghost Horse | n/a | Six later mounts, the buff draw path `0x017f746f` and alternate-grid rings not drawn | N22 L27-32, L58-60, L173-178 |
| Dark Raven | Reconstructed earlier (limits only cited here) | n/a | Later raven items `0x28f8..0x2900` not read; AI 2/4/5 are server commands | N23 L156-160 |
| Character selection | Authored equipment levels shown | n/a | +15 class attachments `0x016d53a4`, cloth setup and class replacement meshes not added | N24 L168-171; N25 L776-786 |
| Login scene | Terrain, objects, after-character glows, sprites and particles | n/a | The unnamed passes are not drawn; the login world creates none of them in the reconstructed code | N26 L24-26; N27 L82-84, L214-222 |
| Movement, camera, input | Coverage table delivered | n/a | IME candidate movie, full context guards and live cross-track timing open | S13 L51-106; N28 L101-106 |
| Performance | Only crowd40 passes the strict 25 Hz all-scene acceptance | n/a | Measured 2026-10-28 on a shared host; nothing measured since | S23 L13-15 |

## Missing consumers and missing assets

### Consumers refused for want of a native routine

Each id is requested by a producer that is merged or PR-ready and is counted as a refusal. "Lanes"
names the lane family that reported it. No single id is reported by two families; the shared need is
the consumer module itself, which all four families depend on.

| Kind | Id / subtype | Requested by | Lanes | Source |
|---|---|---|---|---|
| Particle | `0x7f5a/43`, `0x7f5a/47`, `0x7f54/1` | Kalima types 15/29/32 and tower type 0 producers | Worlds | N11 L121 |
| Joint | `0x7f7c/8` | Kanturu 37/40 inline hook | Worlds | N29 L180 |
| Joint | `0x7fd5/4`, `0x7f7d/11`, `0x7f7c/19` | Crywolf, Barracks/Refuge, Kalima and tower leaves | Worlds | N30 L147 |
| Effect | `0x4be/0`, `0x4bf/0`, `0x419/2`, `0x41a/2`, `0x4c0/0`, `0x4c1/0`, `0x4c2/0`, `0x4c5/0x4c0`, `0x4c5/0x4c1`, `0x4c5/0x4c2` | Kalima and tower producers | Worlds | N11 L122-123 |
| Particle | `0x855d/2`, `0x7fe0/0xa` | Item producer `0x0f22` | Items (branch) | N02 L91 |
| Particle | `0x8616/0` | Item producer `0x0f23` | Items (branch) | N02 L92 |
| Particle | `0x84d1/2`, `0x850b/5` | Item producer `0x0f25` | Items (branch) | N02 L93 |
| Particle | `0x8080/0xe`, `0x807e/0xe`, `0x807f/0xe` | Item producers `0x24be/0x24bf` | Items (branch) | N02 L94 |
| Particle | `0x8081/1`, `0x8082/1`, `0x7ef7/19` | Muun kind-1 secondary bodies | Muun (branch) | N21 L249 |
| Particle | `0x8084/28` | Muun appearance 375, bones 11/18 | Muun (branch) | N21 L20, L249-250 |
| Particle | `0x7efa/3` | Muun appearance 377, bone 52 | Muun (branch) | N21 L22, L250 |
| Sprite bitmap | `0x810d` (no world binding), `0x8003` | Muun appearances 376 and 377 | Muun (branch) | N21 L21-22, L250 |
| Effect | `0x585/0`, `0x586/0`, `0x4b7/1` | Blood Storm parent `0x583/0` and body `0x584/0` | Skills (branch) | N09 L533-534 |
| Particle | `0x8145/1` | Blood Storm body `0x584/0` | Skills (branch) | N09 L533-534 |
| Blur | `0x814b` | Blood Storm body, 55 blur calls | Skills (branch) | N09 L533-534 |
| Effect | `0x49e/0` | Crescent Moon Slash end | Skills | N08 L34; N09 L535 |
| Effect | `0x8001/0` | Fire Breath primary | Skills | N08 L38; N09 L535 |

Totals: 17 particle pairs, 4 joints, 15 effects, 2 sprite bindings and 1 blur, 39 ids. Lane 1 takes the
22 particle, joint and sprite ids of worlds, items and Muun; lane 7 takes the 17 effect-side ids.
The Blood Storm scene alone records 1,883 downstream refusals (N09 L200-203 of the research note).

Refusals that are not missing consumers and must stay: missing or dummy bones, null or out-of-range
map owners, absent keyed-effect hooks and unwritten stack inputs (Elbeland `0x3a` colour).

Older leads that are not confirmed today: the pet list in N31 L155-159 and the Dark Raven list in
N23 L158-159 predate the particle module's pet kinds. Audit current support before counting them.

Actor-side requests are not in this table. ACTORS-007 records the reason "additional caller services:
effect" for 66 selectors without publishing their ids; lane 2 publishes them.

### Assets absent from the frozen Native Data (owner-paused)

Refreshing Native Data is app work that the owner has paused. These rows stay refused with frozen
input and are not ranked.

| Asset | Wanted by | Source |
|---|---|---|
| `DarkLordSkill.bmd` | Transition effect `0x47a/0,1` (effects and Muun remote transition) | N03 L125; N09 L548-549; N21 L35 |
| `Flame01.OZJ`, `water.OZJ` | EFFECTS-031 consumers | N03 L125; N09 L548-549 |

### Assets absent from the read-only game data or lacking a binding

No lane can supply these; they are permanent refusals unless new data appears.

| Asset or row | Detail | Source |
|---|---|---|
| Six Muun models | `shogunpet`, `ninjapet`, `samouraipet` and their `_evol` files under `Data/Item` | N21 L248-249 |
| Muun appearance 193 | No item-model path binding | N21 L249 |
| Nine Muun mesh rows | Meshes the models do not contain: 276, 292, 305 (two), 306 (two), 357, 368, 369 | N21 L242-244 |
| Muun code 363 | Model has actions 0..2 only; 3/4 refused | N21 L245 |
| Actor classes 546, 918 | Seven and two mesh textures missing | N07 L326-327 |
| Actor class 617 | Exact startup file unresolved | N07 L339-340 |

## Remaining gap inventory by area

"Yes, fixture" permits only synthetic/offline presentation. "No" rows are recorded to prevent
accidental dispatch.

| Area | Missing behaviour or evidence | Evidence | Size | In scope |
|---|---|---|---|---|
| Items | 144 bodies (branch): producer/service 50, scalar/colour 24, variable draw count 18, helper caller 17, fixture stop 12, matrix stack 10, independent failure 10, entry state 3 | N02 L53-63 | L | Yes; lane 6 takes the first three groups |
| Item effects | Eight particle pairs of five new producers | N02 L84-94 | M | Yes; lane 1 |
| Hero | Slot-0 head, world weapon override, scale writes | S26 L134-136; N04 L3627-3640 | M | Yes, appearance only; omit `0x00a00fb7` |
| Actors | 217 incomplete (branch) in 28 named groups | N07 L29-41; C03 | L | Yes; lanes 2 and 11 |
| Actors | 80 loader refusals; four named boundaries 374/642, 378, 617 | N07 L337-340 | Unknown | Single cases; not ranked |
| Skills | Catalogue rows and aliases outside the learned set | N10 L152-214 | L | Yes, fixture learned set; no power or eligibility |
| Skills | Death Stab and both auras: general equipment-link selector | N09 L537-538 | M | Yes; lane 3 |
| Skills | Defense held input, seven summons, Fire Breath mount body, stale 47 | N09 L535-545 | n/a | Diminishing or server-driven |
| Worlds | Census rows not yet published | N11 L125; N12 L22-24 | Unknown | Yes; lane 5 after the census |
| Worlds | 46/98 handler context | N11 L23-25, L116-117 | Unknown | Not without a statically identified handler |
| Worlds | Kalima water manager | N11 L118-120 | M research | Yes, static; lane 13 |
| Worlds | Placements of 121/145/95/110 | S19 | Unknown | No, parked protection boundary |
| Worlds | Event-dependent scenery (Raklion, Ferea door, tower sequence, Arca/Imperial, Uruk weather) | N11 L18-21; S36 | L | No server-state acquisition; authored inputs only |
| UI | 17 rows that open only from a server response | N15 L15-18 | n/a | No |
| UI | Eight item-record popups, two unbound parents | N15 L26-31 | M | Conditional; lane 10 |
| UI | 30 state-dependent, 43 no-route rows; Help opener, Home, fifth-tree and event inventory | N14 L264-270; C02 | n/a | Refused without new evidence |
| Audio | 516 owner-unknown candidates in 359 prologue groups (branch) | N18 L25-33; N19 L1029 | L | Yes, classification first; lane 9 |
| Audio | 97 class candidates in eight whole owners | N19 L1108-1113 | M | Yes, static |
| Audio | 66 class-use sites; Guardian handler-state sites | N18 L51, L98-100 | n/a | No: target/buff/request owner absent |
| Audio | Virtualised `0x01854279..0x018542c2` | S42 L82-84 | Unknown | No, opaque boundary |
| Muun | Consumers above; nothing else actionable | N21 L242-256 | n/a | Lane 1 only |
| Mounts | Six later mounts' class visuals, buff draw path, alternate-grid rings | N22 L173-178 | M | Yes; lane 8 |
| Character selection | +15 attachments, cloth setup | N24 L168-171 | M | Yes, fixture records; lane 12 |
| Login scene | Unnamed passes; credit-window branch | N27 L214-222 | S | No evidenced visible gain |
| Input | IME movie, context guards, legacy NewUI open state to GetScreenWidth | N28 L101-106; S34 L86-92 | M | Optional; not ranked |
| Performance | Crowd80, Tormenta and Retina pacing | S23 L13-15 | L | Yes; quiet machine only, lane 14 |
| Packaging, Native Data | Installed Preview at `d4af71dd`; frozen data | S19 | n/a | Owner-paused |
| Network, session, power | Login, sends/decodes, inventory insertion, stat formulas | S39 L455-474 | n/a | No |

## Ranked lanes

All briefs inherit the owner brief, the stop time, the no-subagent rule and the resource guard.
Lane names are proposals; the orchestrator assigns ids. Each lane first rereads the current owning
handoff, because several bases below are PR-ready branches that may have merged.

Method common to all implementation lanes (the throughput method): classify the whole remainder by
exactly what is missing and publish the group sizes first; admit each uniform group with one
table-driven, instruction-checked verifier (per-row original comparison, compiled mutants on the
verifier, proof renders for representatives and for any row that differs); hand-trace single cases
only after the uniform groups; rows that fail the uniform check stay refused with the reason recorded.

Checks common to runtime lanes: root build with `nice -n 10 make -j4`; post-build affected selection;
affected portable suites and private validators with `--jobs 2 --no-mutants --cache`; changed-target
mutants once; the 6b shared-symbol review; the 8d 40-item cap ("8d reduced"); affected-world proofs
and one default identity sweep with a rebuilt `mu-world` and both SHA-256s recorded; skip the
app-packaging test module. No full lane gate.

### 1. RENDER-EFFECTS-034, consumers for worlds, items and Muun, M/L

- Scope: the 22 particle, joint and sprite ids of the consumer table (worlds 3 particles + 4 joints,
  items 8 particles, Muun 5 particles + 2 sprite bindings). No producer changes.
- Start: `reconstructed/particles/` (`particles.c`, the `*_kinds.inc` files), `reconstructed/joints/`
  (`joints.c`, `world_inner_joints.inc`), `native/core/mu_particles.c`, `mu_joints.c`,
  `mu_item_bitmaps.inc`. Original entries: CreateParticle `0x0168fafd` / `0x015ae7b0`, MoveParticles
  `0x01616c80`, RenderParticles `0x0159123f`, CreateSprite `0x01692eb7`, CreateJoint `0x0153b02c`,
  MoveJoint `0x01556c26`, RenderJoints `0x01589b56`. Per-id case addresses come from each producer's
  handoff (N02, N11, N21, N29, N30).
- Dependency and conflict: starts from EFFECTS-033 (PR #403), which owns the same files. Only one
  consumer lane at a time. Bitmap and model registration indices are shared: append, keep leading
  indices stable, and state the count change (EFFECTS-031 moved 97 to 99, 033 moved 99 to 100).
- Method: EFFECTS-031's grouped verifier (22 pairs in one lane): per-pair create, move and complete
  draw-stream comparison, ordered RNG, compiled mutants; then per-producer refusal counts before/after.
- Checks: common checks; proofs for one Kalima alias, the tower, the five item producers and Muun
  appearances 375/376/377; unchanged pool caps (4,096 particles, 500 joints, 200 effects, 1,000 sprites).

### 2. RENDER-ACTORS-008, actor caller-service groups, L

- Scope: three uniform reasons in the 217 incomplete selectors (branch): "additional caller services:
  effect" 66 (27 plain, 14 both-hand, 13 right-hand, 8 NPC, 3 sword-sprite classes 1/5/10, 1 left-hand),
  "additional or different RenderLinkItem services" 25 (15 right, 10 left), "monster opener has extra
  load or different texture context" 18 (8 both, 8 right, 2 classes 595/635). C03.
- Start: `reconstructed/actors/` (`actors.c`, `monster_class_table.h`, `monster_open_table.h`,
  `plain_body_table.h`), `native/core/mu_world_actors.c`, `native/world/parts/actors.c`,
  `scripts/validate_actor_groups.py` on the 007 branch, `docs/research/actor-group-decisions.csv`
  (branch). Original: RenderCharacter's final skeleton branch `0x01369f98..0x0136a00d`, CreateMonster
  `0x0137fbac..0x0138ce1c`, RenderObject `0x016d4fe4`, link render `0x012bd910`.
- Dependency and conflict: stack on ACTORS-007. Consumer files belong to lane 1: record a missing id,
  do not add its consumer. Shares nothing with items if `mu_renderchar.c` is left alone.
- Method: add a per-row recorder of the caller's ordered effect and link requests to the group
  verifier; admit a row when every request has a native consumer and the request stream matches the
  original in the 28 world/action contexts ACTORS-007 uses; publish the missing ids per refused row.
- Checks: common checks; regenerated census and group CSVs; negative kind/world/action controls;
  native loads with textures; the four option-untouched probes per admitted selector.

### 3. RENDER-EFFECTS-035, skill callers outside the learned set, L, request side only

- Scope: (a) the 37 catalogue rows (DK 14, Elf 23); 27 use the default step `0x0139b454` and the
  default ends `0x013aea7a` / `0x013b1911`, ten have their own step or end body. (b) Death Stab 43 and
  auras 27/28, which share the general equipment-link selector. Aliases only with individually
  compared selector records, as 416/424.
- Start: `reconstructed/combat/skill_fx.c`, `demo_skill_fx.c`, `native/core/mu_combat.c`,
  `native/fixture/skills_model.c`, `native/client/demo-skills.txt`. Dispatchers `0x013966ea`,
  `0x013a90c0`, `0x013af035`; receive visual slice `0x0125f5d1` as the model for default-body rows;
  alias base walk `0x00bb1c32..0x00bb1c9e`. N10 L40-44, L279-284.
- Dependency and conflict: starts from EFFECTS-033. Owns the combat files; lane 1 stays out of them.
  Missing consumers are counted and handed to lane 7.
- Method: classification of all 37 rows first (step body, end body, receive slice, consumers present);
  then one caller verifier per uniform group, as EFFECTS-030/032.
- Checks: original request streams, sound/default words, frame gates and RNG interleaving; fixtures
  with zero sent requests, hits and kills. No learned-set change in the shipped demo without a note
  in the handoff; no eligibility, damage, mana or cooldown.

### 4. HERO-ITEMS-002, hero head slot, weapon override and scale writes, M

- Scope: draw slot 0 for the seventeen helms whose class head must show; reproduce `0x009dadf1` for
  the worlds `0x009dacb8` lists; the remaining `0x01394f6f` visual scale writes (`+0x32f4`, part
  floats `+0x288`). Omit `0x00a00fb7` (stat machine) and service state.
- Start: `native/world/world_rt.c` (loader starts at slot one), `native/world/parts/hero.c`,
  `reconstructed/hero-equipment/hero_equipment.c` (`mu_he_head_type`), entry `0x01394870`.
- Dependency and conflict: none with running lanes if `mu_renderchar.c` and the item tables are not
  edited. The older inventory/record-format limits of HERO-ITEMS-001 are superseded; do not copy them.
- Method: trace the record-to-load boundary and head suppression once; one table-driven comparison
  over the seventeen helms and over the override world list; negative controls for other worlds.
- Checks: common checks; hero proofs with and without each helm group; default identity (tour heroes
  wear class parts, so no default view should change; explain any that does).

### 5. RENDER-WORLDS-INNER-006, admissions from the all-world census, M/L

- Scope: exactly the rows that RENDER-WORLDS-PICK-001's census publishes as partial or refused while
  their consumers exist. Fixtures only; no event model. 46/98 stay refused.
- Start: the census CSV and `docs/research/client-worlds-pick.md` (not on any branch at this
  snapshot), `scripts/world_inner_census.py` (branch), `reconstructed/objects/`,
  `native/core/mu_objects_runtime*.c`, `docs/research/client-worlds-inner.md`.
- Dependency and conflict: do not start before the census is pushed. Same files as PICK-001. If the
  census leaves fewer than about ten uniform rows, drop the lane and record why.
- Method: one instruction-checked verifier per form (the INNER-003..005 producer/adapter pattern).
- Checks: common checks; before/after renders per affected world; unchanged captures elsewhere.

### 6. RENDER-ITEMS-002AB, three remaining body groups, L

- Scope: 92 of the 144 bodies (branch): producer/service program missing 50, unread scalar/colour
  program 24, variable body draw count 18. Stop at the existing 24-scalar, twelve-operation,
  sixteen-draw and 512-KiB audit limits unless a group needs a stated, reviewed change.
- Start: `scripts/gen_item_bodies.py`, `scripts/gen_item_owner_fx.py`,
  `scripts/classify_item_bodies.py`, `reconstructed/renderchar/`,
  `docs/research/item-body-groups-002aa.tsv` (branch), which holds each row's helper and draw
  addresses, stopped fixture address and refusal reason.
- Dependency and conflict: stack on ITEMS-002AA (PR #404). New producers will request new pairs:
  list them for lane 1 or 7, add no consumer.
- Method: as 002AA: one reader per group, per-row original comparison, C-to-C admission delta,
  classifier delta. Research part: the next free number after 41 in `client-render-items.md`.
- Checks: common checks; table reproduction and header size under the cap.

### 7. RENDER-EFFECTS-036, effect consumers, M/L

- Scope: the 17 effect-side ids: ten world effects, Blood Storm downstream (`0x585/0`, `0x586/0`,
  `0x4b7/1`, particle `0x8145/1`, blur `0x814b`), Crescent `0x49e/0`, Fire Breath `0x8001/0`.
- Start: `reconstructed/effects/`, `native/core/mu_effect.c`, `mu_particles.c`; Blood Storm bodies
  `0x013f2b83`, `0x014a18fc`, `0x013f2c53`, `0x014a1b1c..0x014a2131` (N09 research L65-66).
- Dependency and conflict: serial after lane 1 (same module and registries).
- Method and checks: as lane 1. Fire Breath's mount body stays outside; admit only the effect.

### 8. MOUNT-VISUAL-002, later mounts' class visuals, M

- Scope: class visuals (vtable `+0x1c`, loop `0x0106bc2b`) of Ice Dragon, Pierce Lion, Ur, Leviathan,
  Tauros and Divine Horse; the buff path of the draw `0x017f746f`; alternate-grid shock rings.
- Start: `reconstructed/helpers/` (`mount_class.c`, `mount_render.c`),
  `native/core/mu_world_helpers.c`, `native/world/parts/helpers.c`,
  `scripts/validate_mount_visuals.py`; Shining Tail visuals `0x01057fb0..0x01059fdc` as the model.
- Dependency and conflict: none with running lanes. Muun files are separate.
- Method: one table-driven verifier over the six bodies; refuse rows whose particle kinds are missing.
- Checks: common checks; one proof per mount with a demo rider.

### 9. AUDIO-007, owner classification of unresolved sound sites, L

- Scope: the 516 owner-unknown candidates (359 prologue groups) and the eight refused whole owners
  (`0x00dd852c` 19, `0x00dde1fb` 14, `0x00de51cf` 11, `0x00d7ec63` 3, `0x00dee2d1` 19, `0x00e0dac7` 12,
  `0x00da9350` 16, `0x00d5b688` 3).
- Start: `scripts/audio_caller_census.py`, `scripts/audio_owner_groups.py`,
  `docs/research/audio-006-entry-groups.csv` (branch), `reconstructed/audio/`,
  `native/core/mu_monster_audio.h`.
- Dependency and conflict: after PR #402. Added sound-call lines only in shared files.
- Method: bounded caller-chain root classification (the UI-WINDOWS-006 trigger-root approach) to give
  each candidate an owner; publish group sizes; wire only groups whose owner exists natively.
- Checks: ordered site/id/object/loop comparison per emitted edge; decoded smoke for new ids. Never
  follow `0x01854279..0x018542c2`; the 66 class-use sites stay refused.

### 10. UI-WINDOWS-007, item-record popups and unbound parents, M

- Scope: the eight provider-missing rows that need a clicked or hovered item record, view only, and
  the parents GuildInfoFrame and MiniGameRummy. UI-WINDOWS-006 labels those records authoritative: a
  row is admitted only when an authored fixture record of its kind already exists.
- Start: UI-WINDOWS-006's ledger (not published at this snapshot), `native/gfx/mu_gfx_layer.c`, a new
  `native/gfx/mu_gfx_windows7.inc`, `scripts/survey_ui_indirect.py`; open sites `0x00b04ba3`,
  `0x00be5405`, `0x00be5453`, `0x0126f12c`, `0x0126f203`.
- Dependency and conflict: after UI-WINDOWS-006. No transactions, splits or rewards.
- Checks: original route/controller decisions, compiled mutants, native journeys with captures.

### 11. RENDER-ACTORS-009, NPC opener and appearance-reader groups, M

- Scope: 18 NPC rows whose opener file/texture/action/model state differs, six constructor
  render-state overrides and ten extra-bitmap rows. C03.
- Dependency: serial after lane 2 (same files). One reader per group.

### 12. CHARSEL-ITEMS-002, +15 attachments and selection cloth, M

- Scope: `0x016d53a4` class attachments and the cloth setup for authored selection records.
- Start: `native/core/mu_charsel.c`, `native/charsel/parts/character.c`, `mu_charsel_rt.h`.
- Conflict: none with lanes 1 to 9 if it uses existing draw APIs.

### 13. WORLDS-WATER-001, Kalima water manager, research first, S/M

- Scope: where the manager behind getter `0x00deeb4e` is created and what its simulation reads.
  Stop with a written limit if creation depends on server state.
- Conflict: `reconstructed/objects`; serial with lane 5.

### 14. NATIVE-PERF-005, L, quiet machine only

- Unchanged from NEXT-GAPS-001: a quiet baseline, then driver submission, terrain/swap waits, GFx
  picking, repeated `getenv`/item lookup and Retina GPU cost. Never beside other lanes. S23.

## Parallel plan: six lanes without shared files

| Slot | Lane | Owned files | Starts when |
|---|---|---|---|
| A | 1 RENDER-EFFECTS-034 | `reconstructed/particles`, `reconstructed/joints`, `mu_particles.c`, `mu_joints.c`, bitmap table | Now, from PR #403's branch |
| B | 2 RENDER-ACTORS-008 | `reconstructed/actors`, `mu_world_actors.c`, `parts/actors.c` | ACTORS-007 PR-ready |
| C | 3 RENDER-EFFECTS-035 | `reconstructed/combat`, `mu_combat.c`, skill fixtures | Now, from PR #403's branch |
| D | 4 HERO-ITEMS-002 | `world_rt.c` hero loader, `parts/hero.c`, `reconstructed/hero-equipment` | Now |
| E | 6 RENDER-ITEMS-002AB | Item generators, `reconstructed/renderchar` | Now, from PR #404's branch |
| F | 8 MOUNT-VISUAL-002, then 5 RENDER-WORLDS-INNER-006 | `reconstructed/helpers`, `mu_world_helpers.c`; then `reconstructed/objects`, `mu_objects_runtime*.c` | Now; PICK-001 PR-ready |

Alternates for a free slot: 9 AUDIO-007 after PR #402, 10 UI-WINDOWS-007 after UI-WINDOWS-006.
Serial pairs: 1 then 7; 2 then 11; 5 and 13. A and C both start from PR #403's branch: C owns
`mu_combat.c` and A does not edit it. `scripts/validators.toml`, `scripts/pins.py`, Makefiles and the
status documents take appended rows only; on conflict keep both sides. These slots describe file
ownership, not permission to exceed the load and memory guard.

## At diminishing returns: do not start

| Candidate | Why | Source |
|---|---|---|
| A generic UI-WINDOWS sweep | 17 provider-missing rows open only from a server response; 30 are state-dependent; 43 have no route after two published sweeps and a third in progress | N15 L15-18, L36-46; C02 |
| MUUN-VISUAL-006 | Left: nine mesh rows the models lack, six absent assets, appearance 193, code 363 actions 3/4. Consumers are lane 1 | N21 L242-251 |
| Item bodies outside lane 6 (52) | Helper caller 17, fixture stop 12, matrix stack 10, independent failure 10, entry state 3; named refusals `0x1710`, `0x10fd`, four shields, four armour overlays | N02 L53-69 |
| Learned-skill leftovers | Defense: no held-input rule in the recovered code. Summons: ground effect done, spawn selector and lifetime unproved. Stale entry 47. Fire Breath mount body | N09 L535-545 |
| Actor single cases | 1/5/10 sprite placement, 595/635 type-226 lifetime, 374/642, 378, 617, 546/918 textures, 22/866 alpha callback, eleven rows behind unresolved callers `0x00fdab58`, `0x01377aef`, `0x0095d4f1` | N07 L326-340; C03 |
| Worlds 46/98 | Static factory traced completely for direct registrations; no handler object or vtable | N11 L23-25, L116-117 |
| Audio class-use sites (66) and Guardian sites | Target, buff, request or timing owner absent | N18 L51, L98-100 |
| Terrain | Only authoritative Chaos stage and camera interpolation state remain | N13 L49-51 |
| Login-scene unnamed passes | The login world creates none of them in the reconstructed code | N26 L24-26 |
| Input context guards, IME movie | OS composition already works; no evidenced visible gain | N28 L101-106 |

## Superseded: NEXT-GAPS-001 snapshot

NEXT-GAPS-001 ranked ten lanes on main `ff8e0543`. Their state on `c5b9d5ca`:

| 001 lane | State |
|---|---|
| 1 RENDER-ITEMS-002Y | Merged (#382); continued by 002Z (#395) and 002AA (PR #404) |
| 2 RENDER-ACTORS-002 | Merged (#368); continued through ACTORS-006 (#396) and 007 (branch) |
| 3 MUUN-VISUAL-001 | Merged (#371); continued through 004 (#397) and 005 (PR #401) |
| 4 RENDER-EFFECTS-027 | Merged (#370) |
| 5 RENDER-WORLDS-INNER-001 | Merged (#365); continued through INNER-005 (#399) |
| 6 RENDER-WORLDS-PICK-001 | PR-ready: box and mouse input done; census published ([CSV](world-inner-census.csv), [finding](client-worlds-pick.md)): 941 pairs, 420 drawn / 213 partial / 308 refused. The 46/98 handler is chain hook 11 and is ported there, so those rows are no longer refused; the producer-less rows are chain hooks 1 (`0x009db8b1`) and 6 (`0x00dac0a2`) |
| 7 AUDIO-002G | Merged (#366); continued through AUDIO-005 (#398) and 006 (PR #402) |
| 8 CHARSEL-ITEMS-001 | Merged (#367) |
| 9 NATIVE-PERF-005 | Not started; still quiet-machine only (lane 14) |
| 10 APP-REFRESH-012 | Merged (#375); further app work is owner-paused |

Obsolete parts of the 001 count table: item bodies 1,404; the 93-program / 30-pair particle census;
the Ferea clouds and Hammer14 refusals (closed by EFFECTS-025); the 32-row Player-model actor subset
(replaced by the 1,024-selector census); the 31-entry movie registry versus 179 movies (replaced by
the 134-row route survey); the 22 worlds with named inline gaps (all delivered except 46/98); the
76-site and 1,980-site audio inventories as separate figures (now one census). The 001 statement
that no whole-client refused-effect census, actor census or window denominator exists is partly
superseded: the actor and window denominators now exist; a whole-client refused-effect census still
does not.

Still valid from 001: Test Area, Aquila, Acheron, Deep Dungeon and Uruk supersessions; the texture
survey's 13 white types are unworn hair meshes; scoped numbers must not be added into a completion
percentage; this lane makes no visual-equivalence, audio-parity or performance claim.

## Source ledger

Line ranges refer to main `c5b9d5ca` unless the entry names a branch commit. Branch entries link to
immutable snapshots. The external brief, resume and queue are dispatch context and are not copied
into the repository. A later lane must refresh ownership before dispatch.

| ID | Owning source and exact location |
|---|---|
| N01 | [RENDER-ITEMS-002Z](../handoffs/RENDER-ITEMS-002Z.md), L17-21, L36-39, L204-211 |
| N02 | [ITEMS-002AA snapshot baec5c08](https://github.com/fryezero/mu-the-matrix-native/blob/baec5c08f1c69b411ad70dc310663de50b87c21f/docs/handoffs/RENDER-ITEMS-002AA.md#L14-L98), L16-19, L21-29, L53-69, L78-82, L84-98 |
| N03 | [RENDER-EFFECTS-031](../handoffs/RENDER-EFFECTS-031.md), L7-27, L118-127 |
| N04 | [Item research on baec5c08](https://github.com/fryezero/mu-the-matrix-native/blob/baec5c08f1c69b411ad70dc310663de50b87c21f/docs/research/client-render-items.md#L3627-L3640), L3627-3640 |
| N05 | [RENDER-EFFECTS-026](../handoffs/RENDER-EFFECTS-026.md), L15-17 |
| N06 | [RENDER-ACTORS-006](../handoffs/RENDER-ACTORS-006.md), L14-16, L125 |
| N07 | [ACTORS-007 snapshot a1eba04b](https://github.com/fryezero/mu-the-matrix-native/blob/a1eba04bbd99658a805e7b93cd72e1928048e18c/docs/handoffs/RENDER-ACTORS-007.md#L3-L45), L3-45, L317-344 |
| N08 | [RENDER-EFFECTS-032](../handoffs/RENDER-EFFECTS-032.md), L16-45, L394-404 |
| N09 | [EFFECTS-033 snapshot 35ae89fe](https://github.com/fryezero/mu-the-matrix-native/blob/35ae89fe717a455163db717584bce62a75c4fe80/docs/handoffs/RENDER-EFFECTS-033.md#L15-L108), L15-108, L531-555; [its research note](https://github.com/fryezero/mu-the-matrix-native/blob/35ae89fe717a455163db717584bce62a75c4fe80/docs/research/client-render-effects-033.md#L57-L76), L57-76, L198-205 |
| N10 | [Demo-class skill audit](client-render-effects-030.md), L18-44, L152-214, L264-291 |
| N11 | [RENDER-WORLDS-INNER-005](../handoffs/RENDER-WORLDS-INNER-005.md), L9-25, L114-126 |
| N12 | [PICK-001 snapshot 5eaeb445](https://github.com/fryezero/mu-the-matrix-native/blob/5eaeb4455e9022ca83e8f501981d6c3001c9d085/docs/handoffs/RENDER-WORLDS-PICK-001.md#L7-L30), L7-30 |
| N32 | Delivered inline worlds: [INNER-001](../handoffs/RENDER-WORLDS-INNER-001.md), L14-18; [INNER-002](../handoffs/RENDER-WORLDS-INNER-002.md), L8-10; [INNER-003](../handoffs/RENDER-WORLDS-INNER-003.md), L7-8; [INNER-004](../handoffs/RENDER-WORLDS-INNER-004.md), L140-146 |
| N13 | [RENDER-TERRAIN-002](../handoffs/RENDER-TERRAIN-002.md), L42-51 |
| N14 | [UI-WINDOWS-005](../handoffs/UI-WINDOWS-005.md), L31, L49-71, L262-272 |
| N15 | [UI-WINDOWS-006 snapshot 8e0c9713](https://github.com/fryezero/mu-the-matrix-native/blob/8e0c971370fbcd6227430276b689175f4b3ab8b7/docs/handoffs/UI-WINDOWS-006.md#L8-L46), L8-46 |
| N16 | [APP-POLISH-009](../handoffs/APP-POLISH-009.md), L3, L289-297 |
| N17 | [AUDIO-005](../handoffs/AUDIO-005.md), L22-31 |
| N18 | [AUDIO-006 snapshot 83dc2528](https://github.com/fryezero/mu-the-matrix-native/blob/83dc25284eb798b86290120ee134c6cd30a277c7/docs/handoffs/AUDIO-006.md#L7-L54), L7-54, L94-100, L256-260 |
| N19 | [Audio research on 83dc2528](https://github.com/fryezero/mu-the-matrix-native/blob/83dc25284eb798b86290120ee134c6cd30a277c7/docs/research/client-audio.md#L1027-L1113), L1027-1047, L1096-1113 |
| N20 | [MUUN-VISUAL-004](../handoffs/MUUN-VISUAL-004.md), L11-13, L30, L206-212 |
| N21 | [MUUN-VISUAL-005 snapshot 7fac39fa](https://github.com/fryezero/mu-the-matrix-native/blob/7fac39fa22e6f86aec3755ff615c397eaad3eadb/docs/handoffs/MUUN-VISUAL-005.md#L7-L47), L7-47, L240-259 |
| N22 | [Helper visuals](client-helper-visuals.md), L27-32, L45-60, L173-178 |
| N23 | [Dark Raven](client-dark-spirit.md), L156-160 |
| N24 | [CHARSEL-ITEMS-001](../handoffs/CHARSEL-ITEMS-001.md), L163-177 |
| N25 | [Character selection](client-character-select.md), L776-786 |
| N26 | [Login scene header](../../native/core/mu_login.h), L12-26 |
| N27 | [Login scene](client-login-scene.md), L76-84, L214-222 |
| N28 | [INPUT-001](../handoffs/INPUT-001.md), L101-106 |
| N29 | [RENDER-WORLDS-INNER-001](../handoffs/RENDER-WORLDS-INNER-001.md), L178-184 |
| N30 | [RENDER-WORLDS-INNER-004](../handoffs/RENDER-WORLDS-INNER-004.md), L140-149 |
| N31 | [Pets](client-pets.md), L151-162 |
| C02 | Text-only counter over [ui-window-route-survey.csv](ui-window-route-survey.csv): 134 rows; `bound` yes 28 / no 106; `classification` 13 provider-complete, 33 provider-missing, 30 state-dependent, 43 no route found, 15 previously bound |
| C03 | Text-only counter over `docs/research/actor-group-decisions.csv` and `actor-missing-plan-groups.csv` at ACTORS-007 `a1eba04b`: rows with decision `incomplete` grouped by `reason`; 217 rows; the three lane-2 reasons total 66 + 25 + 18 |

Entries kept from the NEXT-GAPS-001 ledger because they are still cited (locations verified unchanged
on `c5b9d5ca`, except S20 whose file gained later sections after the cited lines):

| ID | Owning source and exact location |
|---|---|
| S13 | [Input coverage](client-input.md), L51-106 |
| S15 | [World-handler coverage](world-handler-coverage.md), L64-69; [reviewed JSON](world-handler-coverage.json) |
| S19 | `~/Documents/MTM/mu-mac-tools/native/RESUME-2026-11-15.md` (owner instructions, next queue) and the "Session log 2026-11-15" section of `AGENT-QUEUE.md`; replaces the 2026-11-09 resume cited by 001 |
| S20 | [Skill visual coverage](client-skill-visual-coverage.md), L28-113 |
| S23 | [NATIVE-PERF-004](../handoffs/NATIVE-PERF-004.md), L7-45, L118-133 |
| S26 | [HERO-ITEMS-001](../handoffs/HERO-ITEMS-001.md), L125-142, with later inventory/cloak supersessions applied |
| S30 | [CLOAK-004](../handoffs/CLOAK-004.md), L126-141 |
| S31 | [RENDER-WORLDS-AFTER6](../handoffs/RENDER-WORLDS-AFTER6.md), L13-24, L63-70 |
| S34 | [RENDER-TIME-003](../handoffs/RENDER-TIME-003.md), L84-92 |
| S36 | [RENDER-WORLDS-RAKLION](../handoffs/RENDER-WORLDS-RAKLION.md), L172-182 |
| S39 | [README](../../README.md), L455-474. Rendering counts there are stale; used only for the still-open domain boundaries |
| S42 | [AUDIO-002F](../handoffs/AUDIO-002F.md), L78-84 |

The other NEXT-GAPS-001 ledger entries (S01-S12, S14, S16-S18, S21, S22, S24, S25, S27-S29, S32, S33,
S35, S37, S38, S40, S41, S43-S48, C01) supported counts that are now superseded; they remain in
the repository history at `9d6ce467`.
