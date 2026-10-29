# Continue from here

RENDER-WORLDS-AFTER: the after-character pass `0x016d6949` is reconstructed for every world (world list plus the class byte +5 of worlds 134..145, selector `0x017fe909` with its world cases and class slot 0x14 overrides); Abyss of Atlans 1-3 now skip their flagged objects in the first pass (class slot 0x38) and draw them after characters (slot 0x3c). The CreateObject/MoveObject world-group hooks are verified inactive in all 48 class worlds (the class method is last). The frame time `0x01cf103c` (`0x012aeb2b`) feeds the window loops; tours keep 0.1. 13,424 instruction cases, zero mismatches, 21/21 mutants; 29/32 + 14/14 tour views identical, Abyss image error unchanged. [Handoff](handoffs/RENDER-WORLDS-AFTER.md).

RENDER-EFFECTS-005: rank-5 item owner effects for all 19 types (owner bones 35/26, 0x84e2/0x83de particles, 0x7fdd sprite, level-9 overlays) through a separate owner hook, and Deep Dungeon type 52's DungeonStone 0x43a consumed instead of refused. 10,800 instruction comparisons, zero mismatches, 25/25 compiled mutants. Skill coverage unchanged (20/23, 65/77); rank-5 owner effects 0/19 to 19/19. Other bows' arrows, bow 0x12f9 sparks, Rudolph 0x3fa and pet particle kinds remain. [Evidence](research/client-render-effects-005.md), [checks and remaining work](handoffs/RENDER-EFFECTS-005.md).

