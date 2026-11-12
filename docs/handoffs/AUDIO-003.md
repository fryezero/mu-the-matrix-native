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

Results are being collected at source commit `c3c8273c`. Final docs do not change
compiled inputs. The build after integrating main passed in 5.08 s; the earlier
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
- 8d reduced: 120 native items exceed the 40-item cap. The changed native module
  will run from the repository root with canonical `private-env.sh`, along with
  the small pinned census test. No full lane gate or full private registry runs.
- Affected validators: seven selected, including the movement symbol fallback.
  All will run without mutants; no unchanged validator's mutants are repeated.
- Repository audit and final source/spec self-review pending. No independent
  reviewer, live fidelity, mixed-output FMOD parity or default capture sweep is
  claimed. Only the synthetic audio-on/off frame control was needed for this
  audio-only change; no before/after identity sweep ran.

### Steward validators

Source commit `c3c8273c91df67a17b6e1103cc2c7b7e9a06b4b7`.
Canonical environment: source `~/Documents/MTM/mu-mac-tools/native/private-env.sh`
from the repo root. No further mutants are needed for the steward.

Steward validators: validate_movement,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_worlds_g2,validate_render_effects16,validate_audio_objects

Per-row counts and wall times will be filled after the run.

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

## WIP checkpoint

`1a9a1fed` was committed and pushed with done/left/next notes at the first
checkpoint. It preserved the census, adapter and small 800-case comparison.
Second checkpoint, 22:02 CST: source `c3c8273c` is complete and the affected
portable run passed 1,526 tests with zero failures/errors. Done: full original
corpus, mutants, installed smoke, zone music and actual object-part control.
Left: seven affected private validators, reduced private tests, audit, final
documentation, PR publication and cleanup. Next step: resume those checks when
load is below the resource guard. This checkpoint is not PR-ready; no
ready-prs entry is written.

Local reports are under `~/Documents/MTM/mu-mac-tools/native/scratch/audio-003/`
and ignored `verify-runs/`. They are not future inputs. At PR-ready remove these
outputs, build directories, worktree and local branch; retain the remote branch
for the steward.
