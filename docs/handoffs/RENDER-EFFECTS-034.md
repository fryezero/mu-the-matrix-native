# RENDER-EFFECTS-034

PR-ready verified fixture subset. The steward owns the combined gate and merge.

Branch `claude/render-effects-034` starts from RENDER-EFFECTS-033 `35ae89fe` (PR #403, open when this lane
finished; it already contained main `c5b9d5ca`) and merges main `c255e4dd` (batch 119: MUUN-VISUAL-005,
AUDIO-006) at `7ae65313`. Implementation by Claude Fable 5.2, no subagents, no full lane gate. Heavy work
ran at nice 10, make at most four jobs, two validator/test workers, with load waits.

Orchestrator order during the run: finish the particle/joint/sprite ids as one PR-ready unit; stay out of
`reconstructed/combat` and `native/core/mu_combat.c` (RENDER-EFFECTS-035 owns them); the effect-side ids
go to RENDER-EFFECTS-036 unless time remains. Effect consumers live in `reconstructed/combat`, so none
was taken here.

## Consumer table

[Table (CSV)](../research/render-effects-034-consumers.csv) and
[research note](../research/client-render-effects-034.md): every refused consumer pair known on this
base, with original addresses, requesting producers and refusal counts per fixture scene.

| | Pairs / rows |
|---|---:|
| Refused before (table rows) | 43 |
| Admitted here, verified against the original | 21 (17 particles, 4 joints) |
| Sprite bitmaps bound | 2 (`0x810d`, `0x8003`) |
| Refused after | 20 rows: 2 particles, 18 effect-side rows |

The orchestrator's 22-id list (three world particles, four world joints, eight item particles, five
Muun particles, two sprite bitmaps) was checked id by id against the lanes' handoffs: 21 are done, and
Muun particle `0x8084/28` stays refused. The new native ledger added two pairs refused in **default**
world views, `0x8016/5` and `0x7ef7/11`; both are done.

## Pairs added, by group

| Group | Pairs | Requested by |
|---|---|---|
| Plain particles (6) | `0x8016/5`, `0x7ef7/11`, `0x7f5a/43`, `0x7f5a/47`, `0x7f54/1`, `0x7efa/3` | Swamp of Calmness, Elbeland, tower 39, Muun 377 |
| Item particles (7) | `0x8616/0`, `0x7fe0/10`, `0x84d1/2`, `0x850b/5`, `0x807e/14`, `0x807f/14`, `0x8080/14` | ITEMS-002AA producers `0x0f22`, `0x0f23`, `0x0f25`, `0x24be/0x24bf` |
| Follow particle (1) | `0x855d/2` | ITEMS-002AA producer `0x0f22` |
| Pulse particles (3) | `0x8081/1`, `0x8082/1`, `0x7ef7/19` | Muun mount style and secondary particles |
| Joints (4) | `0x7f7c/8`, `0x7f7c/19`, `0x7fd5/4`, `0x7f7d/11` | Kanturu 37/40, tower 39, Barracks 41 / Refuge 42 |
| Bitmap bindings (4) | sprites `0x810d`, `0x8003`; particle bitmaps `0x8616`, `0x850b` | Muun 376/377; the two new item particles |

One table-driven consumer per group: `reconstructed/particles/consumer34_kinds.inc` (a row per pair with
its form) and `reconstructed/joints/consumer34_joints.inc`; `0x7f54/1` is one line in the existing
Explosion case. `0x7efa/3` sets its blend state and draws no sprite, as the original's subtype table
does. `0x855d/2` follows the retained item-owner point at draw, like the existing `0x810a/0x25`. The world
bitmap table grows 100 to 104 (inserted before Fire03; the Fire06 and rain anchors keep their relative
place). Pool caps are unchanged.

The world particle module now keeps a per-pair refusal ledger (`refused_kinds`, 96 rows, overflow
counted) and reports `{"world_unsupported": [[routine, type, subtype, count], ...], "lost": n}` after the
joint summary line. Totals in `stats` are unchanged.

## Scenes: refusals before and after

Installed read-only game data, demo names only. "Before" is this tree with the lane's consumer files
reverted to `35ae89fe` (main did not touch them); for the world and skill scenes the pre-change ledger
gave the pairs.