RENDER-WORLDS-G2: object models now resolve textures as OpenTexture `0x0181fbe9` does (bitmap-name map of the startup and world-pass models, then `Data\Item\`, `Data\Item\Texture\`; textures from `Object<folder>`), and Vulcanus gets its 3700 far plane. Zero unresolved object textures at the 19 affected captures; image error Deep Dungeon 3 13.5 → 3.2, Vulcanus 2.7 → 1.8. 4,157 instruction cases, zero mismatches, 17/17 mutants. [Evidence](research/client-worlds-g2.md), [checks and limits](handoffs/RENDER-WORLDS-G2.md).

BUILD-DEPS-001: automatic header dependencies (`-MMD -MP` `.d` files) for every C/C++ compile the gate builds (native, gfx converter, 36 reconstructed Makefiles, model-recovery, live-readers). The hand-written header lists on the native object rules are gone: a header change now rebuilds exactly its includers. The old lists had missed 826 object/header pairs in 102 native objects. Clean builds before and after are byte-identical (647/647 outputs). [Checks and limits](handoffs/BUILD-DEPS-001.md).

RENDER-WORLDS-P2: Kanturu Underground (137) and Ignis Volcano (138) primary create/move/visual methods; six more verified methods, two more classes: 76/144 and 26/48 with O and P. 6,000 instruction cases, zero mismatches, 35/35 mutants. At the two DATA-ACQ-002 arrival tiles all 6,803 range and 262 Ignis after-character differences go to zero; image 137 5.899 → 5.790, 138 unchanged; unsupported joint kinds and StreamMesh refused and counted. [Evidence](research/client-worlds-p2.md), [checks and limits](handoffs/RENDER-WORLDS-P2.md).
RENDER-WORLDS-O: Abyss of Atlans 1-3 (128-130) primary methods (+9; 61/144 verified, 21/48 classes with RENDER-WORLDS-N); Abyss 2/3 now take their tile bitmaps from World129 as `0x01829457` does (image error 82.2 → 4.4 and 48.0 → 2.2). 9,000 + 5,700 instruction cases, zero mismatches, 24/24 mutants. [Evidence](research/client-worlds-o.md), [checks and limits](handoffs/RENDER-WORLDS-O.md).

RENDER-EFFECTS-004: Rageful Blow's ordinary-world chain (0x461 and nine pieces, item initialiser, weapon draw), Triple Shot through verified CreateArrows/CreateArrow (0/+15/-15) and Spirit of Guardian's wing 0x460/4. Primary routes 18/23 to 20/23, weighted 56/77 to 65/77. 32,000 instruction comparisons, zero mismatches, 15/15 compiled mutants. Rank-5 item owner effects remain for a slice agreed with RENDER-ITEMS-002K. [Evidence](research/client-render-effects-004.md), [checks and remaining work](handoffs/RENDER-EFFECTS-004.md).

RENDER-WORLDS-P: Old Kethotum (135), Burning Kethotum (136) and Bloody Tarkan (140) primary create/move/visual methods; +9 primary methods, +3 classes; with RENDER-WORLDS-O 70/144 verified methods, 24/48 classes. 10,000 instruction cases (incl. clamped AddTerrainLight 0x016caeae), zero mismatches, 51/51 mutants. At the three DATA-ACQ-002 arrival tiles static-field differences 399/303/30 → 0/0/2; image error unchanged. 136 type-0xb5 .ein effects have no native consumer. [Evidence](research/client-worlds-p.md), [checks and limits](handoffs/RENDER-WORLDS-P.md).

RENDER-WORLDS-N: Nixies Lake (113) and Deep Dungeon 1–5 (116–120) primary create/move/visual methods; 52/144 verified methods, 18/48 classes. 13,000 instruction cases, zero mismatches, 29/29 mutants. At the six DATA-ACQ-002 arrival tiles all 13,690 range and 436 after-character differences go to zero; image error mixed (four lower, Deep Dungeon 5 higher). [Evidence](research/client-worlds-n.md), [checks and limits](handoffs/RENDER-WORLDS-N.md).
NATIVE-PERF-004 (merged, acceptance open): pose workers, exact topology cache, ordered GL capture and a lease-audit fast path; main-thread CPU lower in all seven paired runs, 2,804/2,804 frame pairs identical; strict 25 Hz passes only crowd40. Next: NATIVE-PERF-005. [Checks and limits](handoffs/NATIVE-PERF-004.md).

RENDER-WORLDS-M: six Uruk nested particle lifecycles and the `flare_mono` registration (Market/Raklion kinds were already L's). 18,000 checks, zero mismatches, 17/17 compiled mutants and four original loader calls; 16 saved views unchanged; authored Uruk view 47 unsupported requests to 0. [Evidence](research/client-worlds-m.md), [checks and limits](handoffs/RENDER-WORLDS-M.md).

DATA-ACQ-002: guided live captures on the owner's client (four locked sessions, warps only): 32 arrival captures in 31 worlds, 27/48 world classes now have an original populated capture; 16 classes are not reachable by warp. Native camera within 0.007, primary light equal in 31/32; music indices 43 and 44 both iDoppelganger. [Captures and comparison](research/client-world-captures-2.md), [inputs and limits](handoffs/DATA-ACQ-002.md).

AUDIO-002 part 6: live-read music table verified: indices 43 and 44 are both iDoppelganger, all 76 names resolve and are installed; `0x06fba808` is the channel-group name string. Doppelganger manager `0x00e305ee` reconstructed (caller unrecorded); 4,291 cases, zero mismatches, 10/10 mutants; locked Mac gate passes 1,634 tests. [Checks and limits](handoffs/AUDIO-002F.md).

README-REFRESH-004: [handoff](handoffs/README-REFRESH-004.md), [claim sources](research/readme-refresh.md#readme-refresh-004-claim-sources). Public progress refreshed through PR #241; images/pins unchanged, no runtime code or live game used.

SYS-MISC-001b: HelpWindow helpdata reader/controller (888 original-instruction cases, zero mismatches, 18/18 mutants) and native Ctrl+H hosting of the real movie. Text clips only in fixed single-line movie fields (as the original lays them out); hotkey lists scroll to their last row. Locked Mac gate passes 1,630 tests. [Checks and limits](handoffs/SYS-MISC-001b.md).

VERIFY-HARNESS-002: two bounded tools now use shared capture pins and loading, with exact legacy errors. Eight before/after caller reports agree apart from two elapsed-time fields; 72 private owning tests pass. Locked Mac gate passes 1,608 tests and 11 fixtures. Eight loader exceptions and shared-machine consolidation remain. [Evidence and checks](handoffs/VERIFY-HARNESS-002.md).

RENDER-WORLDS-L: seven Karutan/Raklion/Market particle lifecycles and four exact bitmap registrations. 21,000 checks, zero mismatches, 13/13 compiled mutants and five original loader calls; saved-tour OBJECT/light and 13 other views unchanged. [Evidence](research/client-worlds-l.md), [checks and limits](handoffs/RENDER-WORLDS-L.md).

SESSION-SOCIAL-001a: party list/invitations and supplied bars now use a session domain and plaintext fixture feed; winParty retained. Locked Mac gate passes 1,600 tests. Invite/answer sends remain unsent pending NET-DECODE. [Checks and remaining social work](handoffs/SESSION-SOCIAL-001a.md).

AUDIO-002 part 5: three character-select Enter/Esc sound-25 sites reach the native host. Caller adapters 73 to 76; 5,968 original-tick cases, zero mismatches, 11/11 compiled mutants; locked clean Mac gate passes 1,596 tests. [Checks and limits](handoffs/AUDIO-002E.md).

RENDER-WORLDS-K: built-in Lost Tower/Tarkan/Icarus producers and Atlans dispatch correction; 6,000 instruction cases, 21/21 source mutants plus 2/2 native host controls. Icarus image error 26.897 to 23.154. Locked Mac gate passes 1,585 tests. [Checks and limits](handoffs/RENDER-WORLDS-K.md).

RENDER-EFFECTS-003: Meteorite, Aqua Beam primary chain and Inferno bursts; K particle consumers and three exact bitmap registrations. Primary routes 15/23 to 18/23, weighted 46/77 to 56/77. 24,453 instruction comparisons plus 2,547 removal checks, 17 instruction mutants plus one frame mutant and four loader-call checks. Locked Mac gate passes 1,582 tests (200 explicit skips) and ten fixture scenarios. [Evidence](research/client-render-effects-003.md), [checks and remaining work](handoffs/RENDER-EFFECTS-003.md).

SESSION-MAP-001a: frame-fed NPC/portal markers and detector dots through the session and plaintext fixture; 6,501 instruction cases, zero mismatches, 4 compiled and 10 historical mutants caught. Travel remains unchanged. [Checks and limits](handoffs/SESSION-MAP-001a.md).

RENDER-WORLDS-J completes captured Raklion/Karutan primary groups: 33/144 verified methods, 11/48 classes; 111 methods remain. [Evidence](research/client-worlds-j.md), [checks and limits](handoffs/RENDER-WORLDS-J.md).

RENDER-ITEMS-002 part 11: 967/1,674 bounded bodies, 17/17 skins, seventeen link targets/twenty-two types. Adds 87 bodies (41 weapon, 22 armour, 24 pet/item) through per-type wave/sine scalar programs parsed from pinned instructions; 26,154 new instruction cases, zero mismatches, 11/11 compiled mutants. 707 bodies and rank-5 owner effects remain. [Checks and limits](handoffs/RENDER-ITEMS-002K.md).

RENDER-ITEMS-002 part 10: 880/1,674 bounded bodies, 17/17 skins, seventeen link targets/twenty-two types. Adds 104 armour, one weapon and the six requested seed bodies; 33,622 new instruction cases, zero mismatches, 12/12 compiled mutants. Locked Mac gate passes 1,615 tests. 794 bodies and rank-5 owner effects remain. [Checks and limits](handoffs/RENDER-ITEMS-002J.md).

SESSION-ITEMS-001a: session ground ownership and fixture 20/21 feed; 26,200 instruction cases with zero mismatches. Locked Mac gate passes 1,555 tests. Pickup-answer/inventory route evidence remains open. [Checks and limits](handoffs/SESSION-ITEMS-001a.md).

RENDER-EFFECTS-002: Poison, Ice/debris and Power Wave session visuals; audited primary routes 12/23 to 15/23, weighted 37/77 to 46/77. New instruction evidence: 10,619 instruction comparisons and 381 removal checks, zero mismatches, 8/8 compiled mutants. Locked Mac gate passes 1,550 tests. [Coverage and limits](research/client-skill-visual-coverage.md), [checks](handoffs/RENDER-EFFECTS-002.md).

RENDER-WORLDS-I: [handoff](handoffs/RENDER-WORLDS-I.md). Six Loren Market/Uruk primary methods verified; 31/144 families across 11/48 classes. DATA-ACQ-002, Uruk weather/keyed-effect/colored-joint consumers and 113 primary methods remain.

RENDER-TIME-002 live half: read-only post-draw sampler and input replay; two Lorencia runs with mugl patches off (960x600, the client has no 640x480). `compare --mode live` fails: phase unaligned, plus refused live zoom, other characters, sub-25 fps WorldTime jitter and a visible-object gap. Hero path, placement and primary light agree. Threshold review recorded; no limit changed. [Checks and limits](handoffs/RENDER-TIME-002.md).

RENDER-TIME-001 native side: fourteen scripted views across thirteen maps, full-draw temporal samples and regression thresholds. Locked Mac gate passes 1,544 tests; private temporal rerun passes 16/16. The live capture/phase-alignment half remains open. [Checks and limits](handoffs/RENDER-TIME-001.md).

APP-REFRESH-001: [app refresh, smoke and installation](handoffs/APP-REFRESH-001.md).

README-REFRESH-003: [handoff](handoffs/README-REFRESH-003.md), [claim sources](research/readme-refresh.md). Public progress refreshed through PR #207; existing images/pins unchanged, no runtime code or live game used.

SESSION-GLOBALS-001: explicit session/runtime state ownership and committed sequential/fresh-process parity checks. [Inventory and checks](handoffs/SESSION-GLOBALS-001.md).

AUDIO-002 part 3: 36 combat/skill sound sites use session cues, including remote player and monster voices; 19,548 instruction cases. [Checks and limits](handoffs/AUDIO-002C.md).

AUDIO-002 part 4: latest viewport buff input resolves the NPC voice; the migrated Master click enters the cue ring. Caller adapters 66 to 73, sound-capable sites 65 to 73, including six ground-drop sites after SESSION-ITEMS-001a. 5,544 instruction cases, zero mismatches, 15/15 compiled mutants; locked clean Mac gate passes 1,571 tests. [Checks and limits](handoffs/AUDIO-002D.md).

RENDER-WORLDS-H: [handoff](handoffs/RENDER-WORLDS-H.md). Six Duel Arena/world-82 methods verified; 25/144 primary families across 9/48 classes. DATA-ACQ-002 and 119 primary methods remain.

README-STRESS-001: [handoff](handoffs/README-STRESS-001.md). README images 26/27 are privacy-reviewed and pinned; remote armour now retains Data/Effect glow textures. Historical #201 timings remain contextual.

SESSION-SKILL-001: session-owned learned skills, hotkeys and trees in headless/GFx builds; demo replies use one plaintext fixture feed and encrypted casts stay unsent. [Checks and limits](handoffs/SESSION-SKILL-001.md).

INTEGRATION-GREEN-001: [handoff](handoffs/INTEGRATION-GREEN-001.md). Full offline integration is green with explicit optional skips; captures and corpus identity are documented. No new local input retained; lane artifacts are removed after merge.

RENDER-WORLDS-G: [handoff](handoffs/RENDER-WORLDS-G.md). Inventory and six Santa/Vulcanus methods implemented; 14 unaffected tour hashes unchanged. DATA-ACQ-002 captures and 125 primary methods remain.

RENDER-WORLDS-E: [handoff](handoffs/RENDER-WORLDS-E.md). Elbeland boids and Raklion event timer implemented; Aida light accumulation attributed. Full Mac gate passes, 1,463 tests; fourteen-view scores/hashes unchanged.

SESSION-COMBAT-001: plaintext loopback combat migration implemented; kills follow server frames, encrypted casts stay unsent. [Checks and limits](handoffs/SESSION-COMBAT-001.md).

AUDIO-002 part 2: [handoff](handoffs/AUDIO-002B.md). Thirty caller sites have adapters into the character session ring; one NPC buff input remains unresolved. Combat, unmigrated domains, music 43/44 and LIVE-PLAY comparison remain separate.

WORLD-ORDER-001: [handoff](handoffs/WORLD-ORDER-001.md). Tick/draw expectations now read compiled call records; native deviations are explicit. No runtime/order-number change.

RENDER-WORLDS-F: [handoff](handoffs/RENDER-WORLDS-F.md). Missing additive screen passes recovered and wired in both renderers. Original Tarkan/Raklion PNGs are absent, so live-image error remains unmeasured.

RENDER-WORLDS-C2: [handoff](handoffs/RENDER-WORLDS-C2.md). Persistent cover, owner-aware emitter ribbons and integer ambient clock are implemented. Raw Icarus image error is 26.897 / 27.663; exact captured animation phase remains unavailable.

RENDER-WORLDS-D: [handoff](handoffs/RENDER-WORLDS-D.md). Noria missing object 1 to 0; warp create/move/render wired. Raklion active event timer and Elbeland boids remain explicit follow-ups.

AUDIO-002 part 1: [handoff](handoffs/AUDIO-002.md). Native session audio reader and JSONL log are ready; event state and NPC lifecycle callers follow their domain migrations. The exact 43/44 read and virtualised gap remain open.

SESSION-VIEWPORT-001: [handoff](handoffs/SESSION-VIEWPORT-001.md), session-owned player records and fixture-driven --players.

VIEWPORT-MONSTER-001: [handoff](handoffs/VIEWPORT-MONSTER-001.md), shared monster/NPC records and fixture-driven placement.

RENDER-WORLDS-C: [Icarus handoff](handoffs/RENDER-WORLDS-C.md). Named sky/object/joint/dragon paths are ported; the persistent grey layer remains a measured fidelity gap.

RENDER-WORLDS-B: [handoff](handoffs/RENDER-WORLDS-B.md). Per-world moves/placements and snow are wired; nested warp effects and fresh locked live-image comparison remain bounded.

RENDER-WORLDS-A: [handoff](handoffs/RENDER-WORLDS-A.md), per-world flames and deferred draws after the environment, integrated through main `0a85441`; refreshed Mac gate passes and fidelity results are recorded.

SESSION-QUEST-001: [handoff](handoffs/SESSION-QUEST-001.md). Quest state and window actions now use the session;
the fixture owns demo policy. Next: the 70/71 body bytes and NET-DECODE, then account-owned world attachment.

DATA-ACQ-004 manifest slice: [handoff](handoffs/DATA-ACQ-004.md), [re-acquisition procedure](native-data.md). Jump-table diff remains pending on paused NET-DISPATCH-001.

- RENDER-TERRAIN-002: remaining terrain implementation and evidence are in [the milestone handoff](handoffs/RENDER-TERRAIN-002.md). No live client used; per-world object files untouched.

RENDER-ITEMS-002 part 6: [handoff](handoffs/RENDER-ITEMS-002F.md). 559/1,674 bodies, 17/17 skins, nine link targets/fourteen types integrated; ground and both inventory paths consume skin sprites. Remaining: 1,115 bodies, pose-aware rank 5, owner-dependent links and prior model/domain limits. Muun/nested map-object tables remain deferred.

RENDER-ITEMS-002 part 7: [handoff](handoffs/RENDER-ITEMS-002G.md). 635/1,674 bodies, 17/17 skins, twelve links/seventeen types. Every committed README stress-kit body is admitted. Locked Mac gate passes, 1,528 tests. Rank-5 pose/point oracle advances; full rendering, 1,039 bodies and prior limits remain.

LAYOUT-001: [handoff](handoffs/LAYOUT-001.md), generated read-side layouts and JSON consumers. Per-domain migrations can extend their own .def files.

INPUT-001 implemented: [router handoff and final checks](handoffs/INPUT-001.md), [recovered bindings and input-script contract](research/client-input.md). Unavailable domain/window rows and original IME candidate UI remain explicit.

CHARSEL-RT-001 is implemented. See [the lane handoff](handoffs/CHARSEL-RT-001.md) for runtime paths,
unchanged render comparisons and the 300-case private character-create check. Next: SESSION-ACCOUNT-001.

LAYOUT-PROBE-001: [handoff](handoffs/LAYOUT-PROBE-001.md). The manifest must preserve both flag/level fields and describe the attribute extent as a minimum.

## VERIFY-SESSION-001, 2026-10-27

Discovered fixture suites and skill `--fixture` mode are implemented. Two hero scenarios cover all eight
bound routes; per-scenario unbound is zero, unrecovered/unsent counts remain explicit. See
[the milestone handoff](handoffs/VERIFY-SESSION-001.md) for checks, artifacts and remaining work.

## Stage 1 merged (2026-10-25)

**Merged.** PRs #160-#165 are on main. Each passed `make test` on its merged tree; the last ran 1,283 tests. Each
lane's note is in `docs/handoffs/`:
- `NET-CRYPTO-001.md`
- `NET-LINK-001.md`
- `SESSION-CORE-001.md`
- `FIXTURE-001.md`
- `WORLD-RT-001.md`
- `VERIFY-HARNESS-001.md`
- [DATA-ACQ-003.md](handoffs/DATA-ACQ-003.md): bundled C first-run converter; 261 file and 9,166 bitmap hashes equal per option mode; temporary-HOME setup without Python passes, real second user unavailable.

**Integration fix.** `validate_crypto.py` now takes its pins from `scripts/pins.py` and has a manifest row; it
passed through the runner (568 cases at `--scale 2`, 14/14).

**Paused.**
- NET-DISPATCH-001: the agent was stopped by a safety check while writing `scripts/gen_dispatch.py`, so nothing was
  committed; the owner decides how it continues.
- Until then the session routes come from `native/net/dispatch.seed.def`.

**Next (stage 2).**
- NET-DECODE-001: the receive stage `0x012220fd` and the send wrap, over `libmucrypto`; this unblocks the
  encrypted `0x16` report and C3 fixtures.
- Feed `mu-walk --progress` through the session, now that WORLD-RT-001 is merged.
- INPUT-001, LAYOUT-001. CHARSEL-RT-001 and the 300-case private charcreate check are complete.

## Port completion design (ARCH-PORT-001, 2026-10-24)

**Decision and process**
- The owner decided that the finished native client logs in to the **real live servers**.
- Branch `claude/architect-native-port` adds the design that follows from that decision, in `docs/design/native-port/`:
  `rationale.md`, `plan.md` and `sketch/`, with `MODULES.md` and about 60 type and signature sketches at their
  future repository paths.
- It was made with pstack `architect`:
  - four read-only explorers covering runtime composition, network and demo servers, coverage gaps, and
    verification;
  - one explainer, with the "why" constraints;
  - three structurally different candidates: a session core, a re-hosted original image, and a trace contract;
  - an independent cross-judge, which scored them 29/27/13 and picked the same base;
  - a synthesis on the session core.
- The grafts and rejections are recorded in `rationale.md`, under "Synthesis decision".

**What changed outside the design directory.** The decision is recorded in `docs/roadmap.md` (end state and
"Completing the native port"), the `README.md` scope lines and an `AGENTS.md` pointer. No code or test changed.

**Checks.**
- `scripts/audit_repository.py` and `make test`; see the PR for the results.
- The sketches are not compiled.

**Next step.**
- Start the stage-1 lanes, which need no owner or operator answer: NET-DISPATCH-001 (`gen_dispatch.py` →
  `native/net/dispatch.def` plus `validate_dispatch.py`), NET-CRYPTO-001, NET-LINK-001 → SESSION-CORE-001 (the hero
  domain over a loopback fixture; plaintext `0x16` must produce `C1 4D 02 00 16`), WORLD-RT-001, CHARSEL-RT-001 and
  VERIFY-HARNESS-001.
- Each lane owns the paths listed in `plan.md`, under "Parallel lanes".
- The owner and the operator answered on 2026-10-25 (`docs/research/service-contract.md`):
  - a login needs only the account, and a native client is allowed;
  - sessions may be recorded, and automated play is allowed;
  - one client may be logged in at a time;
  - each user runs a guided capture for Native Data;
  - signing is deferred.
- Live runs use the dev account. The password stays in the Keychain item `mu-the-matrix-dev`.
- The plan now has LIVE-HARNESS-001 (`scripts/live_session.py`, game lock) and the client lock in NET-LINK-001.
- `GAME-LOCK.md` still names `~/Documents/mu-mac-tools`; the folder is now under `~/Documents/MTM/`. Its 3- and
  15-minute limits stand until the owner changes them.

## Guest rebuild and private checks (CAPTURE-REBUILD-001, 2026-10-24)

The QEMU x86 guest was rebuilt from the pinned Debian image (`20261015-2632`, SHA-512 matched) on QEMU 11.1.2, with
Wine `8.0~repack-4` and Mesa `22.3.6-1+deb12u2` (llvmpipe, OpenGL 4.5), `restrict=on` networking (outbound, host and
DNS checked unreachable). The client restored its text within 30 s. Each scope was captured with the tool revision
that made the pinned capture (`42ae903`, `3162f2f`, `f8cb2fd`, `b4bd515`); all manifests report
`complete_within_scope`, and every pinned digest was reproduced exactly: text `2bd5f2e9…`, second section
`c985e2e6…`, feature word `bce941d1…`, record bias/template `af5570f5…`/`5998e9d1…`, trig flag `67abdd72…`. The
neighbour table at `0x01cf1640` in a guest read of `0x01ced000` matches `a8cc4549…`
(`evidence/x86-guest-sec3-25/`, used through `MU_PATH_DIRECTIONS`).

With `MU_RECOVERY_INTEGRATION=1` and an installation whose `main.exe` matches the pin, 35 of 38 suites pass. The rest:

- `reconstructed/charsel`: all 1,488 character-create cases match, but its private test runs `--cases 60`, whose
  20 planted-mistake cases contain no CP949 lead byte, so the code-page mutant goes undetected (5/6). The
  documented `--cases 300 --mutations` run detects 6/6. The test's case count is too small, not the C.
- `reconstructed/effects`: needs the `x86-linux-capture-04/main-01ced000.bin` whole-file digest `0571c519…`; no
  prefix of a fresh guest read reproduces it (different runtime state).
- `reconstructed/model-codec`: the two corpus checks need `model-recovery/verified-v14/manifest.json` (pinned
  `fffcbad9…`); this installation scans to `27afde53…` with the same counts, also with the scanner of `e617b79`.
  The instruction comparison itself passes (4,048 synthetic cases, 0 mismatches). `evidence/model-edge/diagnostics.json`
  came from uncommitted probe code.

A Mac Wine capture (free runtime, no mugl, launcher GAME START, pre-login) matched only the record bias, template
and trig flag: the text differs from the guest's in a few bytes (22,180,556 vs 22,180,554 positions differ from the
on-disk section), the feature word is 7 (Rosetta) instead of `0x2f`. It is not a substitute for the guest captures.

## Verification skills (VERIFY-SKILLS-001, 2026-10-24)

Two project-local agent skills were generated with pstack on branch `claude/pstack-verify-skills`:

- `.claude/skills/verify-mu-native/` drives the native programs the way a user does, on a synthetic game root
  built from the `native/tests` fixtures (no installed client): `mu-client` scene flow (headless GL and a real
  window with `shot:`), `mu-world`/`mu-walk` click-to-move, run and zoom, `mu-viewer` model and terrain renders
  with GL-versus-software agreement, `mu-proto`. `features/` is the maintained map (five features, exact commands
  and the end state that proves each). Runs live in `verify-runs/<id>/` (git-ignored; `proof/` survives
  `cleanup.sh`). Proven on this Mac: every recipe in the map passed at `024e949`.
- `.claude/skills/verify-protocol-cbmc/` is the formal check of `native/core/mu_protocol.c` with CBMC 6.11.0 and
  z3 (`brew install cbmc z3`; one command, `run.sh`, about three minutes): six properties over nine harnesses,
  all holding at `024e949`. Frame parsing never reads past the available bytes (0..24); one receive drain never
  touches memory outside the 0x2000 ring and delivers consecutive, rule-shaped frames (0..12 buffered bytes);
  `mu_recv_push` refuses exactly at the ring capacity and leaves state unchanged; the packet builder stays inside
  the 0x145c object and refuses exactly past 0x145a (adds 0..20 bytes); XorData decode inverts encode and writes
  only its range. `run.sh --mutants` plants eleven mistakes in a temporary copy and all eleven are caught. No real
  bug. Not proven: multi-push streams directly (argued from R2 + R3; a direct harness did not finish), the C3/C4
  CryptoModule payload, sockets and callers, `mu_serial_next`, `native/tools/mu_proto.c`.

Environment notes: `tools/python` (venv from `tools/requirements-lock.txt`) and `cbmc` (Homebrew) were installed
for them; the Bash tool of the agent harness runs zsh, so the recipes spell every argument out. Keep the map
honest with `/pstack:maintain-verification-skill` and the harness with `/pstack:maintain-formal-verification-skill`.

## README refresh (DOCS-README-002)

README images 18–25 come from local renders; their full-size sources and a map to each README image are in
`~/Documents/mu-mac-tools/native/renders/readme-sources/` (README.txt there). New README images must be reviewed
(no account names, other players' chat or private paths) and pinned in `scripts/audit_repository.py`. When
NATIVE-SKILL-003 merges, update the "Skills 3" row and the skills section.

## Social systems, original handlers and item options (NATIVE-SOCIAL-001)

Round 1 merged in PR #147, `4420bb2`. Round 2 is on `claude/native-social2`.
Read [client-social-original.md](research/client-social-original.md), with the earlier
[HUD/trade/friend milestone](research/client-social.md). Party send/receive, shared UI/room/letter identities,
mail cache/pending/windows/drafts and complete 15-byte trade instances now drive the real GFx movies.
`mu_social_item_tables/view` resolve installed option tables; `item_options/formula/display/present` hold
bounded reconstructed consumers. Missing tables produce unavailable-details notices. Escrow, vault and
mutable instance fields retain wire data. Round 2: 29,700 C-to-original comparisons, zero mismatches,
36/36 C mutants. Round 1 retains its separate 7,000 comparisons and 10/10 mutants.
Local renders: `~/Documents/mu-mac-tools/native/renders/social/round2-{mail,compose,messenger,trade-options}-final/`.
The local `social-options.tsv` export belongs in Preview Native Data/lang; its recipe and exact original
ranges are in the finding. Remaining boundaries are transport/code pages, opaque excellent eligibility,
equipped/embedded state and uncaptured mastery patches, later stat finalizers and exact original CRT/UI.

## Item mixing and jewels, NATIVE-MIX-001

Read [client-mix.md](research/client-mix.md). `reconstructed/mix` now includes selection, score, scalar grouping,
aggregation and mix valuation. `native/core/mu_mix` feeds MixGoblinSel/MixInventoryFrame in the shared GFx layer;
`--npc-script` has mixopen/mixput/mixtake/mix/mixresult/mixadd/jewel. Replies are delayed offline snapshots,
not server-outcome predictions. Unicorn: 68,554 comparisons, zero mismatches, 17/17 mutants. Fifteen portable
and sixteen native mix regressions; native renders and reports under `~/Documents/mu-mac-tools/native/{renders,scratch}/mix/`.
Follow-up adds PersonalShopProductList/Register/Purchase and NPC/self repair with reserved identities and delayed
demo replies; task total 98,506 Unicorn comparisons, zero mismatches, 23/23 mutants. Social callback dispatch
and long script names have regressions. Next: jewel settlement, catalog routing and equipped repair. Harmony/cost D, class/option feeds, separate Chaos-weapon system and
wire replies remain open. No original client launched or owner Preview process touched.

## Repository split (REPO-SPLIT-001)

The Wine track now lives in [fryezero/mu-the-matrix-mac](https://github.com/fryezero/mu-the-matrix-mac) (local
checkout `~/Documents/mu-the-matrix-mac`); Wine-track work (app, installer, runtime, mugl/hotpatch, launcher fixes,
fast x87, player guide) goes there, native work stays here. Its history was extracted with `git filter-repo`
(121 commits), and this repository's history is unchanged; old `mac-play/` paths and issue/PR numbers still resolve
here. Changes here: `live-readers/` (objread, memread, lightread, langread, `make live-readers`, built by the local
CI instead of the Mach profilers), `native/app/icon/make-icon.swift`, the Wine-track rows/sections/findings moved out
of status, roadmap, handoff and `evidence-index.json` (a `wine_track` pointer remains), README images in
`docs/images/` pinned in `scripts/audit_repository.py`. Live tests of the original client still use the Mac app's
runtime and `~/Documents/mu-mac-tools/mu-autologin.sh` under the game lock.

## README refresh, 2026-10-20

The main README now separates playable Wine support and its measured 25 FPS optimization
work from the native offline reconstruction. It reuses six existing comparison captures
in `docs/media/`, unchanged, with provenance and a hash-pinned audit exception. It records
the zoomed-out boss-fight and runtime-distribution limits rather than promising 25 FPS
in every situation. No game runtime or recovery behavior changed in this documentation task.

Read `status.md`, then choose a task from `roadmap.md`. Gameplay recovery needs runtime evidence. The user no longer has a Windows PC available, so do not make access to one a prerequisite for the next task. The full x86 Linux/Wine guest on this Mac has now restored readable client code; start with `research/restored-client-text.md` and `../runtime-linux/README.md`.

## World fidelity tour (NATIVE-FIDELITY-002)

`scripts/fidelity_tour.py run MANIFEST` renders every map of a live capture set with `mu-world --fidelity-dump` and
writes side-by-side/diff images and a scoreboard (camera, image stats, object field differences, light grids).
The 2026-10-22 captures (13 maps) and their decoded placements are local under `~/Documents/mu-mac-tools/native/`
(`scratch/fidelity2/live/`, `renders/fidelity2/`). Fixes landed: Icarus terrain skip (#149), per-world object
creation/move cases (#151), Icarus rising cloud puffs (#153). Live reads used: objread/lightread per map, memread of the
effect pool and terrain globals, a `mugl` GL trace and a `mugl` on/off A/B (settings restored). Next: the gaps ranked
in [client-world-fidelity.md](research/client-world-fidelity.md#4-gaps-ranked-by-visibility); report the Tarkan shading
difference that depends on `mugl` to the Wine track.
## Experience, levels and stat points (NATIVE-PROGRESS-001)

Read [`research/client-progression.md`](research/client-progression.md). `reconstructed/progress` holds the class
formulas, the experience table and bar, the progression answers, the "+" buttons and the speed row; compare with
`tools/python/bin/python scripts/validate_progress.py --cases 500 --mutations` (main checkout's Python, about 50 s;
reports in `~/Documents/mu-mac-tools/native/scratch/progress/`). `native/core/mu_progress` is the session with the
demo server; mu-world/mu-walk/mu-client take `--progress`, `--progress-class/-level/-points/-rate` and
`--progress-script "F:kill:CLASS F:add:STAT F:button:ROW"`; with `--gfx` the bar, the character rows and the "+"
buttons follow it (`world_gfx_progress`), with `--combat` kills feed it and the level up draws its flares and ground.
Renders stay local (`~/Documents/mu-mac-tools/native/renders/progress/`). Next: CalculateAll's equipment options
(slot 4/8) and the master tree, the window's value builder `0x00b40661`, the third-class joints `0x7f78`
0x2d/0x2e, the join packet `0x0124cc64`.

Options, menu and respawn (second PR): `reconstructed/progress/progress_options.c` (winOption, family `options`) and
`mu_prg_recv_respawn` (family `respawn`); the host is `native/world/world_gfx_options.{c,h}` (settings file
`~/Library/Application Support/MuTheMatrixNative/option.ini`, `MU_NATIVE_SETTINGS_DIR` for tests; the mapping table is
in the research note §8). mu-world's `--progress-script` takes `key:VK`, `click:X*10000+Y`, `menu:N`, `volume:N`,
`monster:N` for headless window checks and `--travel-script F:respawn` for the respawn answer; mu-client takes
`esc` and `click:X,Y` to the GFx layer first in the world. The combat demo's death calls `combat_respawned` (main.c):
`mu_map_respawn` (DEMO town gates) + `mu_progress_respawn`. Next: the options save request `0x0182ff32`, a consumer
for the Effect limitation, the respawn tail after `0x0127c048`.

## Move snapshot compatibility (NATIVE-MAP-002)

The 298 failures come from skill2's lang5, not the distinct quest2/lang5 named in the brief. All three
snapshots have identical 69 real move records. The missing-key default has nonzero sort fields only in
skill2; `Tables.lookup` now supplies its captured record to C. Read
[client-maps.md](research/client-maps.md#move-default-records-native-map-002) for digests, addresses and
the five-family failure breakdown. Private reports/logs: `renders/map2/` and `scratch/map2/` under
`~/Documents/mu-mac-tools/native/`. Native offline rows agree across all captures and three sort orders;
private map travel passes. Lang4 and both lang5 copies each pass 5,001 instruction cases with zero mismatches
and all 10 planted mistakes detected. Portable map tests: 11 pass; native map tests: 9 pass. No game session
was opened. Party markers and mixing remain outside this change.

## Quest follow-ups and later skill inputs (NATIVE-POLISH-001)

F6 56/7B dispatch to the existing walk path through `mu_quest_resume_path`; world reload retains an armed
destination/mode. The synthetic quest-travel host executes guide request → reload at an entrance short of the
goal → delayed answer → remaining movement. NPC 257 creates one flare 42, emits flare 41, and contributes
terrain light after the frame-light copy. Owner death removes the persistent joint and its light.
`validate_quest_polish.py --cases 2000 --mutations`: 2,000 answer cases + one actual tab constructor, zero
mismatches, 2/2 mutants caught. `validate_joints.py --cases 1800`: 5,400 cases across all kinds, 90 per new
subtype per family, all equal; all nine negative controls distinguish a wrong result. Reports and native
renders stay in `~/Documents/mu-mac-tools/native/renders/polish/` (`quest-npc/`, `npc257/`).

The pinned MyQuestInfo constructor inserts only keys 0–4: no event-map tab was added. Run
`probe_later_skills.py --snapshot scratch/skill2/live/lang5.bin` with the pinned text/data: every fourth-tree
node lookup lacks a nested allocation; 282 fifth-table lookups pass, but the original manager getter stops
on undefined `0x01d22c04`. Read [client-skills.md](research/client-skills.md#11-later-tree-input-probes-native-polish-001)
for exact boundaries and next capture needs. These are partial input findings, not completed later trees.
Alternate-grid shock rings and Muun were not extended. No original client was launched or existing Preview killed.
Failed destination loads cancel the pending resume and armed path; a missing-map regression verifies no
movement in the old world. The initial newer-snapshot map failures were independently reproduced on the
pre-polish `62be84d` archive: the same 298/5,001. Original-input map validation remains green.

## Map follow-ups (NATIVE-POLISH-001)

`shell.c` mirrors the current walk world into scene globals and remembers each character's demo join location.
MoveCommand uses alignment 10 from the executed registry slice `0x00ac66f8..0x00ac6722`. The loaded actors supply
NPC E7 records through `mu_map_add_npc`; the demo retains them across Tab requests and clears them on map reload.
`validate_map_polish.py --cases 500 --mutations` compares 875 bounded teleport checks and one registry call,
zero mismatches, 3/3 mutants caught. `validate_gfx3.py --cases 20 --mutations` includes 60 window cases.
Reports and renders: `~/Documents/mu-mac-tools/native/renders/polish/`. Read the new section of
[client-maps.md](research/client-maps.md#native-polish-001-map-follow-ups) for exact execution boundaries and the
navimap locale blocker. Party markers remain owned by NATIVE-SOCIAL-001.

## Maps and travel (NATIVE-MAP-001)

Read [`research/client-maps.md`](research/client-maps.md). `reconstructed/map` (overlay, Move window, gates; compare
with `tools/python/bin/python scripts/validate_map.py --snapshot "$SNAP" --cases 500 --mutations`, `SNAP` = the
langread `lang4.bin`, about 3 min); `core/mu_map` (session + demo server). **Travel API for quests** (NATIVE-QUEST-002's
"Go Now"): `mu_map_travel_to(session, world, x, y)` or `mu_map_travel_move(session, key)` on the app's `mapsess`; the
world changes on the next frame (`mu_map_take_teleport` in `advance()`). mu-world/mu-walk/mu-client:
`--travel-script`, `--no-map`; with `--gfx` Tab shows hudMap and M the Move window (the movie dir needs
`NaviMap/` from `gfxconvert.py`). Renders/captures stay local in `~/Documents/mu-mac-tools/native/renders/map/`
(`live/`, `gfx/`, `gfx-travel/`, `walk/`).

**Next.** NPC markers from the placement (the server's 0xE7 records), the Move window's client position,
the event world map (0x73), mu-client's scene world after a travel, a live 0xE7 capture to compare marker names.

## Fourth skill tree (NATIVE-SKILL-003)

Read section 12 of [`research/client-skills.md`](research/client-skills.md). Capture: `langread PID out.bin
nested:0x6d8 graph:0x06fbb8ec=0x44,10,0 graph:0x06fbb930=0x80,8,0 graph:0x06fbbaec=0x4c,8,0` (local snapshots in
`~/Documents/mu-mac-tools/native/scratch/skill3/live/`); `live_lang_to_plain.py` writes `tree4.tsv`,
`tree4_tips.tsv`, `tree4_side.tsv` for `MU_LANG_DIR`. Validate with `validate_skill_later.py --snapshot
s2_tree4.bin --cases 300 --mutations` (main checkout's Python; fast mode drops per-read hooks, `--strict` keeps
them). Run one process per family (`--families X`, mutants with `--mutations --mutants-only`) in parallel: about
8 minutes for 6,510 cases and the 10 mutants. Stub addresses must be allocated once per machine: every new stub
address adds a Unicorn code hook, and case time then grows with the case count. Renders: `~/Documents/mu-mac-tools/native/renders/skill3/`. Next: the side stat panel `0x00c26ed3`,
SetClassName/SetExp, 7E 07, then the fifth tree from `s3_tree5.bin` (section 12 lists its entry points).

## Skill state, usability and Master tree (NATIVE-SKILL-002)

Read sections 8..10 of [`research/client-skills.md`](research/client-skills.md). `skill_list.c`, `skill_canuse.c`
and `master_tree.c` run under `validate_skill_server.py` / `validate_skill_tree.py --snapshot "$SNAP" --cases 500
--mutations`: 4,508 + 7,876 cases, 0 mismatches, 9/9 mutants caught. Use the main checkout's `tools/python/bin/python`
for Unicorn; the portable venv lacks it. Pinned captures are in that checkout's ignored evidence directory;
`SNAP=~/Documents/mu-mac-tools/native/scratch/skill2/live/lang5.bin`. Scalar CRT `strstr` is selected, and families
clear their client stubs. Native `core/mu_skill` owns tree state; `world_gfx_tree.c` plays A / character buttons,
icons, tooltips and click-twice demo confirmation. `skills_class.tsv` supplies class maps; Imprint boots on the
authored 1024x768 stage then receives SetWindowSize. Reports/renders: local `scratch/skill2/`, `renders/skill2/`.
Next: nested live reads and validated parsers/managers for the 4th/5th Lang tables; FormulaData and authoritative
equipment/buff/event/pentagram feeds. The optional 4th/5th movies stay empty and explain the missing data.

## Skills: bar, tooltip, Skill Imprint window (NATIVE-SKILL-001)

Read [`research/client-skills.md`](research/client-skills.md). `reconstructed/skill` holds the Skill(Kor) row parser,
the bar feed, delays, the stat/mana checks, the icon draw and the tooltip builder; compare with
`tools/python/bin/python scripts/validate_skill.py --snapshot "$SNAP" --mutations` (Unicorn, about 6 min; `SNAP` =
the langread `lang3.bin`). `core/mu_skill` is the native game side (needs `skills_ext.tsv`: rerun
`scripts/live_lang_to_plain.py` on the snapshot), the GFx layer's skill host plays SkillInfoPopup/SkillStampFrame,
`world/world_gfx_skill.c` draws the window icons. Renders and live captures stay local
(`~/Documents/mu-mac-tools/native/renders/skill/`). Next: the stamp manager's entries and imprints (server data),
the usability check's weapon/buff/world branches, a live read of the skill records' class maps (+0x6c) for the
class lists, MasterSkillTree / SkillTree4th/5th, the window's open position.

## Character creation, deletion and the menu (NATIVE-CHARCREATE-001)

Read section 11 of [`research/client-character-select.md`](research/client-character-select.md). `reconstructed/charsel/charcreate.c`
is the create panel, the delete flow and winSystemMenu's game side (compare with `scripts/validate_charcreate.py --cases 300
--mutations`, about a minute, Unicorn; `--emit-poses` prints the NewFace pose table). `native/charsel/charsel_create_gfx.c` plays it
in mu-client/mu-shell `--gfx` (CharacterSelect, Caution.swf, winSystemMenu.swf; convert them with `gfxconvert.py --bridge`), the
name tables come from `scripts/live_lang_filters.py` (filter.txt, filtername.txt in `MU_LANG_DIR`). OFFLINE DEMO answers: a local
store (`--store FILE`, the window defaults to `~/Library/Application Support/MuTheMatrixNative/offline-characters.txt`). Renders
stay local (`~/Documents/mu-mac-tools/native/renders/charcreate/`). Next: a live capture of the panel (bust placement), the
Caution window's own queue/display code in Unicorn, the Option window (winOption), the rename mode if a server uses it.

## Character-select picking and GFx list (NATIVE-CHARSEL-003)

Read section 10 of [`research/client-character-select.md`](research/client-character-select.md). `reconstructed/charsel/charsel_gfx.c`
is the CharacterSelect movie's game side (compare with `scripts/validate_charsel_gfx.py --cases 300 --mutations`, about
20 s, Unicorn); `native/charsel/charsel_list_gfx.c` plays the movie in mu-client/mu-shell (`--gfx DIR`, `--gfx-log`);
`mu_charsel_pick` runs NATIVE-NPC-001's `mu_npc_pick` for scene 5; `skill_fx.c` and `mu_particles` carry the star dragon 0x5ac/0x5ad. Renders stay
local (`~/Documents/mu-mac-tools/native/renders/charsel3/`; JPEXS output and the probe in `scratch/charsel3/`). Next: the create-character panel (offline: local
characters) and the GFx menu; class-name codes 9/10.
- NATIVE-PERF-002: integrated timings, matching render hashes and the remaining 80-player/pacing shortfall are in [the handoff](handoffs/NATIVE-PERF-002.md).
- NATIVE-PERF-003: [measurements, exact full-frame comparisons and remaining 80-player target](handoffs/NATIVE-PERF-003.md). Final real-time comparisons and full Metal intervals are recorded; strict 25 Hz work/pacing acceptance remains open. AS2 wall time is pinned only for image comparisons.

## Native frame time and window (NATIVE-PERF-001)

Read [`research/native-performance.md`](research/native-performance.md). Profile with `mu-client ... --auto --hold
SCENE --seconds S --perf FILE` (window) or `--headless --frames N --perf FILE` and `native/tools/perf_report.py`;
`MU_PERF_BASELINE=1` runs the pre-milestone paths for before/after on the same binary. The 2D layer's GPU replay is
`native/viewer/ui_gl.c` (keep it in step with `core/mu_ui_raster.c`), batching `native/viewer/gl_batch.c` (a session
must not interleave with direct GL calls; `MU_NO_GL_BATCH=1`), the cap's sleep `mu_sleep_ms` in `core/mu_perf.c`,
resizing `mu_shell_resize` and `apply_resize` in `client/main.c`. Checks: `native/tests/test_native_perf.py`
(`perf_gl_host.c`), `native/tools/imgdiff.py` for captures. Profiles, matrices and resize captures stay local
(`~/Documents/mu-mac-tools/native/renders/perf/`). Next: a per-object pose cache, the GFx layer's per-frame cost,
a run on a Retina display.

## Native preview app (NATIVE-APP-001)

Read [`research/native-preview-app.md`](research/native-preview-app.md). `native/app` builds
`Mu The Matrix Native Preview.app` (`make -C native preview-app`; `make -C native/app install` copies it to
`~/Applications` and runs its `--setup`). The launcher is `native/app/Sources/{PreviewCore,main}.swift`, the network
guard `native/app/nonet/mu_nonet.c`, the dylib bundling `native/app/bundle-dylibs.sh`. libmugfx comes from this
checkout's `native/gfx/build-mugfx.sh` (or `MUGFX_LIB=`); its Ruffle build needs Java (`JAVA_HOME`, e.g. the JDK under
`MU_GFX_DEPS`). Checks: `native/tests/test_native_app.py` (private smoke with `MU_RECOVERY_INTEGRATION=1
MU_GAME_ROOT=...`). Window screenshots stay local (`~/Documents/mu-mac-tools/native/renders/app/`). A launch from
Finder that copies from `~/Documents` triggers macOS's Documents consent prompt; `make install` avoids it by preparing
Native Data from the shell. New milestones that add mu-client options should add them to `LaunchPlan.make` and the
settings window. Next: a resizable/full-screen window and an in-app "demo tour" (the `--auto` flow in the window).

## Character-select scene at runtime (NATIVE-CHARSEL-002)

Read section 9 of [`research/client-character-select.md`](research/client-character-select.md).
`reconstructed/objects/charsel_world.c` (CGMCharacterScene_Ex) runs in the object lifecycle for world 0x5d;
`mu_charsel_attach_objects` and the session's particle module give `mu-charsel`, `mu-charsel-window` and `mu-client`
the scene's sprites, particles and shadows. Compare with `scripts/validate_charsel_world.py --cases 2000 --mutations`
(about 25 s) and `validate_particles.py` (extended); live snapshots and screenshots are local
(`~/Documents/mu-mac-tools/native/scratch/charsel2/live/`, `renders/charsel2/`, `render.sh`/`sheets.py`;
`mu-charsel --objects-out` for the per-object comparison). Next: the stardr01 effect `0x5ac` (CreateEffect
`0x013f41b4` and its child `0x5ad`), the scene-5 character pick, the GFx character list.

## Guide, class upgrades and tracker, NATIVE-QUEST-002

`reconstructed/quest/quest_{guide,classic,summary,move,wrap}.c` and `scripts/validate_quest2.py` implement and
compare 7,004 cases with zero mismatches and 5/5 planted mistakes caught. Each family owns its emulator stubs. MyQuestInfo tabs 0/1, winQuestSummary,
QuestProgressInfo and NpcJobChangeQuest are wired in `world_gfx` for mu-world and mu-client. The map travel API
handles cross-map Go Now. NPC 257 uses the extracted Player +13 set 24 and 12:3 wing at scale 1.0; class mentor
229 exercises the class window. Local tables add guidequest/guidestrings/dialoganswers TSVs. Demo rows/verbs and
remaining limits are in [client-quests.md](research/client-quests.md#8-guide-class-upgrades-tracker-and-go-now-native-quest-002).
Reports/renders: `~/Documents/mu-mac-tools/native/renders/quest2/`. The Preview app must carry the three added
local tables. Chapter abort uses the offline demo's accept fallback. Next: event-map tab, auto-move answers,
real server rewards and NPC 257's recorded cosmetic joint.

## Quests (NATIVE-QUEST-001)

Read [`research/client-quests.md`](research/client-quests.md). `reconstructed/quest` (libquest) is the client side: the
quest system, the F6 handlers, the texts and NpcQuestProgress/npcdialogue-list/MyQuestInfo; every client effect is a log
line delivered to a sink as it happens. Compare with `tools/python/bin/python scripts/validate_quest.py --snapshot
LOCAL/lang4.bin --mutations` (about 2 min; the snapshot needs `langread ... node:0x137c=0x118 map:0x1ec2e60+...`, see the
finding). `native/core/mu_quest` runs it with a demo server; `world_gfx` drives the movies (convert `NpcQuestProgress
MyQuestInfo`), T opens MyQuestInfo, demo rows `dialog`/`quest` in `world/lorencia-demo-npc.txt`. Checks:
`reconstructed/quest/test_quest.py`, `native/tests/test_native_quest.py`. Renders local
(`~/Documents/mu-mac-tools/native/renders/quest/`). Next: the guide quest tab (read GuideQuest), the quest summary HUD,
the move-to-target button, class-upgrade quests (Quest.bmd, NpcJobChangeQuest).

## Talking to NPCs (NATIVE-NPC-001)

Read [`research/client-npc-interaction.md`](research/client-npc-interaction.md). `reconstructed/npc` (libnpc) holds the
talk-result dispatch, the character pick and the box table; `native/core/mu_npc.*` runs the talk in mu-world/mu-walk
(`--npc`, `--npc-demo native/world/lorencia-demo-npc.txt`, `--npc-script`); the GFx layer plays NpcDialogue, NpcShop and
StorageInven (convert them next to the HUD set). Compare with `tools/python/bin/python scripts/validate_npc.py
--mutations` (about 40 s; `--emit-box` regenerates the box table). Checks: `reconstructed/npc/test_npc.py`,
`native/tests/test_native_npc.py`. Renders stay local (`~/Documents/mu-mac-tools/native/renders/npc/`). The
multi-item `--combat-script` bug NATIVE-LANG-001 reported is fixed (items split at spaces/commas; unknown actors are
reported). Next: read the NPC dialogue text table (NPCDialogue.bmd's text ids, another Lang.mpr table) and the shop
list packet's item records with the live-read route; the talk case's special classes; the quest windows
(NpcJobChangeQuest uses Dialog(kor)); the client's item price routine for the shop.

## Overhead names, HP boxes, chat bubbles (NATIVE-NAMES-001)

Read [`research/client-overhead-text.md`](research/client-overhead-text.md). `reconstructed/names` is hudPlayerName's game
handler; `native/core/mu_names.*` runs it with a model of the movie, `mu_world_names.*` feeds it from mu-world (hero,
monsters, demo HP, SetPlayerDie removal, hover, chat), `world/world_names_gfx.c` drives the real movie with `--gfx`,
`core/mu_label.*` is the shared label helper (the stand-in; NATIVE-ITEMS-001's item labels use its glyph path). Compare with
`scripts/validate_names.py --cases 1000 --negative 100` (about one minute, needs Unicorn). Monster names/heights come from
`mu_lang` (Npcname, `MU_LANG_DIR`); renders stay local (`~/Documents/mu-mac-tools/native/renders/names/`).
Next: player stores/castle marks/other players, a live capture of a
monster box and a bubble.

## Joints, world-object effects, login particles (NATIVE-JOINT-001)

Read [`research/client-joints.md`](research/client-joints.md) (section 5 is the per-world survey of particle, joint
and effect creators). `reconstructed/joints` (libclient_joints) is the single joint implementation (`skill_fx`
wraps it); `native/core/mu_joints.*` runs it for `mu_combat` and for the world objects in `mu_particles` (which also
keeps their effects: the Tormenta tornado). Compare with `scripts/validate_joints.py --cases 3000` (about 2 min),
`validate_skill_fx.py` and `validate_particles.py` (both extended). Renders are local
(`~/Documents/mu-mac-tools/native/renders/joints/`, `render.sh`/`sheets.py`). `mu-world --joint-demo SUB` shows a
lightning subtype anywhere. Next: MoveObject's kinds of the other worlds once their object lists are decoded, the
character-select scene's object lifecycle and kinds, Inferno's burst, RenderObject's effect draw executed.
## Lang.mpr tables (NATIVE-LANG-001)

Read [`research/client-lang-tables.md`](research/client-lang-tables.md). `langread` (live-readers/) reads the
tables the client built from Lang.mpr out of a running client, under the game lock, at the server list. The
plaintext goes through `scripts/live_lang_to_plain.py` to `~/Documents/mu-mac-tools/native/scratch/lang/` (local),
and `MU_LANG_DIR` enables it in mu-world, mu-client, mu-walk, mu-charsel, mu-render and the shell.

Compare with `scripts/validate_lang.py --snapshot LOCAL/lang3.bin --mutations` (Unicorn, about 15 s);
`--write-maps` regenerates `native/core/mu_lang_maps.h`. A client update moves the addresses: repeat the read.

Next:

- read more tables through their consumers (SkillRequire, Slide, BuffEffect, the quest strings);
- map the character window's SetName and skill-tooltip GlobalText numbers;
- port GetSkillDistance's bonuses.

## More Lang tables, NPC dialogue text, item prices (NATIVE-LANG-002)

Read sections "NATIVE-LANG-002" of [`research/client-lang-tables.md`](research/client-lang-tables.md) (with the survey of
all 74 tables). The snapshot `lang3.bin` was enough (no new live read). New plaintext files next to the old ones
(`buffs.tsv`, `charinfo.tsv`, `skillreq.tsv`, `soulconv.tsv`, `questtext.txt`; the old names and formats are unchanged).
The NPC dialogue comes from NPCDialogue.bmd + QuestWords.bmd (`reconstructed/npc/npc_dialogue.c`), prices from
`reconstructed/price` (ItemValue, ConvertRepairGold). Compare with `scripts/validate_lang.py --snapshot lang3.bin
--mutations` (about 40 s), `scripts/validate_npc_dialogue.py --mutations` (about 8 s) and `scripts/validate_item_price.py
--mutations` (about 5 min). Renders stay local (`~/Documents/mu-mac-tools/native/renders/lang2/`). Next: the skill tooltip
body (SkillTooltipText.bmd through `0x00c1ef6b`), the character window's values (SetCharacterInfo), the shop list packet,
ItemTRSData from Lang.mpr against the local itemtrsdata.bmd, the quest windows over MUQuestString/QuestProgress.

## Particles, sprites and blob shadows (NATIVE-PARTICLE-001)

Read [`research/client-particles.md`](research/client-particles.md). `reconstructed/particles` (libclient_particles)
ports the legacy particle list, RenderSprite, the sprite list, RenderBodyShadow, the bone helpers and
RenderObjectVisual for Lorencia/Tormenta; `native/core/mu_particles.*` runs it in mu-world through hooks into the
object runtime, the environment and `mu_combat` (`--no-particles` restores the stand-ins). Compare with
`scripts/validate_particles.py --cases 3000 --heavy-cases 300` (about 50 s). Renders stay local
(`~/Documents/mu-mac-tools/native/renders/particles/`, scripts `render.sh`/`all.sh` there). Other callers create
particles through `mu_world_particles_create`/`_sprite` (supported kinds: `mu_pt_kind_supported`). Next: the login
scene's Shiny02/flare01 sprites through the module and its clouds/WATERFALL1 kinds, the Tormenta joints 0x7f7d
(joint pool) and effect 0x40e, more particle kinds as callers need them, the character shadow's flag conditions
(`+3`, `+0x44`, the option singleton) from RenderCharacter.

## Model lighting (NATIVE-LIGHT-001)

Read [`research/client-model-light.md`](research/client-model-light.md). Game scenes take `mu_model_scene_params`
(light override 1, as read live); static objects pose with RenderObject's arguments from `mu_obj_render`'s log (scale in
the bones); monsters/NPCs get the frame light + 0.2. Check with `native/tests/test_native_light.py` and, privately,
`scripts/validate_model_light.py --world 94|0 --objects LOCAL/EncTerrain<n>.plain --live SNAPSHOT` (snapshots from
`live-readers/lightread`, local under `~/Documents/mu-mac-tools/native/scratch/light/live/dumps/`; renders in
`renders/light/`). Next: the hero's (1, 1, 1) branch of RenderCharacter, the ambient creatures' body light, and a lit
check of the HUD item models of NATIVE-GFX-003 (`native/world/world_gfx_game.c`).

## Login scene (NATIVE-LOGIN-001)

Read [`research/client-login-scene.md`](research/client-login-scene.md). `mu_scenemgr_login_render_3d` /
`mu_scenemgr_login_tick_head` (reconstructed/scene), `reconstructed/objects/login_world.c` (CGMLogInScene_Ex) and
`native/core/mu_login` + `native/login/login_gl.c` draw World95 behind the login overlay in `mu-client`
(`--login-objects DIR` with the local `EncTerrain95.plain`) and `mu-render ui login|servers --scene`. Compare with
`scripts/validate_scene.py --only login_render login_tick_head` and `scripts/validate_login_world.py --cases 2000
--mutations` (about 30 s); live snapshots and screenshots are local (`~/Documents/mu-mac-tools/native/scratch/login/live/`,
`renders/login/`). `objread` takes an optional globals output. Next: the sprite and particle systems (CreateSprite
`0x01692eb7`, CreateParticle `0x0168fafd`, RenderSprites/RenderParticles), the vertex-light inputs behind the sky/ship
brightness difference, and the exact command of the 1280×800 pale-terrain report (not reproduced here).
## Combat effects (NATIVE-COMBAT-002)

Read section 8 of [`research/client-combat.md`](research/client-combat.md). `reconstructed/combat/skill_fx.*` ports the
older effect system (effects, particles, joints) and the hero's hit/death voices; `mu-world --combat` draws skills
through it (keys 1..9, 0; `--hero-hp`). Compare with `scripts/validate_skill_fx.py --cases 3000` (about 35 s). Renders
stay local (`~/Documents/mu-mac-tools/native/renders/combat2/`, script `native/scratch/combat2/render_all.sh`). Next:
CreateSprite `0x01692eb7`, the swirl's smoke/spark particles and `0x7fd5` joints, Inferno's burst `0x013c07f4`,
monster hurt/death sounds (model sound slots), RenderObject's effect draw executed, a live fight capture outside a PvP
area.

## Combat (NATIVE-COMBAT-001)

Read [`research/client-combat.md`](research/client-combat.md). `reconstructed/combat` (libcombat), `native/core/mu_combat.*`
and `mu-world`/`mu-walk --combat` (`--combat-weapon`, `--combat-script`, keys 1..6) fight demo-placed monsters with the
client's attack rules, damage text and hit/death reactions; the server side is a labelled demo. Compare with the client
with `scripts/validate_combat.py --cases 3000 --heavy-cases 300` (about 50 s; report under `evidence/native-combat/`);
`scripts/combat_static.py` regenerates `attack_speed_table.h`. Renders stay local
(`~/Documents/mu-mac-tools/native/renders/combat/`, scenario script in `native/scratch/combat/render_all.sh`). Next: reduce
MoveEffect for arrows and MODEL_FIRE and RenderEffects' draw states, MoveCharacter's area-skill switch (Evil Spirit,
Twisting Slash, Inferno) and the per-step attack routine `0x013966ea`, the Player hit/death actions, and a short live fight
capture to compare timings.

## World character render (NATIVE-RENDERCHAR-001)

Read [`research/client-renderchar.md`](research/client-renderchar.md). `reconstructed/renderchar` (librenderchar),
`native/core/mu_renderchar.*` and `mu-render character|actor --world-render` draw the client's world passes. Compare with the
client with `scripts/validate_renderchar.py` (sections items, kinds, back, character, linkbones; the full run takes
about 40 minutes and regenerates `special_types.h`, `back_matrices.h`, `link_bones.h`). Renders stay local
(`~/Documents/mu-mac-tools/native/renders/renderchar/`). Next: the EnchantEffect colour table (runtime data), the
type-specific item branches (wings first), RenderBodyShadow `0x012bc07a`, and the monster body RenderObject `0x016d4fe4`.

## Actors (NATIVE-ACTOR-001)

Read [`research/client-actors.md`](research/client-actors.md). `reconstructed/actors` (libactors), `native/core/mu_actor.*`
and `mu-render actor --type/--monster/--npc` render animated monsters and NPCs; `mu-render character --pose` animates
players. Compare with the client by running `scripts/validate_actors.py` (pinned text and data; about 17 s); it
also regenerates the extracted class, NPC and Player-speed headers. `scripts/actor_static.py` regenerates the monster
action table. Renders stay local (`~/Documents/mu-mac-tools/native/renders/actors/`). Next: trace the monster
weapon/attachment render path in RenderCharacter `0x01363260`, load item attribute data for exact player weapon
actions, and drive the world-specific map processors with their singleton state.

## Native terrain (NATIVE-TERRAIN-001)

Read [`research/client-terrain.md`](research/client-terrain.md). `reconstructed/terrain`, `native/core/mu_terrain.*`,
`build/mu-terrain` and `mu-viewer --terrain` load and draw any world from `MU_GAME_ROOT`. Compare with the client by
running `scripts/validate_terrain.py` (pinned text, data and dispatch flag; `--game-root` adds the installed files
and `--installed-worlds 1,143 --installed-tiles 0` checks every tile). Renders and reports stay local. Next: decode
or capture the object placement (the `.obj` files do not decode with `0x0098c5f2`; a runtime capture of the
loader's output buffer would avoid the protection layer), then draw `Object<n>\` models through the model path.
Dynamic lights, world tiles, frustum, decals and the 24-bit height choice are done (NATIVE-TERRAIN-002,
[`research/client-terrain-frame.md`](research/client-terrain-frame.md); `--scale-002` scales its checks).

## Static objects (NATIVE-OBJECTS-001)

Read [`research/client-objects.md`](research/client-objects.md). `reconstructed/objects`, `native/core/mu_objects.*`,
`mu-terrain objects|render --objects` and `mu-viewer --terrain --objects` implement the `.obj` loader, record layout
and object model table; `scripts/validate_objects.py` compares them with the client. The installed `.obj` files are
refused by the client's own loader instructions (transformation past the protection boundary). The placements of
World1/94/95/142 were read live from the object list of a client we started (`live-readers/objread`,
`scripts/live_objects_to_plain.py`, finding section 6); the plaintexts stay local and load through
`mu-world`/`mu-charsel --objects-dir` and `--objects FILE`. Next: other worlds (a character already standing
there, under the game lock), object lighting and animation.

## World objects at runtime (NATIVE-OBJECTS-002)

Read [`research/client-objects-render.md`](research/client-objects-render.md). `reconstructed/objects/object_render.{h,c}`
holds CreateObject, the move pass (MoveObjects, MoveObject, CreateFire) and the render pass (RenderObjects, RenderObject,
body light, RequestTerrainLight) for Lorencia and Tormenta Island; `native/core/mu_objects_runtime.c` runs them in
`mu-world`/`mu-walk` and `mu-terrain render --object-steps N`. Compare with `scripts/validate_object_render.py --cases
2000 --mutations` (Unicorn Python, pinned text and data; about 30 s) and with live snapshots via
`scripts/live_object_state.py` (`--primary-light` from `mu-terrain export`, `--pair A B` for the frame advance,
`--velocity-out` for the Tormenta speed sidecar). Snapshots, sidecars and renders stay local
(`~/Documents/mu-mac-tools/native/scratch/objects3/`, `renders/objects3/`). Render at 1600x1000: the default
1280x800 headless size shows a pre-existing terrain artefact. Next: the legacy particle system (CreateParticle
`0x0168fafd`), RenderObjectVisual `0x017f9758` with bone positions, other worlds' object cases, and a Tormenta re-read
with Nighty selected.

## Auto move and walk/run rules (NATIVE-PATH-002)

Read sections 4 and 5 and the identity block of [`research/client-path.md`](research/client-path.md).
`mu_path_long`/`mu_auto_path_*` (reconstructed/path) and `mu_player_run_counter`, the predicates and
`mu_move_speed_input_from` (reconstructed/movement) drive `mu_walk`, `mu_walker`, `mu-path --long --class --boots`
and `mu-world --boots L --auto-move X,Y` (S + click in the window). Compare with
`scripts/validate_path.py --cases 1000 --mutations --worlds all` (about 20 minutes; `--only long,auto,run,speed_state,predicates`
for the new families). The neighbour table now comes from `evidence/path-table-live-01` (manifest, `memread`).
Renders stay local (`~/Documents/mu-mac-tools/native/renders/path2/`). Next: trace MoveHero's auto-move gates
(option byte `0x0bdc5981`, the helper check, cancel byte `0x0bdc599c`, flag 3) and the arrival handler's actions,
give the hero real gear from the character list (boots level, buffs, pets) once equipment decoding exists, and time a
live walk/run against the native one.

## Click-to-move (NATIVE-PATH-001)

Read [`research/client-path.md`](research/client-path.md). `reconstructed/path`, `native/core/mu_path.*` and
`build/mu-path` find, follow and render click-to-move paths on any world's attribute map. Compare with the client by
running `scripts/validate_path.py --cases 1000 --mutations --worlds all` (needs `MU_CLIENT_TEXT`, `MU_IMAGE_DATA`,
`MU_TRIG_FLAG`, `MU_PATH_DIRECTIONS` and `MU_GAME_ROOT`; about 3 minutes). Renders stay local
(`~/Documents/mu-mac-tools/native/renders/path/`). The native-world window can adopt `mu_pathing`/`mu_walker` in place
of its straight-line walk. `mu_walk` now uses this finder; the world branch's own port was removed in the reconciliation (finding). The
listed next steps (neighbour table, speed and run-counter predicates, long-distance helper) are done in NATIVE-PATH-002.

## Prepared Windows capture path

Review and validate `windows-capture/capture-client.c` on Windows x64 against the pinned client. The helper identifies `main.exe` by SHA-256, opens the process for query/read access, and saves executable image regions from main.exe, IGC.dll and RGS.dll. It leaves the process running and writes a manifest with region digests and limitations. Build/smoke success under Wine does not prove native game capture.

Keep the capture local. Validate every file against `capture.json` before importing bytes into analysis. Live reads are not an atomic snapshot. Private executable allocations outside the selected image regions are not captured. Establish actual code restoration and build identity before declaring an unpacked program.

## Existing local artifacts

On the original workstation the lab directory is `main-exe-study`. Its ignored paths retain:

- `input/main.exe`: exact original analysis copy.
- `evidence/loader-recovery/recovery.json`: compression chunk mappings and identities.
- `evidence/loader-recovery/themida-decoded.bin`: 41,984,000-byte protector layer.
- `evidence/loader-recovery/emulation-04/`: corrected STOP-at-import trace and overlays.
- `evidence/rea-*.json`: full REA outputs, including failures and limitations.
- `asset-recovery/verified-v2/`: image scan manifest and selected exports.
- `model-recovery/verified-encrypted-v2/`: corrected complete model scan and selected exports.
- `runtime/`: isolated client copy and startup logs.

A GitHub clone contains source and reviewed summaries, not these artifacts. Reacquire private inputs or work on independent format/tests tasks when the lab data is unavailable.

## Traps already investigated

- The first unpacked layer is still the protector. Its matching size/hash does not establish gameplay recovery.
- Default Ghidra whole-region analysis exhausted a 2 GiB heap. A 4 GiB profile with two analyzers disabled completed, but returned short obfuscated call wrappers.
- An early emulator run treated unresolved IAT values as callable addresses and fell into zero data. Emulation-04 corrected this with STOP-only traps. The earlier run is not decryption evidence.
- V15 model payloads can leave a full sixteen-byte alignment trailer. Preserve it, retain block alignment, and validate the complete model structure.
- The original Mac filesystem is case-insensitive. Use file identity to deduplicate selected aliases such as Player.bmd/player.bmd.
- GitHub counts are not game-recovery percentages. Track proof for functions and behaviors, not a speculative overall completion number.

## End a work session

Record the branch/issue, change, input digest, decisive addresses/offsets, checks run, ignored artifact locations and next action. Update only the relevant findings, `status.md` and this handoff. Keep credentials, proprietary payloads and process dumps out of the repository.

## Original lab versus GitHub checkout

The original lab retains an archival local `lab/bootstrap` branch. The published
GitHub `main` branch is the collaboration baseline. For new development, clone
that repo or fetch and switch to `origin/main` once local Git authentication is
configured; preserve ignored lab artifacts separately.

## Published collaboration baseline

The repository is [fryezero/mu-the-matrix-native](https://github.com/fryezero/mu-the-matrix-native). All 58 source/documentation files were downloaded from GitHub and compared byte for byte with the reviewed local snapshot. [The first CI run](https://github.com/fryezero/mu-the-matrix-native/actions/runs/38826951964) passed on macOS and Linux at commit `358354a009836105f2d9928397a4fe3f083326e7`. Setup actions were then updated to Node 24 versions to remove runtime deprecation warnings. Private game inputs and raw evidence remain in the original lab only.

## Latest model recovery

MODEL-014 is implemented on `codex/model-v14`. All 216 v14 models decode through the bounded Crypto++ wrapper and pass strict structural parsing, matching the separately compiled pinned upstream oracle. The complete scan is `model-recovery/verified-v14/manifest.json`; independent comparison is `evidence/v14-source/project-oracle-comparison.json`. The new public fixture has 91 synthetic vectors covering every cipher pair, thresholds, overlapping windows and selector aliases. Portable tests pass 43/47 with four explicit private skips; local integration passes all 47.

The runtime experiment is isolated under `runtime/x86/`, with a verified Debian base, a working overlay, a localhost-only SSH forward and a read-only game transfer mount. Preserve the existing guest while checking progress; do not start duplicate QEMU instances on its disk or port. The copied client launches far enough to restore its first code section. No login/gameplay or complete source rebuild is established.

## Continue after the Mac-only capture

RUNTIME-X86 is tracked in GitHub issue #5. The first executable section is repeatably restored, SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`. The successful bounded REA record is `evidence/rea-restored-client-prefix.json`. The verified scoped capture and durable manifest are `evidence/x86-capture-text-08/`. The authored Linux reader is `runtime-linux/capture_text.py`; it selects only that section and writes durable identity/hash metadata. Read the restored-code report before importing bytes. Preserve original captures and failed attempts separately. The current client reaches an unresolved localhost connection and no demonstrated login window.

GitHub CLI now authenticates as the repository owner through the macOS keychain. Git fetch/push and PR/check operations work directly; use them instead of browser uploads. The current development branches track their real GitHub history; older `lab/` branches retain the initial archival snapshots. Never print or commit the authentication token. PR #4 contains the model work and its corrected Linux build.

The runtime work is [PR #6](https://github.com/fryezero/mu-the-matrix-native/pull/6), stacked on model PR #4. Both pass macOS/Linux CI. Both are now merged into main, in dependency order. Runtime tests discover 55 cases, with 51 passing and four private-input skips in a source-only checkout; opt-in local integration passes all 55. The final capture08 binds the mapped header to the pinned file device/inode before and after reading and reproduces the earlier restored digest. The guest shut down cleanly after transfer and local verification. CAP-002 results follow below.

## First source behavior from restored instructions

CAP-002 / issue #7 is merged into main through [PR #8](https://github.com/fryezero/mu-the-matrix-native/pull/8). Read `research/client-copy64.md` and `../reconstructed/client-memory/README.md`. The authored 64-byte copy matches the pinned captured routine in 393 synthetic cases under Unicorn 2.1.4, including both overlap directions and sub-word alignment. An intentionally wrong `memmove` replacement fails 158 cases. REA decompilation is retained in `evidence/rea-client-copy64.json`; the generic profile missed the explicit pointer return/ECX role, which were checked from instructions and emulation.

Portable tests pass 57/62 with five explicit private skips; local integration passes all 62. Original class/callers and real-game invocation are unresolved. PRs #4, #6 and #8 are merged. PR #8 passed macOS/Linux CI. Continue with [issue #9](https://github.com/fryezero/mu-the-matrix-native/issues/9) to recover caller/type context or validate the adjacent clear routine, then approach x87 arithmetic with precision/control-word checks. Merge authority is recorded in AGENTS.md.

## Clear routine and reference search

Issue #9 is merged into main through PR #10 after passing macOS/Linux CI. Read `research/client-clear64.md`. The full wrapper/helper match authored clear64 in 768 cases across scalar/SSE feature branches, all 64 alignments and both DF states. The actual global feature value is unknown. No helper stub is used; execution hooks check branch coverage and memory access. Exact absolute-address scans of the original executable and restored text found no references to the first copy/clear/length entries. Original type/callers remain unresolved. Local evidence paths and REA identity are in the finding. Tests pass 59/65 with six explicit private skips and all 65 with opt-in local inputs. Next broaden the bounded function/data map to find useful subsystem entry points.

## Bounded window map

CLIENT-MAP-001 / issue #11 is merged into main through PR #13 after passing macOS/Linux CI. Read `research/client-window-map.md`; current local map is `evidence/client-map-64k/candidate-map-v5.json`. The first 64 KiB yields 803 explicitly labeled candidates, not recovered symbols. REA's initial 31-entry inventory overlaps 29; two entries are missed by the authored heuristic. A separately seeded REA dossier for `0x004013d0` suggests a cofactor/reciprocal 4-by-4 record operation, whose global double/template at `0x01a7dd40` and `0x01cf3b00` are outside the text capture and remain unknown. Next capture those selected image-data ranges with verified process/file identity before validating nontrivial arithmetic. Static map tests cover loops, segmented references and explicit unresolved paths. Portable dependencies now include Capstone through `tools/requirements-portable.txt`; full analysis still adds Unicorn.

## Selected record constants captured

Issue #12 is merged into main through PR #14 after passing macOS/Linux CI. Read `research/client-math-data.md`. The fixed `math-data` scope saves only 8+64+4 bytes and requires the restored-text hash before and after reading. Capture09 passed all identity/mapping/source checks, was transferred and hash-verified; the same source also repeated the legacy text scope. An early packed-state attempt was correctly refused with no payload. The guest shut down cleanly. Captured bias equals positive double zero, template equals a public identity matrix construction and feature bit1 is set in this Wine run. Original bytes remain ignored. Next reconstruct the selected cofactor/reciprocal operation, with explicit x87 control-state and overlapping-buffer checks.

## Controlled record arithmetic

Issue #15 is merged into main through PR #16 after passing macOS/Linux CI. Read `research/record-math.md` and the module README. Actual helper/wrapper bytes and captured data match authored C in 1,680 cofactor and 1,050 inverse cases under PC53/RNE masked x87 state with an empty stack. A translation snapshot replacement fails 16 alias cases; PC24 differs in 1,471 comparisons. Evidence JSON and REA dossier stay ignored. Full arena, stack/register effects, control state and bounded accesses are checked. Original FP state, type/callers, NaN/trap/status and general underflow domains remain unverified. Tests discover 88 cases: 81 portable pass with seven private skips; all 88 local integration pass. Next recover genuine caller/type context or original FP-state evidence before widening the model.

## Rejected model fields

Issue #17 is merged into main through PR #18 after passing macOS/Linux CI. Read `research/model-edge.md`. All 17 v15 rejections now identify their decisive decoded field offset. Thirteen complete structural records contain 66 direct edges to dummy parents; the other four have a NaN animation position, an active normal index and unsupported normal/vertex bone values. Native and Python decryptions agree for every complete payload. Raw diagnostics/probe stay in `evidence/model-edge/`. New errors preserve acceptance and expose `BmdError.offset` for these paths. Five independent synthetic regressions cover field offsets and indirect dummy ancestry. Next recover original model-loading/hierarchy behavior before accepting sentinel or dummy-parent semantics.

MODEL-EDGE (issue #17) recovers that behavior; read `research/model-edge.md`. `scripts/validate_model_edge.py` runs the client's reader section, pose builder, transform and mesh draw on the 17 files with the third section mapped zero and foreign accesses recorded. All runs match, with authored C `model_reader.c`; the report is in `evidence/model-edge-client/`. The client accepts all 17 unchecked. The dummy-parent children are unused IK Chain leaves, so geometry is state-independent. The other four read unowned memory at recorded addresses. `bmd10.py` `client_layout=True`, `recover_models.py --client-layout` and the native loader/viewer reproduce the client and list every value; strict defaults are unchanged. Open: runtime contents of that memory, the heap texcoord of `rockinghorsepet_evol`, and the callers that load these files.

## Second image section acquired

Issue #19 is merged into main through PR #20 after passing macOS/Linux CI. Read `research/client-image-data.md`. The fixed second section at VA0x01a7c000, length2557764, repeats SHA-256 `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`. All identity flags, restored-text checks, early refusal, transfer digests and legacy math/text modes pass. Guest shut down cleanly. Ignored evidence is `evidence/image-data-run10/`; the local ASCII catalog has candidate BMD strings at 0x01aef904,0x01aefab4,0x01aefc6c. Next inspect bounded pinned-text references to those addresses and confirm instruction/function boundaries before inferring loader semantics. Do not relax the rejected-model checks without client evidence.

Continue with GitHub issue #21, CLIENT-LOADER-001. Local raw literal matches occur at 0x018202c7,0x018203f0,0x01830aef; nearest prologue candidates are 0x018202b4,0x018203e0,0x01830aa6. Linear decode reaches candidate PUSH instructions, but control flow/function boundaries remain unverified. The ignored `model-loader-literal-candidates.json` and `model-loader-prologue-candidates.json` retain these observations. Validate bounded REA dossiers before assigning loader semantics. Main is the reviewed baseline; guest is shut down.

## Client-linked v12 source

Issue #21 is merged into main through PR #23 after passing macOS/Linux CI. Read
`research/client-model-loader.md` and `../reconstructed/model-codec/README.md`.
The BMD filename caller at `0x018202b4` calls `0x012b3812`, whose v12 branch
calls `0x0098c5f2` for both length query and decode. REA dossiers are local under
`evidence/model-loader-first/`, `evidence/model-loader-callee/` and
`evidence/model-codec/`. The 194-byte leaf decoder matches authored C in 4,048
synthetic cases and all 180 installed v12 payloads, totaling 3,176,971 bytes.
A feedback-before-store replacement fails 312 overlap cases. The C API preserves
signed-length query/nonpositive behavior and read-after-write alias effects.
The comparator checks full arena, two reads/one write per byte, saved registers,
caller return, stack cleanup and both DF states, without decoder substitutes.
Portable tests pass 94/102 with eight private skips; all 102 local integration
pass. Complete model loading, original types and hierarchy acceptance remain
open. Next follow v14 target `0x016ced37` or v15 setup/decode
`0x0091a6c0`/`0x0091a730`, or validate a bounded v10 loader path with explicit
I/O/allocation dependencies.

## v15 jump slots resolved

Issue #24 is merged into main through PR #26 after passing macOS/Linux CI. Read
`research/model-dispatch.md`. Two fixed four-byte slots at `0x01d04e14` and
`0x01d04df4` repeat targets `0x0092a430` and `0x0092be30`, both inside pinned
text. Capture11, repeat, all three legacy scopes and transferred hashes pass;
a controlled second startup refused known packed text with an empty manifest
and no slot payload. Guest shut down cleanly. Raw artifacts are under
`evidence/model-dispatch-run11/`; original preflight failure and corrected
readiness attempt remain in `evidence/client-lea/` logs. A bounded decode-target
REA dossier is in `evidence/client-lea-resolved/`. Next inspect key setup and
its eight/four/single-block helpers, validate actual argument passing and
compare authored behavior against original code before claiming a v15 decoder.
Hierarchy findings landed in PR #25; review corrections follow below.

## Hierarchy review and shared baseline

PR #25 landed while the dispatch work was integrating. Post-merge independent
reviews verified the core selected-loop observations and found two evidence
accuracy issues, addressed under #27 in `codex/review-model-hierarchy` and merged
through PR #28. Both platform checks passed on commit
`6fd939d2c757b268f1c000f4efdd4d8439025936`, CI run `38892589220`.
Raw E8/PUSH searches remain heuristic candidates; PUSH lookahead now stops at
control transfers, including LOOP and traps. The v2 report keeps 314 raw call
candidates and 300 buffer-push candidates, with explicit unverified provenance.
Prior dummy-slot contents remain unknown, and child output is a composition
with that prior input, not necessarily equal to it. Read
`research/model-hierarchy.md` and `handoffs/claude-model-hierarchy.md`.
Strict parser acceptance is unchanged. Raw verification and test logs are in
`evidence/hierarchy-review/` and `evidence/hierarchy-review-*.txt` in the original
lab. Next continue v15 key/decode source using the resolved dispatch targets;
actual pose-buffer state during affected-model rendering remains unobserved.

## Client-linked v15 key context

Issue #29 / `codex/client-lea-key` merged through PR #30 after macOS/Linux CI
run `38893633476`. It adds authored C key setup for the observed
`0x0092a430` target. Read `research/client-lea-key.md`. The 6,446-byte original
body matches 1,320 synthetic cases across 16/24/32-byte keys, all word alignments,
both DF states and null/unsupported gates. It writes forward keys plus round
count at byte 768, leaving unused context bytes untouched. An independently
compiled reversed-order variant fails 1,248 valid cases. Key/context spans must
be disjoint; ECB payload decoding and native Windows behavior remain unverified.
Raw probe, reports and test logs are under `evidence/client-lea-key/`; REA is
`evidence/client-lea-resolved/rea-key.json`. Next validate eight/four/single-block
helper argument passing and batch alias behavior, starting at resolved wrapper
`0x0092be30` and helpers `0x00927060`, `0x00929370`, `0x0093bb20`. No VM startup is
needed for the captured instruction bytes. Guest remains shut down.

## Client-linked v15 ECB source

Issue #31 / `codex/client-lea-decode` merged through PR #32 after macOS/Linux CI
run `38895766466`. It adds authored batch ECB source. Read
`research/client-lea-decode.md` and `../runtime-linux/lea-compare/README.md`.
The relocated original wrapper and AVX/scalar helpers match 12,960 valid and
46 no-op guest cases. The ABI bridge rejects its own bad callee; wrong scalar
batching differs in 4,094 cases. Host Unicorn checks 1,152 scalar cases with
memory hooks, but refuses AVX. A separate host C corpus comparison matches all
11,583 v15 payloads, 655,268,704 bytes, against the independent reader. Original
instructions were not run on that entire corpus; structural rejections remain.

The guest runner only reads pinned text, copies four selected bodies into a
shared relocated window, and checks output/ABI with page guards and read-only
context. It has no inside-arena read trace. Static pinned-byte checks validate
relocation and the BMD caller's 32-byte public key. Original-address mapping
conflicted with runner allocations; that failed probe and Unicorn AVX failures
are retained. Guest run14, scalar/corpus reports and all test logs are ignored
under `evidence/client-lea-decode/`; earlier probe failures are under
`evidence/client-lea-key/`. Guest is shut down after verification.

The suite discovers 135 tests, 124 portable passes plus eleven private skips;
all 135 opt-in private checks pass. A clean source checkout is checked separately.
Next recover original record-loading/allocation paths or the actual hierarchy
matrix concatenate at `0x00cff83e`. Keep unknown prior dummy-slot state explicit;
a decoder result does not justify relaxing the parser or claiming rendering.

## Controlled hierarchy composition

Issue #33 / `codex/pose-concat` merged through PR #34 after macOS/Linux CI
run `38898823896`. It adds `mu_pose_concat` to record-math, reusing byte
storage helpers without changing cofactor/inverse behavior. Read
`research/pose-concat.md`. Original `0x00cff83e..0x00cfff3b` matches 5,176 controlled
RNE binary32 cases. A separately compiled input-snapshot variant fails 2,464.
Of 5,200 attempts, 24 leave the finite normal/zero domain and are recorded
separately. Initial NaN differences exposed incomplete emulator status reporting;
new instruction hooks inspect arithmetic results directly instead of trusting
MXCSR status alone. Raw failures, corrected report and REA are in ignored
`evidence/pose-concat/`. Standalone validation also verifies three selected
hierarchy call instructions. No live pose-buffer state or actual renderer is
claimed. Guest remains shut down; this check uses existing captured bytes.

Next recover rotation helper `0x00d00724` or bounded original record-loading /
allocation behavior. Native game source, simulation and services remain open.

## Rotation dispatch flag captured

Issue #35 / `codex/trig-state-capture` adds the fixed `trig-state` scope. Read
`research/client-trig-state.md`. The four-byte main-image flag at `0x0bdd1cc8`
repeats value 1 with digest `67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450`.
Restored text and every identity flag pass. An early attempt saves only an empty
incomplete manifest on the known packed hash; all four legacy modes repeat
run11 formats/digests. Transfer verification and raw results are ignored in
`evidence/trig-state-15/`; guest shut down cleanly.

Rotation candidate `0x00d00724` reads three floats scaled by captured 0.5, calls
float wrappers `0x009681bd`/`0x009fa223` three times each, and writes four floats.
REA in `rea-rotation.json` suggests Euler-to-quaternion behavior; no authored
source equivalence yet. Wrappers call `0x01985700`/`0x0198c4d0`, which test the
captured flag plus x87/MXCSR state. Next emulate with actual text/data/flag under
explicit FP settings, following actual trig code and stopping on unknown reads.
Fallbacks also reference `0x0bdcfbc8`, not yet captured. Do not assume a live path
from the flag alone or substitute host sine/cosine as proof. Full game recovery
remains incomplete. Suite:141 total,129portable/twelve private skips; all141
local integration pass. Original raw bytes stay local.

A private smoke probe now runs the full rotation candidate and its actual trig
helpers on three synthetic angle triples with flag 1, x87 PC53/RNE and MXCSR
`0x1f80`. All return, including zero input yielding `(0,0,0,1)`. It stops on any
read of uncaptured bytes in the flag's page; none occurred in those cases.
`evidence/trig-state-15/probe-rotation.py` and `rotation-probe.json` preserve this
lead. It is not an authored-source equivalence or complete ABI/access check.
The next concrete task is now C reconstruction plus a bounded comparison suite
using those actual helpers, without stubs. Do not count three smoke cases as a
validated quaternion implementation.

## Rotation conversion reconstructed

Issue #37 / `claude/rotation-reconstruct` (worktree
`~/Documents/mu-worktrees/rotation`) adds `mu_rotation_quaternion` and
`mu_rotation_quaternion_using` to record-math. It also adds
`scripts/validate_rotation.py` and `scripts/scan_trig_midpoints.c`. Read
`research/client-rotation.md`. The helper converts three binary32 angles to
the x,y,z,w quaternion of Rz(a2)·Ry(a1)·Rx(a0). Each half angle is rounded to
binary32, and products are rounded separately in the original order.

Unicorn runs the actual 411-byte body, both float wrappers and the actual
client trig entries without stubs. It uses captured flag 1, x87 `0x027f`,
MXCSR `0x1f80`, the full pinned text and the verified second section. Any other
read stops a case. All 8,012 SSE2-domain cases match bitwise, including arena,
ABI, ordered stores and bounded access checks. Another 2,816 alias/alignment
and 256 PC64/PC24/register/status variants also match. Wrong axis order fails
7,547, and binary64 products with one final rounding fail 3,460. Five
caller CALLs are verified statically.

The C uses host libm sine/cosine. The client SSE2 results differ from macOS
libm by one binary64 ULP in 718 of 48,072 calls. All agree after binary32
rounding, including 112 scanned host-midpoint candidates run with both signs in
every axis. Angles with |a| >= 180,224 and ±inf enter the x87 fallback, which
stops at uncaptured `0x0bdcfbc8`. NaN returns through it, but that path is not claimed.
Unicorn reports no MXCSR status bits. The first harness run aborted on that
NaN path; the cause is recorded in the finding.

Raw reports (`comparison-01-no-midpoints.json`, `comparison-02.json`), scanner
output, notes and test logs are ignored under `evidence/client-rotation/` in that
worktree. Its `evidence/` and `input/` entries otherwise symlink to the main
lab for read-only use. Portable: 147 discovered, 134 pass, 13 explicit skips.
Opt-in integration passes 142. Five installed-model checks need `MU_GAME_ROOT`
data, which was not available outside the CrossOver bottle and was not used.
No guest or CrossOver run.

Next: recover the BMD bone-track loop `0x012b42ae..0x012b4441`. Per action it fills
position (12×keys), rotation (12×keys) and 16×keys entries via `0x00d00724`.
Compare it against installed v12/v14 bone data before moving into pose-builder
interpolation at `0x012b5064`. Alternatively, reconstruct client SSE2 sine/cosine
`0x019a72f8`/`0x019acd58` exactly to remove the libm substitution. The
public-constant relationship must first be established against the private tables.

## Bone-track loop reconstructed

Issue #40 / `claude/bone-track-loop` (worktree `~/Documents/mu-worktrees/bone-tracks`)
adds `mu_bone_tracks_read` in `reconstructed/model-codec/bone_tracks.{c,h}`,
built as `libbonetracks` with record-math. It also adds
`scripts/validate_bone_tracks.py`. Read `research/client-bone-tracks.md`.
The loop `0x012b4225..0x012b4441` writes these bone fields:

* `+0x22`, the dummy flag, written first and tested from the record;
* for non-dummy bones only, the name at `+0x00`, the raw parent at `+0x20` and
  a track-array pointer at `+0x24`.

The track array has 12 bytes per action. Its three pointers lead to positions
(12 bytes/key), Euler rotations (12 bytes/key) and quaternions (16 bytes/key)
from `0x00d00724`. Each non-dummy bone makes 1+3×actions operator-new calls,
with saturating sizes. Zero counts still allocate 1-byte blocks. Nothing is
bounds-checked.

Unicorn runs the actual loop, memcpy `0x0194c200`, operator new/malloc and the
rotation/trig helpers. Only the HeapAlloc import (stub `0x7bc275e0`), the
uncaptured heap handle `0x0bdcfc10` and memcpy feature word `0x0bdcb284`
(values 0/1/2) are modeled. Every other uncaptured or undefined read stops a
case.

Results: 342 synthetic comparisons match. Installed models matching through the
existing readers: v12 180/180, v14 216/216 and v15 11,566/11,566 (17
reader-rejected v15 not run), totalling 4,759,146 rotations. An
eliding-zero-allocation control differs in 57 comparisons. Allocation failure
stops at uncaptured CRT state (`0x0bdcf8f0` new mode, TLS errno), as does a
beyond-SSE2 angle (`0x0bdcfbc8`).

The full report `comparison-v12-v14-v15.json` (SHA-256 `323e7c3f…dbbf`), its log
and the test logs are ignored under `evidence/client-bone-tracks/` in that
worktree. `model-recovery/verified-v14` there is a read-only symlink to the
main lab, made for the model-codec integration check. Portable: 155 discovered,
141 pass, 14 explicit skips. Opt-in integration with `MU_GAME_ROOT` (read-only
`runtime/client`) passes all 155. No guest, CrossOver or
main-checkout change.

Next: pose-builder interpolation at `0x012b5064`, which consumes these
per-action arrays (rotation calls at `0x012b53c9` and `0x012b53d8`). Use the
same harness boundaries, seeding the model from this loop's output. Alternatives:

* run the 17 rejected v15 files through the loop with a non-validating locator;
* compare the sibling plaintext reader's bone loop `0x012b35c7..0x012b37e3`
  against all 701 v10 models.

## Pose builder reconstructed

Issue #46 / `claude/pose-builder` (worktree `~/Documents/mu-worktrees/pose-builder`)
adds `mu_pose_build` in `reconstructed/model-codec/pose_builder.{c,h}`, built as
`libposebuilder` with the bone-track loop and record-math. Record-math gains
`mu_quaternion_compare`, `mu_quaternion_slerp[_using]`, `mu_quaternion_matrix`
and `mu_angle_matrix[_using]`. The validator is `scripts/validate_pose_builder.py`.
Read `research/client-pose-builder.md`.

The builder is thiscall on the model (eight stack arguments, `ret 0x20`). Per
non-dummy bone it takes q1/p1 from (prior action, prior frame) and q2/p2 from
(current action `+0xa8`, integer frame). It slerps by the frame fraction unless
all components agree within 0.001 (then it copies q1), and lerps positions.
Out-of-range frames reset to key 0 but keep the fraction. Bone 0 can lock x/y
to the current action's key 0, and special bone `+0x60` rebuilds its quaternions
from head-adjusted Euler angles. The quaternion goes to global `0x075a90d8+16*i`.
The matrix composes with the root global `0x078965ac` (rebuilt from model
angles unless keep-root) or with `output+parent*0x30`.

Every case first runs the actual bone-track loop; the builder then runs with all
client callees (compare/fabs, slerp/acos/sin, matrix helpers, rotation,
composition) and no stubs. Only the two uncaptured globals and caller memory
are modeled. Results: 483 synthetic calls, 1,822 direct helper calls and 47,833
installed calls on 180 v12, 216 v14 and 11,566 v15 models all match. Lerp differs
in 364 and modulo frame wrap in 60. Host-libm trig agrees after binary32
rounding in every observed call (binary64 differs by at most one ULP).
Zero-key actions read uninitialized 1-byte heap blocks; t beyond the SSE2
domain and far parents stop as characterization.

The report `comparison-v12-v14-v15.json` (SHA-256 `d93ceb8e…0615`), its log,
synthetic reports, disassembly listings and test logs are ignored under
`evidence/client-pose-builder/` in that worktree. `model-recovery/verified-v14`
there is a read-only symlink to the main lab. After rebasing onto the fast-x87
changes: portable 190 discovered, 175 pass, 15 explicit skips. Opt-in
integration with `MU_GAME_ROOT` (read-only `runtime/client`) passes all 190.
No guest, CrossOver or main-checkout change.

Next: trace the builder's callers (314 raw candidates) to recover how the
prior frame/action and keep-root flag are chosen per animation tick. Then
follow the output matrices and quaternion table into the skinning/renderer
consumer. Alternatives: the second builder `0x012bcffb` (action-0 only), the
17 rejected v15 files with a non-validating locator, or the v10 sibling loop.

## Skinning path reconstructed

Issue #53 / `claude/skinning-path` (worktree `~/Documents/mu-worktrees/skinning`)
adds:

* `mu_model_transform` and `mu_animation_tick` in
  `reconstructed/model-codec/skinning.{c,h}`, built as `libskinning` together
  with the pose builder, the bone-track loop and record-math;
* record-math vector helpers `mu_vector_rotate`, `mu_vector_transform` and
  `mu_vector_irotate`;
* `scripts/validate_skinning.py`, which runs the actual instructions;
* `scripts/client_render_static.py`, a static map of callers, import slots and
  GL order.

Read `research/client-skinning.md`.

Callers. All 314 raw builder candidates sync, in 105 functions:

* 300 write the shared bone buffer `0x06fce398`;
* 117 take frame, prior frame, prior action, angles and head angles from one
  object (`+0xd0`, `+0xd4`, `+0x2c`, `+0x164`, `+0x170`);
* 140 take a computed frame, 108 of them `object+0xd0` minus a local;
* 19 use `(int)frame - 1` as the prior;
* 12 are bind poses and 26 are other.

The tick `0x012b4dd3` has 91 candidates and is the prior-frame writer. When the
integer frame changes, `*prior_action = model+0xa8` and
`*prior_frame = old integer`. Keep-root calls (25) follow root setter
`0x012b7019`, which copies a parent bone matrix into root global `0x078965ac`
for attachments.

Skinning. The transform `0x012b5bde` is reached through wrapper `0x00966ea5`
with buffers vertices `0x078978a0`, normals `0x0812cce0` and light
`0x06fd0918`, at per-mesh strides `0x2bf20`/`0xea60`. Each vertex uses one bone,
with no blending. Normals are rotated only. Light is a clamped Lambert term and
also goes to a secondary table at `0x075a9ee8`.

Comparisons. The actual transform, tick and vector helpers run with no client
stubs. Installed models chain through the actual bone-track loop and actual
builder, and the transform reads the builder's real output window. Results:

* 903 direct helper calls, 226 synthetic transforms, 24 builder-chained
  synthetic models and 481 synthetic ticks match;
* installed v12 180, v14 216 and v15 11,566 transforms match, covering
  3,814,006 vertices and 3,988,165 normals, plus 35,871 installed ticks;
* the transposed-rotation, translated-normal, prior-every-tick and ignore-lock
  controls fail in 210, 223, 259 and 35 cases.

Draw. The mesh draw `0x012b8d1d` (wrapper `0x00966e4a`, 6,361 raw calls) was
not executed. Statically it sets cached GL state, binds the texture through
`0x0184acf6`, issues one `glBegin(GL_TRIANGLES)`, and per corner calls
glTexCoord2f, then glColor3fv or glColor4f, then glVertex3fv on the transform
output, then glEnd. The body `0x012bb35a` brackets the mesh draws with
glPushMatrix/glPopMatrix and makes no matrix call between them.

The import slots are named against Debian Wine `8.0~repack-4` i386 opengl32/glu32,
matching the guest. All 81 + 4 slots resolve, and the first slot equals the file's
only static import name. The `.deb` (`c992aad6…8d57`, matching the bookworm
`Packages` hash), the extracted DLLs, the report `comparison-v12-v14-v15.json`
(`4b225477…c036`), the static report `static-05.json` and the logs are ignored
under `evidence/client-skinning/`. A first run with v14 reader-rejected (unbuilt
`libmodulus`) is kept as `run-01-v14-unbuilt/`.

`model-recovery/verified-v14` in that worktree is an untracked read-only
symlink to the main lab; do not stage it. Portable: 209 discovered, 192 pass,
17 explicit skips. Opt-in integration with `MU_GAME_ROOT` (read-only
`runtime/client`) passes all 209. No guest, CrossOver or main-checkout change.

Next: execute the mesh draw `0x012b8d1d` and body `0x012bb35a` under Unicorn,
with the OPENGL32 IAT targets mapped to an authored GL-call recorder. Seed them
with the actual transform output on installed models, and compare against an
authored C emitter of the same GL stream (per-corner texcoord/colour/vertex,
state and binds). Alternatives:

* trace the action-change code that writes object `+0x2a`, `+0x2c` and `+0xd4`;
* identify the 24 immediate GL_TRIANGLE_FAN routines behind the profiled
  four-vertex fans;
* trace the main loop and frame cap.

## Frame loop and hot draw sites mapped

Issue #55 (CLIENT-FRAME-001), branch `claude/frame-loop`, worktree
`~/Documents/mu-worktrees/frameloop`. Read
[`research/client-frame-loop.md`](research/client-frame-loop.md). The work is
static; no client code ran and nothing was patched.

**Loop.** The WinMain loop uses `PeekMessageW(PM_REMOVE)`. When the queue is empty
it calls the scene dispatcher `0x01859d8a`. Scene states 3, 5 and 6 go to the frame
driver `0x01851d39`, state 4 to the loading screen and state 2 to the intro. The
frame driver works like this:

* `[0x0bdc5ec0]` accumulates elapsed time, and game logic runs once per 40 ms
  step (`0x01851d6b`, `0x01851f90`);
* GetTickCount at frame start is stored in `[0x0bdc5e64]`;
* the scene render is followed by SwapBuffers at `0x01852653`;
* if elapsed < 40, it calls `Sleep(40 - elapsed)` (`0x0185267a`) and sets elapsed to 40.

**Cap.** The cap is the immediates at `0x0185266b`, `0x0185266f` and `0x01852690`,
with the branch `7D 26` at `0x0185266c`. The 44-byte block has SHA-256
`37978e18…2e14`. It does not occur in the Themida-packed file, so the only way to
change it is an in-memory write after unpacking, for example from the owner's mugl
proxy at the first wglSwapBuffers, after verifying the block. The rendered-frame
counter `[0x0bdc5ebc]` has 225 readers and would speed up with the frame rate.
Logic and the wall-clock float `[0x06fce370]` would not. `IGC.dll` hooks the
function at `0x01851d5e` and `0x018526e7`.

**Draws.** The fans come from three places:

* the terrain renderer `0x016cd468`, which walks the frustum box in 4×4-tile
  blocks and emits one fan per tile per layer through `0x016cf46c` and friends,
  plus a grass quad;
* terrain decals `0x016cdd5f` (460 callers), one fan per covered tile;
* 2D helpers `0x0184d9bb`/`0x0184dcb1`/…, with 243 and 170 callers.

Quads are mostly the sprite routine `0x0184c39c` (433 calls in `0x0159123f`) and
effects. All 51 sites carry return addresses for runtime attribution.

**VBOs.** The calls go through data-import function-pointer slots
`0x01a7cb54..0x01a7cc14` (GLEW-style). There is no glBufferSubData name string.
The effect system streams two GL_STREAM_DRAW buffers:

* sprite: 144 B at object `0x01d1e2c8`, a whole-buffer update per draw;
* emitter: 144,000 B at `0x01d1e6f8`, an `n*144` prefix per draw;

each followed by `glDrawArrays(GL_QUADS)` with client arrays at offsets 0, 12 and 20,
stride 36.

**Checks.** `scripts/client_frame_static.py` takes about 30 s. Its report is
`evidence/client-frame/static-02.json` (`9627bb4f…0abe`, ignored), with the pinned
Wine DLLs extracted alongside. Portable: 218 discovered, 200 pass, 18 explicit
skips. The new private check passes with `MU_RECOVERY_INTEGRATION=1` and
`MU_GAME_ROOT=runtime/client`. The full opt-in suite was not rerun. No guest,
CrossOver bottle or main-checkout change.

**Next.**

* Add an opt-in glBegin return-address counter to mugl and map the counts through
  `static-02.json`. This settles the terrain/decal/UI split and attributes the
  unexplained glViewport/glOrtho and glActiveTexture calls (`IGC.dll` or the
  third-party renderer).
* Extend mugl's buffer orphaning to offset-0 prefix updates of the 144,000-byte
  effect buffer.
* If the owner wants a higher menu cap, prototype the verified in-memory write
  in a test bottle, not MuMatrix32.

## Native model viewer (NATIVE-VIEW-001)

Branch `claude/native-viewer`, worktree `~/Documents/mu-worktrees/native-viewer`. Read
[`research/native-viewer.md`](research/native-viewer.md) and [`../native/README.md`](../native/README.md).

**Built.**

* `native/core`: portable C. It covers the checked BMD loader, client-memory layout around `mu_bone_tracks_read`/`mu_animation_tick`/`mu_pose_build`/`mu_model_transform`, the `mu_meshdraw` corner-loop port, the scene driver, the software rasterizer, textures, PNG and SHA-256.
* `native/viewer`: SDL2 + GL 2.1 window and CGL headless rendering.
* `native/tools/mu_render.c`: headless CLI with the `info`, `dump`, `corners`, `render`, `image` and `scan` commands.
* `native/tests`: fixtures, the golden reference harness, the independent mesh-draw model and 16 tests (12 portable, 4 private).

**Checks.**

* `make test PYTHON=tools/.venv/bin/python` passes on macOS: 270 discovered, 22 explicit skips.
* `native/tests` also passes in Ubuntu 24.04 arm64 and x86_64 containers, with identical pinned render hashes. The harness script and logs are in `~/Documents/mu-mac-tools/native/scratch/`.
* The private checks pass with `MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=<MuTheMatrix>`. The full golden run used `MU_NATIVE_GOLDEN_PER_VERSION=100000 MU_NATIVE_GOLDEN_MAX_VERTICES=100000` (466 s). The corpus scan takes 6 s.
* Local renders of installed models are in `~/Documents/mu-mac-tools/native/renders/` and are never committed.

**CI.** The macOS job installs `sdl2` and `jpeg-turbo` and builds the window viewer with `make native-viewer`. Linux installs `libjpeg-dev`. The viewer test skips without `sdl2-config`.

**Next.**

* Execute the mesh draw and body under Unicorn with a GL recorder. Compare against `mu_meshdraw` and `mu_scene_draw_model` to settle mode selection, state, texture parameters and the `0x072acfd8` normal-texcoord writer.
* Then do character assembly (Player skeleton, parts, keep-root attachments), followed by terrain.

No game, CrossOver bottle or registry was touched.

## Post-merge review of PR #66 (NATIVE-VIEW-001)

PR #66 was opened at 18:09:58Z and merged at 18:11:39Z without the independent review that
`CONTRIBUTING.md` asks for, and with no tracking issue. Its PR and push CI were green before the merge.
The review is a comment on PR #66. Branch `claude/native-viewer-review-fixes` fixes what it found:

* `native/core/mu_image.c`: a TGA whose image-ID length (byte 0) runs past the end of the data made
  the uncompressed path read past the buffer, because the unsigned `size - offset` wrapped.
  AddressSanitizer showed it with an 18-byte file, and `mu-render image` returned success with garbage
  pixels. The decoder now rejects the file. A regression test covers raw and RLE files, plain and
  OZT-wrapped, and fails without the fix.
* The golden tests now assert equal mesh counts before comparing meshes with `zip()`.
* `THIRD_PARTY_NOTICES.md` now lists SDL2 (zlib) and libjpeg-turbo (IJG/BSD-3/zlib, IJG
  acknowledgement for binary distribution). Both are linked, not vendored.
* `research/native-viewer.md`, `roadmap.md` and `status.md` now separate CI-verified claims from
  reported single-run ones: the full private corpus, installed textures and GL counts, Linux arm64
  hashes, and the authorship independence of the mesh-draw model.

**Checks run in the review:**

* `make test`: 270 run, 22 skips, all OK on macOS.
* A clean `make -C native all viewer` builds with `-Werror` and no warnings.
* `python3 scripts/audit_repository.py`: 0 rejected.
* An ASan/UBSan build passed the portable native tests, apart from two environment-only cases: the
  ctypes dylib, and the CGL viewer, which hangs under ASan. It also passed about 2,200 mutated BMD
  inputs and 4,000 mutated TGA/BMP/OZT/OZB inputs. The TGA bug above was its only finding.
* Private tests were not re-run, because the review touched no game data.

**Next:** unchanged from the NATIVE-VIEW-001 entry above.

## Character assembly (NATIVE-CHAR-001)

Branch `claude/native-char`, worktree `~/Documents/mu-worktrees/native-char`. Read
[`research/native-character.md`](research/native-character.md) and [`../native/README.md`](../native/README.md).

**Built.**

* `reconstructed/model-codec/character.{c,h}` (`libcharacter`): the rotation position `0x012b7019`, the transform position `0x012b6ef1`, and the class tier, skin index and tier-2 skip helpers; also the part type/file table of the loader `0x01830aa6`.
* `scripts/validate_character.py`: Unicorn comparison of those routines and the loader loop, plus installed `Player.bmd` → part and `Player.bmd` → item chains through the actual bone-track loop, builder, root setter and transform.
* `native/core/mu_character.*`, `mu_model` share/keep-root/rotation-position hooks, `mu-render character|chardump`, character options and the viewer's character mode.
* Tests: `reconstructed/model-codec/test_character.py` (4 portable, 1 private) and `native/tests/test_native_character.py` with `character_reference.py` (5 portable after the review, 2 private).

**Checks.**

* The validator passes everything (ignored report `evidence/native-char/character-full-03.json`, `bca220a3…94ae3b`, 90 s, MuMatrixKit game root).
* The private character tests pass with `MU_RECOVERY_INTEGRATION=1 MU_GAME_ROOT=…`.
* Local renders are in `~/Documents/mu-mac-tools/native/renders/char/` and are never committed.

**Next.**

* Trace the player stand/attack action selection, to name actions.
* Implement the world-path weapon specifics of `0x012bd910`: item lighting flag 0, draw `0x0176ce74`, per-part animation state, and the attribute 0x54/0x59/0x72 branches.
* Add the safe-zone back-carry matrices of `0x0139db9a`.
* Executing `0x0139be7a` under Unicorn with recorded draw calls would settle the render-flow reading.

No game, CrossOver bottle or registry was touched.

### Review before merge (NATIVE-CHAR-001)

An independent review ran before publication, on the same branch.

* **Docs vs code.** The finding, README and status match the code: link bones 33/42/47, light 0.4/0.8/0.2, the slot order 5..0 then weapons and wing, wing vector (0,0,15) at frame 2, creation scale 0.9. The ignored validator report (`character-full-03.json`, the same SHA-256 as runs 01 and 02) records 384/384 positions, 3x256 helper cases, 380 loader calls, 4 poses, 300 parts and 267 items.
* **Labelling.** Roadmap, status and finding now mark the Unicorn and installed results as reported single private runs. CI covers the synthetic golden data.
* **Fixes.** The new character options check their numbers before converting them to integers: slots for `--part`/`--weapon`/`--weapon-action`, and int32 range for `--class`, `--parts` and weapon actions. Before, `--weapon nan PATH` converted NaN to an int, which is undefined behaviour, and on arm64 it loaded slot 0. `mu-render image|scan|info` without a path reached a NULL dereference after the argument-count change; the commands now refuse it. The viewer title counts missing character textures. A portable regression test covers these cases.
* **Memory safety.** An ASan/UBSan build of `mu-render` passed the portable native suites. 3,000 mutated synthetic character sets (Player, parts, weapons, wing) and Players with 1, 3, 34 and 200 bones under link bones 33/42/47 gave no finding.
* **Checks.** `make test PYTHON=tools/.venv/bin/python` passes (282 tests, 25 explicit skips). `make native-viewer` builds with no warnings. `python3 scripts/audit_repository.py` rejects nothing. No client data, textures, renders or client bytes are committed. No absolute client path is referenced; the game root comes from `MU_GAME_ROOT` or `--game-root`. Private integration was not re-run in the review; the character agent's last run used the MuMatrixKit installation.

## Camera, picking, input and frame loop (NATIVE-FRAME-001)

Branch `claude/native-frame`, worktree `~/Documents/mu-worktrees/native-frame`. Read
[`research/client-camera-input.md`](research/client-camera-input.md) and
[`../reconstructed/camera/README.md`](../reconstructed/camera/README.md).

**Checks.** `scripts/validate_camera.py --cases 1000 --mutations` (private captures): 33,250 comparisons,
0 mismatches; 11/11 mutations detected. Portable: `reconstructed/camera/test_client_camera.py`,
`native/tests/test_native_frame.py`. Renders stay local in `~/Documents/mu-mac-tools/native/renders/frame/`.

**Next:** decode the world data that feeds the world FOV, far factors and near plane; port the 4x4 tile walk
`0x016d2e8e` and character picking; trace MoveHero past target selection (path finding, move packet);
replace the flat terrain with the terrain milestone's renderer.
## Native audio (NATIVE-AUDIO-001)

Branch `claude/native-audio`, worktree `~/Documents/mu-worktrees/native-audio`. Read
[`research/client-audio.md`](research/client-audio.md) and [`../reconstructed/audio/README.md`](../reconstructed/audio/README.md).

**Built.** `reconstructed/audio` (FMOD-boundary reconstruction of the sound system, sound table, music,
frame block `0x0185280c`, OpenWorld volume, Option.ini, UI conversions); `scripts/validate_audio.py`
(Unicorn comparison); `scripts/extract_audio_tables.py` (local sound/music table, never committed);
`native/core/mu_wav.c`, `mu_audio.c`, `mu_audio_decode.c`, `mu_audio_host.c`; `native/tools/mu_audio.c`
(`list`, `decode`, `render`, `scan`) and `mu_audio_live.c` (SDL2).

**Checks.** `make test` passes on macOS with 30 new tests (3 private); the audio tests also pass in Ubuntu
24.04 arm64 and x86_64 containers with the same pinned render hash (`scratch/audio/linux-test.sh`). The validator passes every check
with `--random 2000`; its report and the local tables are in `~/Documents/mu-mac-tools/native/scratch/audio/`.
Renders: `~/Documents/mu-mac-tools/native/renders/audio/` (scripts and WAVs).

**Next.** Capture `0x01cf1680` to settle music indices 43/44; reconstruct the event-world music managers;
map the SND_Play call sites to game events; wire the module into the native client frame loop.

No game, CrossOver bottle or registry was touched.

## Mesh draw executed (CLIENT-MESHDRAW-EXEC-001)

Branch `claude/native-unicorn`, worktree `~/Documents/mu-worktrees/native-unicorn`. Read
[`research/client-meshdraw-exec.md`](research/client-meshdraw-exec.md).

**Built.**

* `native/core/mu_meshdraw.{c,h}`: a port of the mesh draw `0x012b8d1d`, body `0x012bb35a`, GL state wrappers
  and the `0x072acfd8` normal-texcoord writer, emitting the literal GL call stream. It also ports the
  texture-name parser `0x01185111` (`mu_meshdraw_sub_from_name`). New conventions: `MU_MESHDRAW_FAULT` stops
  where mode 0x8000 would read outside a pixel buffer; out-of-range indices are refused.
* `native/core/mu_meshdraw_case.{c,h}`: self-contained case files. They are written by `mu-render corners --case-out`
  and replayed by `mu-render replay`.
* Scene, textures and viewer:
  * `mu_scene` builds mesh `+0x1c` records from the texture names and keeps no pixel buffers;
  * `mu_textures` applies the client upload rules;
  * the GL backend uses per-texture filter and wrap with the client's GL enums;
  * the viewer's M key cycles flags, and windowed time advances.
* `scripts/validate_meshdraw.py`: the Unicorn harness, also covering the name parser, a math sweep, pinned CI
  cases and negative controls.

**Checks run.**

* Validator, full configuration (`--per-folder 30 --mutations 500 --math-sweep 200000`, 9 min 40 s):
  * synthetic: 207/207 viewer and 500/500 mutated cases;
  * installed: 2,713/2,713 cases (7,033,092 records in total), 64/64 branch probes reached;
  * texture names: 9,461/9,461 installed and 4,038/4,038 synthetic;
  * math: 0 binary32 differences;
  * negative controls: 4/4 fail;
  * pinned CI groups: equal to the test pins.
* A two-change perturbation of the port fails 11 cases.
* `scripts/local-macos-ci.sh` passes after rebasing on main through #75 (frame loop, actors, audio). It runs `make test`
  (380 run, 35 skips), the viewer build, machprof and the audit. Earlier counts were 315/28 after the character, terrain and
  network merges, and 274/23 before any rebase.
* Integration with #73/#74:
  * `mu_frame`, `mu-frame`, `mu-frame-window` and `mu-render actor` pass their textures to the scene, and the rasterizer gets
    per-texture filter and wrap;
  * the frame's world state uses `mu_meshdraw_state_defaults`;
  * the draw-time option is now `--client-time MS`, because `--time` is the actor/character animation time in seconds.
* `make -C native all viewer` builds with `-Werror`.
* Private native tests: all 49 pass with `MU_RECOVERY_INTEGRATION=1` and the evidence paths from `main-exe-study` (321 s; the
  mesh-draw execution test runs the validator at 3 models per folder). Before the rebase, 20 of 20 passed.
* After the rebase:
  * the terrain path uses the GL blend enums of the new `mu_meshdraw_state`;
  * character items pass their own textures to the scene, so bitmap names and component counts are set;
  * a class-1 character renders textured: `meshdraw-character-class1-{soft,gl}.png`, 16 pixels over 8/255.
* `scripts/audit_repository.py` on the staged tree: 0 rejected.
* Local renders: `~/Documents/mu-mac-tools/native/renders/meshdraw-*.png`.
  * Headless GL with `--compare` on Monster05, Sword01, Bonfire01, CR_shield01 and ArmorClass01, plus `0x1000` chrome and
    `0x42` additive variants.
  * At most 23 pixels per 512x512 frame differ from the software path by more than 8/255.

**Corrections to earlier notes.**

* The WIP commit message said the scene setup's fog mode is GL_EXP. It is
  `glFogi(GL_FOG_MODE, GL_LINEAR)` (`0x0184b073`).
* The viewer's previous normal-table placeholder and state reading are replaced by the executed rules.

**Next.**

* Character assembly (Player skeleton, part models, keep-root attachments).
* Find the live callers' flags and model fields (`+0x44`, `+0x94`, `+0xa4..+0xa6`, `+0xca`, `+0xcb`) and any
  writer of sub-object `[4]`.
* Port or verify the CRT x87 trig fallback for arguments of magnitude 90,112 or more.

No game, CrossOver bottle or registry was touched; installed BMDs were read only.

## Native 2D interface layer (NATIVE-UI-001)

Branch `claude/native-ui`, worktree `~/Documents/mu-worktrees/native-ui`. Read
[`research/client-ui-2d.md`](research/client-ui-2d.md) and [`../reconstructed/ui/README.md`](../reconstructed/ui/README.md).

**Checks.** `make test` runs the portable checks (`reconstructed/ui/test_ui.py`, `native/tests/test_native_ui.py`).
`scripts/validate_ui.py --game-root "$MU_GAME_ROOT"` runs the full Unicorn comparison (about 7 min; needs
`native/build/libmuui` for OpenJpeg). Live reference captures and renders stay local under
`~/Documents/mu-mac-tools/native/renders/ui/`.

**Next:** reconstruct the legacy server-select window (`CServerSelWin`, `0x01075554`, created by
`CreateLoginScene` `0x011e2dc0`) with CButton/CWin and its server-name text, then the MENU/CREDIT window, to
complete the server-select screen over the 3D login world.

## Native window layer: server select and credits (NATIVE-UI-002)

Branch `claude/native-ui2`. Read [`research/client-ui-widgets.md`](research/client-ui-widgets.md).

**Checks.** `make test` runs `reconstructed/ui/test_ui_widgets.py` and the server/credits checks in
`native/tests/test_native_ui.py`. `scripts/validate_ui_widgets.py --cases 120` runs the full Unicorn comparison
(a few minutes). Renders and live captures stay local under `~/Documents/mu-mac-tools/native/renders/ui2/`.

**Next:** the character-select windows (`CreateCharacterScene` `0x011e2f2a`: `CCharSelMainWin` `0x009a492e`,
the server message box `0x010750e1`), `CUIMng::Update`'s focus and docking (`0x011e3143`, `0x011e3823`), and the
GFx layer (MENU/CREDIT/EXIT buttons).

## In-game interface: GFx boundary, item grid, item pass, tooltips (NATIVE-HUD-001)

Branch `claude/native-hud`. Read [`research/client-hud.md`](research/client-hud.md).

**Checks.** `make test` runs `reconstructed/hud/test_hud.py` and `native/tests/test_native_hud.py` (synthetic game
root). `scripts/validate_hud.py --sections grid,slots,pass,item3d,html,format --cases 100` runs the Unicorn
comparison; `MU_GAME_ROOT` makes the format section use the installed itemtooltiptext formats (never written out).
Renders and live captures stay local under `~/Documents/mu-mac-tools/native/renders/hud/`.

**Next:** the tooltip builder `0x00f0eb44` as a whole (price, set/socket/excellent blocks, name colours) and the
remaining formatter types; RenderObjectScreen `0x016c2d82`/RenderPartObject `0x017e63f4`; a capture of the routine
that fills the item render-info map `0x06fbb624` (true scale); native windows fed by the GFx boundary.

## Client data tables (NATIVE-DATA-001)

Branch `claude/native-data`. It adds the following:

* `reconstructed/data`: table codecs and a 45-entry loader catalog with exact decode-unit schedules.
* `native/core/mu_data` and `native/build/mu-data`: list, dump, item-models, model, decode and mpr.
* `scripts/validate_data_tables.py` and `scripts/validate_item_models.py`.
* Portable tests: `reconstructed/data/test_data_tables.py` and `native/tests/test_native_data.py`.
* Private tests: `tests/test_data_tables_private.py`.

[Finding](research/client-data-tables.md).

**Checks run:**

* `make test`: 288 run, 25 private skips, all OK on macOS.
* Private: both validators and the private native data test pass against MuMatrixKit. Reports are under `evidence/client-data-tables/`.
* `scripts/audit_repository.py`: 0 rejected. No game data or decoded output is committed.

**Next:**

* Name the `mu_item_fields` from their consumers (inventory size, requirements).
* Locate the skill/minimap/movereq loaders.
* Lang.mpr text needs the package password, which is behind the protection boundary.

## JSON effects (NATIVE-FX-001)

Branch `claude/native-effects`, worktree `~/Documents/mu-worktrees/native-effects`. Read
[`research/client-effects.md`](research/client-effects.md) and
[`../reconstructed/effects/README.md`](../reconstructed/effects/README.md).

**Checks.** `scripts/validate_effects.py --mutations 1500 --frames 60` (private captures, `--game-root`): 1,870 cases,
0 mismatches, 44 matched client divide faults (`--only REGEX` reruns selected cases). Portable:
`reconstructed/effects/test_effects.py`, `native/tests/test_native_effect.py`. Renders stay local in
`~/Documents/mu-mac-tools/native/renders/effects/`.

**Next:** map the EffectManager (creation by name, lists, parenting, owner tint, frustum culling) and the callers
that attach effects to characters, skills and world objects; then draw effects in the native viewer and frame loop
over the real terrain.

## Walking around the world (NATIVE-WORLD-001)

Branch `claude/native-world`, worktree `~/Documents/mu-worktrees/native-world`. Read
[`research/native-world.md`](research/native-world.md) and
[`../reconstructed/movement/README.md`](../reconstructed/movement/README.md).

**Checks.** `scripts/validate_movement.py --cases 1000 --mutations --game-root "$MU_GAME_ROOT"` (private
captures), portable `reconstructed/movement/test_client_movement.py` and `native/tests/test_native_world.py`.
Renders stay local in `~/Documents/mu-mac-tools/native/renders/world/`.

**Next:** compare the native walk with a live in-game capture; reconcile with the parallel `native-path` path-finder
port; port the path finder's target-area branch and the
weapon/mount cases of SetPlayerWalk/SetPlayerStop (or adopt the NATIVE-ACTOR-001 tables).


## A living native world (NATIVE-WORLD-002)

Branch `claude/native-world2`. Read [`research/native-world-alive.md`](research/native-world-alive.md).

**Checks.** `scripts/validate_hero_sound.py --cases 10000` and `scripts/extract_effect_classes.py --emit-c` (private
captures), portable `reconstructed/audio/test_hero_sound.py`, `reconstructed/actors/test_effect_class_table.py` and
`native/tests/test_native_world2.py`. Renders and the WAV stay local in `~/Documents/mu-mac-tools/native/renders/world2/`.

**Next:** a live window-only reference capture of Lorencia for a side-by-side (the character now lives on MTM-1;
check its location first); the bone matrix path `0x0129fd4f` for effects; NPCs assembled from part models; the
SND_Play sites of monsters, skills and NPC voices; the zoom-mode global `[0x0bdb5880]`.

## Character select (NATIVE-CHARSEL-001)

Branch `claude/native-charsel`. Read [`research/client-character-select.md`](research/client-character-select.md)
and [`../reconstructed/charsel/README.md`](../reconstructed/charsel/README.md).

**Checks.** `scripts/validate_charsel.py --cases 1000 --mutations`, `scripts/validate_charsel_window.py --cases 120
--mutations` and `scripts/validate_camera.py --only move_camera_record` (private captures); portable
`reconstructed/charsel/test_charsel.py` and `native/tests/test_native_charsel.py`. Renders and the live capture stay
local in `~/Documents/mu-mac-tools/native/renders/charsel/`.

**Next:** decode EncTerrain94.obj (marker positions, the pedestal and scenery), port the scene-5 character pick and
`0x009a5029`, draw the 2D layer in the window front end, and reconstruct the GFx character list boundary.

## Item attributes and table layouts (NATIVE-DATA-002)

Branch `claude/native-data2`. It adds the following:

* `reconstructed/data/item_attributes.*`: named Item.bmd attributes, plus C for max durability `0x00ccc5b0` and the warehouse/repair bans.
* `reconstructed/data/table_layouts.*`: record layouts for Item.bmd and 27 tables, each field with an evidence class.
* `mu-data`: named JSON dumps, `item ITEM_BMD CODE` and `layouts`.
* `scripts/validate_item_fields.py`.
* Tests: `reconstructed/data/test_item_attributes.py`, `native/tests/test_native_data.py` and the private `tests/test_data_tables_private.py`.

[Finding](research/client-item-attributes.md).

**Checks run:**

* The private validator: 604,981 comparisons, 0 mismatches. Report under `evidence/client-data-tables/`.
* Synthetic tests and `make test`.

**Next:**

* Reconstruct the requirement routine `0x00ccf659`, the ItemConvert bonus formulas (FormulaData evaluator `0x0117b5eb`) and the price routine `0x0169320b`.
* Trace consumers for the data-only layouts (Muun, Mix, Quest).

## Effect layer (NATIVE-FX-002)

Branch `claude/native-fx2`. Read [`research/client-effect-manager.md`](research/client-effect-manager.md).

**Checks.** `scripts/validate_effect_tree.py --mutations 600 --clones 400 --scenes 300 --frames 30` (private captures,
`--game-root`): 1,670 cases, 0 mismatches. Portable: `reconstructed/effects/test_effect_tree.py`,
`native/tests/test_native_effect.py`. Demo: `native/build/mu-effect scene "$MU_GAME_ROOT" --world 0 --demo --out x.png`.

**Next:** decode the map-object and Muun effect tables, attach effects to native characters (bones), move the scene
pass into the frame loop and the OpenGL viewer.

## Scene flow, offline (NATIVE-SHELL-001)

Branch `claude/native-shell`. Read [`research/client-scene-manager.md`](research/client-scene-manager.md) and
[`../reconstructed/scene/README.md`](../reconstructed/scene/README.md).

**Checks.** `scripts/validate_scene.py --cases 1000 --loading-ui-cases 120 --mutations` (private captures): 7,000 cases
+ 120 loading-screen cases, 0 mismatches, 8 planted mistakes detected. Portable: `reconstructed/scene/test_scene.py`,
`native/tests/test_native_shell.py` (`mu-shell` over synthetic data; the private test runs the demo session over the
installed client). Captures stay local in `~/Documents/mu-mac-tools/native/renders/shell/`.

**Next:** draw the World95 login world behind the server list (record camera, like character select); reconstruct
the main-scene init and the startup loader's steps; replace the offline session with the network layer once that is
in scope.

## GFx interface through Ruffle (NATIVE-GFX-001)

Branch `claude/native-gfx`. Read [`research/native-gfx.md`](research/native-gfx.md).

**Build.** `native/gfx/fetch-ruffle.sh` (Ruffle `nightly-2026-10-17`, commit `061b39b0…`, into `$MU_GFX_DEPS`;
Temurin JDK if no `java`), then `native/gfx/build-mugfx.sh` (Rust via rustup; `mugfx`, `mugfx-shot`,
`native/build/mu-gfx-window`). Not part of `make test`; CI skips the Ruffle test.

**Checks.** `native/tests/test_native_gfx.py`: 10 portable tests, plus 2 private ones with
`MU_RECOVERY_INTEGRATION=1`. `gfx_inventory.py` gives the inventory and `ruffle_survey.py` the 179-movie
survey. Renders are local in `~/Documents/mu-mac-tools/native/renders/gfx/` (`proto/`, `survey/`).

**Next:** AS2 polyfills or Ruffle patches for `onReleaseAux`, `hitTestDisable` and the CLIK focus extensions.
Then decode `DefineCompactedFont`, register device fonts and wire keyboard/IME. Make the integration zero-copy
(per-window viewports, shared textures). Wire CharacterInfoFrame and the item-hover tooltip.

## Ambient life and weather (NATIVE-ENV-001)

Branch `claude/native-env`. Read [`research/client-environment.md`](research/client-environment.md) and
[`../reconstructed/environment/README.md`](../reconstructed/environment/README.md).

**Checks.** `scripts/validate_environment.py --cases 400 --ticks 60 --mutations` (private captures): 400/400 cases,
94/94 probes, 10/10 mutations. Portable: `reconstructed/environment/test_environment.py`,
`native/tests/test_native_env.py` (private part: installed target worlds). Renders stay local in
`~/Documents/mu-mac-tools/native/renders/env/`.

**Next:** a live window-only capture of Lorencia/Noria to confirm the invisible-leaf reading; RenderObject
`0x016d4fe4`, RenderBodyShadow `0x012bc07a` and CreateSprite/CreateParticle for the shadows, glows and splashes;
the Icarus dragons and the Devil Square/Chaos Castle rain.

## GFx interface in the native client (NATIVE-GFX-002)

Branch `claude/native-gfx2`. Read [`research/native-gfx2.md`](research/native-gfx2.md).

**Build.** `native/gfx/fetch-ruffle.sh` (now also applies `native/gfx/ruffle-patches` on a worktree
`$MU_GFX_DEPS/ruffle-061b39b0c3ec-mu`), then `native/gfx/build-mugfx.sh` (libmugfx, mugfx-shot,
`native/build/mu-gfx-window`). mu-world/mu-client build without Rust: the layer `dlopen`s libmugfx
(`MU_GFX_LIB` overrides the path). Movies: `gfxconvert.py --bridge --transparent --var _root.isClient=true
--fontconfig English --font-subset latin` for main, InventoryFrame, InfoPopup, CharacterInfoFrame, chat.

**Run.** `native/build/mu-world --game-root "$MU_GAME_ROOT" --gfx DIR [--gfx-open inventory,character]`
(I/C/Enter/1-0/Esc, mouse); `native/build/mu-gfx-window --gfx DIR [--headless-gl|--headless] [--scale 2]
[--bench --open] [--readback] [--full-stage]`. `MU_GFX_LOG=FILE` logs every callback and invoke.

**Checks.** `native/tests/test_native_gfx2.py` (14 tests; Ruffle ones skip without mugfx). Renders local in
`~/Documents/mu-mac-tools/native/renders/gfx2/`.

**Next:** `loadBitmapFromLib` and the data/image movies (hotkey icons), RenderItem3D models over the item
windows, the expanded inventory and shops, the GFx layer in mu-client's world scene, double-buffered surfaces.

## The client's HUD movie, icons and item models (NATIVE-GFX-003)

Branch `claude/native-gfx3`. Read [`research/native-gfx3.md`](research/native-gfx3.md).

**Build.** `native/gfx/fetch-ruffle.sh` (now 7 patches) and `native/gfx/build-mugfx.sh` (mugfx ABI 3). Movies:
convert `base ExternalBase ImageData Icons main Chat Tooltip Popups ItemDurability AlarmFrame topmenu bufflist
hudPlayerName hudMap hudNotice InventoryFrame InfoPopup CharacterInfoFrame` with the NATIVE-GFX-002 options.
Without `base.swf` the layer keeps the stand-alone main/chat players.

**Run.**

* `native/build/mu-world --game-root "$MU_GAME_ROOT" --gfx DIR [--gfx-open inventory,character]`: item models,
  skill.bmd icons. `MU_GFX_NO_ITEM_MODELS=1` and `MU_GFX_SINGLE_BUFFER=1` turn those features off.
* `native/build/mu-client ... --gfx DIR`.
* `native/build/mu-gfx-window --gfx DIR [--double] [--standalone]`.

**Checks.**

* `native/tests/test_native_gfx3.py`: 12 tests.
* `scripts/validate_gfx3.py --cases 40 --mutations`: needs Unicorn (`tools/python`) and the captures
  (`MU_CLIENT_TEXT`/`MU_IMAGE_DATA` or `evidence/`).
* Renders are local in `~/Documents/mu-mac-tools/native/renders/gfx3/`.

**Next.**

* Feed the remaining HUD movies: bufflist with buff icons, hudMap, hudPlayerName, Tooltip/Popups,
  ItemDurability.
* The expanded inventory and the shops, with item models.
* Reconstruct the client's window-hotkey key scan and the armour-part height rule (`0x06fbc830`).
* Crop the base movie's view to its visible parts.

## Dropped items, labels, pick-up, monster voices (NATIVE-ITEMS-001)

NATIVE-ITEMS-001 (branch `claude/native-items`) reconstructs the client's items on the ground
([finding](research/client-ground-items.md)).

**What.**

* `reconstructed/items`: packet 0x20 `0x0122c216`, CreateItem `0x016daa27`, ItemObjectAttribute `0x016da00b`,
  ItemAngle `0x01802a66` and the name builder `0x017ea422` (lifted by `scripts/items_static.py`), MoveItems
  `0x017ea1aa` + sparkle `0x017f7290`, RenderItems `0x017e9495`, TestFrustrum `0x016ccc14`, SelectItem `0x016b4fc0`,
  label colours `0x00c84f00`; static readings of the hudPlayerName label path (addItem, per-frame anchor, Alt
  setItemView), MoveHero's pick-up case, space-bar pick-up, delete/answer handlers.
* Monster hurt/death sounds: `mu_monster_shock`/`mu_monster_die` (`reconstructed/combat`) over
  `reconstructed/actors/monster_sound_table.h` (`scripts/actor_static.py --emit-sounds`), wired in `mu_combat`.
* `native/core/mu_items.*` + mu-world/mu-walk: demo drops from kills, fall/land/sparkle, item render passes, labels,
  click/space pick-up, Alt, `--item-script`. The sparkle uses NATIVE-JOINT-001's Shiny01 particle kind; label
  strings use NATIVE-LANG-001's GlobalText/skill/NPC tables when `MU_LANG_DIR` is set.

**Checks.** `scripts/validate_items.py --cases 3000 --heavy-cases 300` (Unicorn, `tools/python`, captures under
`evidence/`): 22,200 cases, 0 mismatches; `reconstructed/items/test_items.py`, `native/tests/test_native_items.py`
(portable; private parts with `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`). Renders are local in
`~/Documents/mu-mac-tools/native/renders/items/`.

**Next.**

* Feed hudPlayerName (addItem/removeItem/setItemView) through NATIVE-GFX-003's interface instead of the native
  overlay, and put picked-up items into the inventory grid.
* Trace the item OBB (`+0x31c`) and the ray test `0x018500bf`; the model getter's texture folder for armour.
* Wire the set-item prefix/tier tables (ItemSetType/ItemSetOption) for exact label texts; resolve the special
  models' files; use NATIVE-LANG-001's EnchantEffect colours for the item glow.
* A short live check of label colours and drop sizes when a safe spot with drops is available.


## Fidelity pass: lights, item models, item labels (NATIVE-FIDELITY-001)

Branch `claude/native-fidelity`. Read [`research/client-fidelity.md`](research/client-fidelity.md).

**What.** `mu_rc_character_light` (RenderCharacter's light block), `mu_env_body_light` (RenderObject's body light on
the ambient creatures), `mu_hud_object_screen` (RenderObjectScreen: Player pose and per-group height for armour,
InvenItemAnimation, the `0x26f2` remap), `reconstructed/items/item_sets` (the set manager and its prefix lookup),
`special_models.h` (the item-model loader's AccessModel calls); `scripts/live_lang_to_plain.py` writes
`pentagram.tsv`, `invenanim.tsv`, `legendary.tsv`, `cashsets.tsv`, loaded by `native/core/mu_lang`. Wired into the
hero (`mu_walk_place`), `mu_env.c`, `world/world_gfx_game.c` and `mu_items.c` (labels go through the shared
`core/mu_label` path). `--item-script` drops take an optional set-bits field.

**Checks.** `scripts/validate_fidelity.py --sections env_light,object_screen,special_models,lang_tables,set_prefix
--game-root "$MU_GAME_ROOT" --snapshot "$MU_LANG_SNAPSHOT"` and `scripts/validate_renderchar.py ... --sections light`
(Unicorn, `tools/python`): 9,398 cases, 0 mismatches over six families (hero light 855, creatures 226, RenderObjectScreen 3,000, special models 45, Lang lookups 370, set prefix 4,902), every negative control detected. `native/tests/test_native_fidelity.py` (portable; private parts with
`MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`, `MU_LANG_SNAPSHOT`). Renders are local in
`~/Documents/mu-mac-tools/native/renders/fidelity/`.

**Next.**

* The glow branch of the light block (`0x0139bcdc` classes) and RenderCharacter's later light rewrites (PK colour).
* The hero pointer in character select (scene 5's 0.5 + object light).
* RenderItem3D's 27 special codes, so the remaining special models reach the inventory.
* A live label check with an ancient item when a safe spot with drops is available.
## Other players (NATIVE-PLAYERS-001)

Branch `claude/native-players`. Read [`research/client-remote-players.md`](research/client-remote-players.md) and
[`../reconstructed/players/README.md`](../reconstructed/players/README.md).

**What.** `reconstructed/players/remote_players.*` (the class byte, ChangeCharacterExt with the wing switch, item
level and class skin, the ride state, the move packet 0x3d, MoveCharacters' remote step; static: the viewport
record and creation, the character create defaults, destroy / DeleteCharacter, the store packets and setStore);
`native/core/mu_world_players.*` (the demo server from `native/world/lorencia-demo-players.txt`, the client side in
the session, the plates through `mu_names` with the new `mu_names_set_store` / `MU_HN_OP_STORE` and the GFx
`setStore` invoke); mu-world `--players FILE`, `--no-players`, `--player-range N`; mu-client `--players FILE`.

**Checks.** `scripts/validate_players.py --cases 1000 --negative 60` (Unicorn, `tools/python`, captures under
`evidence/`): helpers 768 + 1,000, equipment 1,000, move 1,000, step 1,000 cases, 0 mismatches, 7/7 planted
mistakes caught (report `evidence/native-players/report-01.json`). Portable: `reconstructed/players/test_remote_players.py`
(10), `native/tests/test_native_players.py` (9 + 1 private). Renders stay local in
`~/Documents/mu-mac-tools/native/renders/players/` (`gl1/`, `lorencia-players.mp4`, `lorencia-players-town.png`,
`lorencia-players-store.png`, `soft1/`).

**Next.** Trace the equipment change packet 0x45 end to end; draw the helper (pet / mount) models and the ride pose
states; player hover (setTopMovie) and selection; a live capture of a crowded town to compare plates and chrome sets;
replace the demo server with the network layer when it exists.

## Pets and mounts (NATIVE-HELPERS-001)

Branch `claude/native-helpers`. Read [`research/client-helpers.md`](research/client-helpers.md) and
[`../reconstructed/helpers/README.md`](../reconstructed/helpers/README.md).

**What.** `reconstructed/helpers` (the angel's bugs, the mount manager's classes, moves, action map, rider action, lift
and render; `mount_classes.h` is generated by `scripts/validate_helpers.py --sections mount_class --emit-classes`);
`native/core/mu_world_helpers.*` (models, owners, host services, draw; the rider hooks `ride_hook` / `riding` /
`place_offset` in `mu_walk` and `mu_world_players`, ChangeCharacterExt's recorded calls as the players' helper
events); mu-world/mu-client `--helper NAME|CODE [--helper-state N] [--no-helpers]`; the players file's `pet=`, `ride=`,
`ride_state=`.

**Checks.** `scripts/validate_helpers.py --bug-cases 1000 --cases 1000 --negative 60 --mutations` (Unicorn,
`tools/python`, captures under `evidence/`, about four minutes): 8,639 cases, 0 mismatches (report
`evidence/native-helpers/report-02.json`). Portable: `reconstructed/helpers/test_helpers.py`,
`native/tests/test_native_helpers.py` (private Lorencia case with `MU_RECOVERY_INTEGRATION=1`, `MU_GAME_ROOT`). Renders stay
local in `~/Documents/mu-mac-tools/native/renders/helpers/` (`showcase/`, `t-*`, `players1/`).

**Next.** The data-driven pet process `0x00b990b0` (petdata.bmd, Demon / Spirit of Guardian / Rudolph / Panda /
Skeleton) and the Dark Raven; the equipment change is opcode 0x25 (`0x01228b60`, not 0x45, which is the transformed-player
viewport `0x0122f1b6`): run it through mu_world_players; the later mounts' class moves and after-pass visuals; the
hero's helper from the inventory; a live capture of a rider and an angel for a side-by-side.

## Helper visuals, pets and mounts (NATIVE-HELPERS-002)

Integrated verified FX work without retaining the unverified WIP snapshot. Native now draws the 24 functors,
Shining Tail sparkles/mist/claws/runes/tail emitter, Ghost Horse aura/claws/breath and both eye trails, Dark Horse
ring and Fenrir lightning/paw marks. Flying bones include object origin; flashes have their real mount owner.
Shared models are reposed per owner; bone bounds use the loaded skeleton size. Mount instance IDs and visual state reset on teardown, including viewport re-entry and immediate replacement. Pets and Dark Raven are included
(`client-pets.md`, `client-dark-spirit.md`); the Preview picker exposes them.

Checks: `validate_mount_visuals.py --cases 300` (7,200 functors + 1,200 class cases); particles create/move/render
3,800 each; joints create/move/render 1,800 each; skill_fx create/move/decal 1,500 each; full helpers 1,000-session
run with 6/6 mutations. All equal; planted mistakes caught. Reports: ignored `evidence/native-helpers2/*-final.json`,
`mount-visuals-finish.json`; synthetic owner/pose/bounds regression in `native/tests/helper_fx_host.c`. Research:
[client-helper-visuals.md](research/client-helper-visuals.md). Renders local under
`~/Documents/mu-mac-tools/native/renders/helpers2/` (`final-shining-tail/`, `final-ghost-horse/`,
`final-shining-tail-every-frame/`, `finish-fenrir-blue/`); prior live capture left Nighty dismounted safely and closed.

Next: recover the alternate signed-integer terrain grid before drawing shock rings in worlds 0x18..0x1d/0x24
(the client adds 400 to those heights; native skips them); port other later/rare/transformed classes' own effects
(functors already covered), optionally Muun, and feed the helper from inventory. No protection or network-login work.
