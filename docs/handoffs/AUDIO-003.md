# AUDIO-003: offline object callers and audio census

Branch `codex/audio-003`, based on `d4af71dd`, with main `710ac816` integrated.
Offline/static only. No original client, launcher, live service, installed app
or staged app is used or changed. No event feed, request/answer route, protection
analysis, character-power feature or original-process memory write is added.

## Census

The reproducible inventory is `scripts/audio_caller_census.py --report <local>`.
It reads the existing pinned captures through `pins`, with no asset-path or byte
export. [Method, source anchors and limitations](../research/client-audio.md#audio-003-census-and-object-delivery-2026-11-11).

| Owner bucket | Candidates | Existing audio boundary | Added |
|---|---:|---:|---:|
| UI | 20 | 8 | 0 |
| Hero actions and shared hit/attack/death services | 37 | 28 | 0 |
| Skills and shared character/effect timelines | 263 | 18 | 0 |
| Monsters and NPC voices | 781 | 3 | 0 |
| World objects and ambient | 111 | 47 | 16 |
| Items | 9 | 6 | 0 |
| Events and progression presentation | 4 | 3 | 0 |
| Unresolved owner | 755 | 0 | 0 |
| Total | 1,980 | 113 | 16 |

The denominator is the historical direct E8-target scan, reproduced exactly,
not a CFG proof of every candidate. 1,225 have an owner bucket; 755 remain
unresolved. Shared owners are counted once. The nearest MSVC prologue is only a
grouping aid. Exact source references and the existing 48-class vtable table
supply the reviewed classifications. The separate source-reference field says
that a bounded reconstruction mentions the owner, not that all sound branches
are implemented or delivered. 763 monster candidates have no such reference.

The 113 existing boundaries are 76 historical adapters, two AUDIO-002G sites,
32 frame ambient sites, two Crywolf result sites and the earlier hero level-up
site. Credits remains an offline-controller boundary. Conditional event/remote
adapters keep their earlier input limits. AUDIO-003 adds 16 boundaries, giving
129 enumerated sites. This is not a whole-client native completion percentage.
A complete semantic owner census remains open; the 755 unknowns are a refused
research group, not a claim that those sounds are absent.

## Wired and refused groups

The new `native/core/mu_object_audio.h` forwards requests that existing native
routines already selected. Original routine/site/id/object/loop are retained.
The only edit to another runtime file is one include and one added delivery call
in `native/world/parts/objects.c`. World object routines, item tables, particles,
combat aura files and inventory UI are untouched.

| Group | Result and original eligibility |
|---|---|
| Devias doors | Two MoveObject sites, 18 for type 0x56 and 17 for 0x14/0x41/0x58; bounds mode false and distance strictly below 200 |
| Elbeland | Seven OBJECT-owned loop-1 sites, 0x317/0x318/0x319/0x314/0x316/0x315/0x313. Existing type and terrain safe-bit gates remain |
| Uruk 100/101 | Type-20 visual emitter, 0x442, NULL, loop 0, after existing visual eligibility |
| Kardamahal 143 | Six sites, 0x5a6/0x5a9/0x5a7/0x5a8/0x5a4/0x5a5. Types 146/149 require action 2; 150..152 retain signed rand remainder selection; other type gates remain |
| Hero actions, demo monster combat, item drops | Existing verified delivery retained. Shared services already own their once-per-action markers. No added duplicate hook |
| Class monster sound selectors | 763 classified candidates without a bounded native reference remain research leads; their owner bodies/context are not invented |
| Ignis | Two 0x570 sites select different action/frame branches. Existing id-only callback cannot distinguish their provenance; refused |
| Kethotum variants | Ambiguous repeated-id sites need caller context at the audio boundary; refused |
| Kubera stop requests | Existing native consumer is absent. Refusals remain counted; no guessed stop delivery |
| Pickup success, remote results, buffs, transformed contexts, events | Missing or excluded authoritative/domain inputs remain refused |
| Opaque frame interval | 0x01854279..0x018542c2 remains excluded and is never followed |

[Exact sound sites and gates](../research/client-audio.md#wired-object-boundaries).
SND_Play ignores its object. There is no new 3D, attenuation or per-site volume
rule; these sounds use the Effect group. Log key -3 denotes an unkeyed world
OBJECT, and -2 denotes NULL. No pointer is logged.

These object emitters intentionally request sound again while their gate holds.
The existing manager suppresses an already-playing id. No new once-per-action
filter changes the original request stream. Elbeland's loop flag also reaches
the standalone facade now. Session audio drains while disabled; standalone
and detached delivery have no backlog. The adapter consumes no RNG and changes
no object, animation, visual or replicated-state field.

## Music

Static world/zone music already had delivery through `mu_world_sound_frame`,
`mu_audio_host_set_world` and `mu_audio_host_tick`; no competing selector is
added. A native decoded smoke checks eleven segments: pub, Lorencia theme,
Devias church and field, Noria, Dungeon, Atlans, Lost Tower, Aida, Kanturu and
an unscored control world. Requests and synthetic PCM identify the ten tracks.
Repeated same-track frame requests retain the loop. The existing instruction
proof for the frame selector remains unchanged; it is not counted as a new
Unicorn family here. State-dependent event managers retain missing-input cues.

## Verification

The affected validators ran at `ab5839746985d6ae813efac8273ac87d05bb7eec`;
compiled/validator inputs are source commit `c3c8273c`. Final docs do not change
those inputs. The build after integrating main passed in 5.08 s; the earlier
lane build passed in 5.61 s.

- New original caller comparison: 4,000 cases, 1,000 each for Devias, Elbeland,
  Kardamahal and Uruk. Zero mismatches/stops; all 16 source sites reached.
  Devias is the existing bounded world branch, not the whole MoveObject body.
  Other families retain their existing full-body/explicit service boundaries.
  Original return addresses independently supply sites and original arguments.
  The unchanged owning comparisons still check OBJECT, AL where applicable,
  full normalized call order and RNG. Native cues are additionally compared.
- Compiled mutants ran once: 10/10 caught, 15.32 s command wall. They target
  world admission, Devias/Elbeland/action sites, loop, object, Uruk alias,
  random branch, id and ordered multi-request delivery. The production adapter
  is unchanged from checkpoint `1a9a1fed`; later validator edits add independent
  supplemental expectations, explicit original-site coverage and input digests.
- Focused native/private evidence: all added ids decode from read-only installed
  inputs with `--no-options`. Synthetic runtime tests cover original safe gating,
  active-id suppression, nonzero loop PCM after the source ends, Effect mute,
  disabled drains, detached standalone delivery, no replay and independent readers.
  The actual world part delivers Elbeland through the session with equal
  audio-on/off fixture frames. The eleven-zone smoke checks indices and PCM.
- Affected portable run: 125 work items, 1,526 tests, 1,252 passed, 274
  explicit skips, zero failures/errors. Six reported suite groups, including
  120 native modules. Runner wall 410.6 s; command wall 495.72 s including
  selection. The initial banner names the registry's 38 suite directories.
- 8d reduced: 120 native items exceed the 40-item cap. From the repository
  root with canonical `private-env.sh`, the changed native module plus pinned
  census test pass **11/11**, zero skips/failures, **6.34 s** command wall.
  No full lane gate or full private registry ran.
- Affected validators: all seven pass, zero failures/errors/skips, 114.07 s
  command wall including selection. The movement symbol fallback is retained.
  All ran without mutants; no unchanged validator's mutants are repeated.
- Repository audit: **2,194 staged files, zero rejected, 26.26 s** command
  wall. Source/spec self-review passed for provenance,
  callback lifetime, mute/no-replay, original gates/order and owned-path scope. No independent
  reviewer, live fidelity, mixed-output FMOD parity or default capture sweep is
  claimed. Only the synthetic audio-on/off frame control was needed for this
  audio-only change; no before/after identity sweep ran.

### Steward validators

Tested commit `ab5839746985d6ae813efac8273ac87d05bb7eec`.
Canonical environment: source `~/Documents/MTM/mu-mac-tools/native/private-env.sh`
from the repo root. No further mutants are needed for the steward.

Steward validators: validate_movement,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_worlds_g2,validate_render_effects16,validate_audio_objects

| Validator | Cases/checks | Wall seconds |
|---|---:|---:|
| `validate_movement` | 6,614 | 77.0 |
| `validate_audio_callers` | 5,528 | 8.0 |
| `validate_audio_domains` | 2,544 | 31.9 |
| `validate_audio_items` | 3,000 | 5.9 |
| `validate_worlds_g2` | 2,657 | 9.7 |
| `validate_render_effects16` | 424 | 4.3 |
| `validate_audio_objects` | 4,000 | 4.8 |

The 6b review finds the new helper only in the object part, the new native host
and new validator. No existing shared symbol, constant, record layout or table
size changes. The selector's movement fallback is retained.

## Next

Recover the 755 unknown owners individually before admitting their gates. For
monster work, start with the reviewed slot +0x70 selectors and distinguish a
whole missing owner from a bounded source reference. Carry original caller/site
context through the object audio boundary before adding Ignis or ambiguous
Kethotum sites. Stop consumers need an equally explicit command boundary.
No event feed, pickup answer, transformed/buff input or FMOD mixer parity is
inferred from these fixtures.

## WIP checkpoints, completed

`1a9a1fed` was committed and pushed with done/left/next notes at the first
checkpoint. It preserved the census, adapter and small 800-case comparison.
`ab583974` was pushed at 22:02 CST with the full original/mutant/portable results
and the remaining private checks. Both WIP sections are superseded by the green
finish results above. Main was fetched again after the audit and remains
`710ac816`; no further integration or compiled-input rerun is needed.

Local reports are under `~/Documents/MTM/mu-mac-tools/native/scratch/audio-003/`
and ignored `verify-runs/`. They are not future inputs. At PR-ready remove these
outputs, build directories, worktree and local branch; retain the remote branch
for the steward.