| Scene | Refused before | Refused after |
|---|---:|---:|
| Elbeland default view, 25 steps | 2 (`0x7ef7/11`) | **0** |
| Elbeland, draw-all, 61 steps | 32 | **0** |
| Swamp of Calmness default view, 25 steps | 1 (`0x8016/5`) | **0** |
| Swamp of Calmness, draw-all, 61 steps | 64 | **0** |
| Other 44 views, default and draw-all (88 runs) | 0 | 0 |
| Muun 16 with the mount style, 90 steps | 180 (`0x8081/1`, `0x8082/1`) | **0** |
| Muun appearance 376, 90 steps | 720 (sprite `0x810d`) | **0** |
| Muun appearance 377, 90 steps | 102 (90 sprite `0x8003`, 12 particle `0x7efa/3`) | **0** |
| Muun appearance 375, 90 steps | 270 (`0x8084/28`) | 270 |
| Inline world host: Kanturu type 0x69, tower 0x36, 0x2f, Barracks 0x5a | 1 each (joints) | **0** each, joint routed |
| Skill 344 Blood Storm, 100 steps | 1,883 | 1,883 |
| Skills 44, 49, 41 (real sword model) | 1, 1, 5 | 1, 1, 5 |
| Other 27 skill scenes | 0 | 0 |

**Scenes whose refusals reached zero:** Elbeland and Swamp of Calmness (default and draw-all), so all 92
world-view runs are at zero; Muun 16 mount style, Muun 376 and Muun 377; the four inline world joint
cases. The item producers of RENDER-ITEMS-002AA are not on main, so their eight pairs have no scene here;
they are covered by the original comparison and the native fixture. The tower particles are event-gated
(production fixes the sequence inactive) and have no refusals in the sampled scenes.

Proof renders (local, not committed, deleted with the lane's scratch): 17 particle, 4 joint and 4 sprite
fixture images from the native host; the Swamp of Calmness brazier before/after (the flame now draws);
Muun 16 mount, 376 and 377 before/after. All were looked at. The joint fixtures use a uniform test
bitmap, so they show geometry, not the game texture.

## Original proof

`scripts/validate_render_effects34.py`, registry row `validate_render_effects34`, 200 cases per pair and
family: **12,647 checks, 0 mismatches, no original-machine stop**. Create, move and draw of every particle
pair (record fields, ordered calls, `rand()` counts, draw calls; the follow pair also compares the draw's
owner-point position write); `CreateJoint`, `MoveJoint` and `RenderJoints` for the four joints (record,
ordered calls, full GL stream); 26 native host rows (17 particles, 4 joints, 4 bitmap bindings, the
ledger); a 21-row admission census.

**91 compiled mutants, all detected, zero original stops**: three per pair (removed create, changed move,
removed draw), 24 form controls (lifetimes, thresholds, the pulse floor and colour, the follow start and
NULL owner, the arc's turn/jitter/speed, the bolt's far end and jitter) and four native controls (follow
hook, two swapped bitmap files, the ledger). One control was first aimed at the wrong family
(`clud_texture`, draw instead of create) and was corrected and rerun alone; one native control needed a
ledger fixture in the host before it could be detected. No successful control was repeated.

Target SHA-256 `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`, text
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`, data
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.

This proves the stated instruction slices and the native adapter contracts. It is not a claim about
original GPU pixels, the client's shared RNG phase, pool equivalence or which requests a live session
issues.

## Default identity and binaries

Both trees ran `make -C native -j4 world` right before their sweep; hashes were read again after
rendering.

- Before (consumer files at `35ae89fe`): `d9783e95d396df78393d23ad1d00f62be39d321fbaf9d0cfd054b71820862274`.
- After: `@@AFTER_SHA@@`.

Default world draw, DemoKnight, no draw-all, default clock, 640x400, 25 steps sampled at 0 and 24; the
14-view October tour and the 32-view DATA-ACQ-002 tour.

| | Identical |
|---|---:|
| PNGs | 91 of 92 |
| OBJECT/light dumps | 92 of 92 |
| Logs | 46 of 46 |
| Reports | 0 of 46 raw; 44 differ only by the ledger line and the four bitmap slots |

**Views that change, and why.** Swamp of Calmness frame 24: the brazier's `0x8016/5` particle was refused
and now draws (2,667 pixels inside x 24..95, y 0..48; mean RGB difference 0.183 of 255). Its report gains
one created/drawn particle and two `rand()` calls. Elbeland's report gains two created/drawn `0x7ef7/11`
particles and six `rand()` calls; its two saved frames stay byte-identical. Every report gains the
`world_unsupported` line and four loaded bitmap entries at slots 96..99; the rest of each bitmap list is
equal after removing those four. This is native-to-native identity, not original image equivalence.

## Tests changed in other lanes' files

Three expectations followed the new consumers; each is a few lines:

- `native/tests/worlds_inner_host.c`: the four inline joint cases now expect the joint routed and no
  refusal (as RENDER-EFFECTS-031 did for `0x7f7d/8,9,10`); the host's joint hook checks their owner and
  width.
- `reconstructed/joints/test_joints.py`: the four pairs moved from the refused list to the admitted one.
- `native/tests/test_muun_transition.py`: Muun 16's pulse particles now draw and take rotation and size
  from the world's one `rand()` stream, which the transition's own requests advance. The end-frame
  identity of the two runs is now asserted outside the Muun's particle box, plus zero live and drawn
  transition models.

No world object routine, Muun module, item table, actor, UI, audio or combat source file was edited.

## Completed checks and test budget

Commands ran from the repository root with the canonical `private-env.sh`. No full gate.

@@CHECKS@@

**8d reduced:** @@EIGHTD@@

**Packaging exclusion:** only `native/tests/test_native_app.py` was removed from the portable affected
work list, by a task-local wrapper (not committed). No package, signing, install, installed-app journey,
Native Data refresh or README work.

## Steward validators

`private-env.sh` supplies MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_SECTION3, MU_EVIDENCE_DIR,
MU_NATIVE_DATA_DIR, MU_LANG_DIR and the row-specific paths. Run
`scripts/run_validators.py --private --no-mutants --cache --affected origin/main --jobs 2`.
**Mutants: only `validate_render_effects34`, already run once here; none needed from the steward.**

@@VALIDATORS@@

## Limits and next lane

- `0x8084/28` (Muun 375) stays refused: its move reads the owner OBJECT's bones 11 and 18 each step
  (`0x0129f12c`, `TransformPosition` `0x012b6ef1`). The native Muun request carries no owner and the
  particle host has no owner-bone service. Request-side note for the Muun lane: pass the Muun as the
  particle owner and expose its posed bone points; the consumer's create and alpha/scale program are in
  the research note.
- `0x8145/1` (Blood Storm) stays refused: the particle form is recovered (research note), but the combat
  pool has no `0x8145` bitmap row and `native/core/mu_combat.c` was out of bounds. One row plus the pair's
  admission closes it.
- RENDER-EFFECTS-036 list, unchanged: Blood Storm `0x585/0`, `0x586/0`, `0x4b7/1`, blur `0x814b`;
  Crescent `0x49e/0`; Fire Breath `0x8001/0`; tower effects `0x4be/0`, `0x4bf/0`, `0x419/2`, `0x41a/2`,
  `0x4c0/0`, `0x4c1/0`, `0x4c2/0`, `0x4c5/0x4c0`, `0x4c5/0x4c1`, `0x4c5/0x4c2`. New from the ledger: effect
  `0x454` subtypes -1, 1, 2, 3, 4 (Twisting Slash with the installed sword model). The actors' type 226
  effect (classes 595/635) also needs its move/draw/retirement path.
- `0x7f7d/11` with a width below 8 divides by zero in the client; the native modulo helper returns 0
  there. Producers pass 15 times the object scale.
- The item pairs draw once RENDER-ITEMS-002AA's producers merge; recount their scenes then.
- The CSVs that RENDER-ACTORS-008 and RENDER-EFFECTS-035 were to push were checked @@CSV_CHECK@@.
- Eligibility, damage, mana, cooldowns, server keys, packets, protection, live client state and owner
  apps are outside this fixture subset.

## Delivery

Ready for steward after PR publication and the single ready-prs entry; nothing is pushed after that
line. Cleanup removes this lane's scratch (census, traces, proof renders, the exported before-tree and its
build), ignored builds, the worktree and the local branch; the remote branch stays. No new private input
needs retaining. Paths: `~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-034` and
`~/Documents/MTM/worktrees/render-effects-034`.
