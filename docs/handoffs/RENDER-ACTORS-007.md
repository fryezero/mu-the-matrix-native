# RENDER-ACTORS-007

## Result and census

The world actor renderer consumes 138 further generated bounded fixture plans:
53 NPCs, fifteen ordinary weapon assemblies and seventy constructor-state
selectors. They span 108 registered model indices and 99 exact body files.
The 39 earlier plans and 550 ACTORS-006 plans remain separately checked.

| Native body classification | Before | After |
|---|---:|---:|
| Checked bounded body plan | 589 | 727 |
| Incomplete/unverified special passes | 355 | 217 |
| Refused by the loader | 80 | 80 |
| Fixture selector contexts | 1,024 | 1,024 |

Selectors include aliases and repeated defaults; they do not count unique
creatures or establish whole-client fidelity. An opener alone never admits
an actor. The opener CSV's `checked_group_body_contexts` counts these checked
callers separately from opener extraction.

## Implemented group and evidence

The frozen ACTORS-006 remainder and its final decisions are published in
[actor-group-decisions.csv](../research/actor-group-decisions.csv). The
[refined groups](../research/actor-missing-plan-groups.csv) still partition
all 905 originally incomplete selectors, including the 550 checked by 006.

| Refined missing plan | Before | Still incomplete | Admitted |
|---|---:|---:|---:|
| NPC whole-body caller/pass/native plan | 84 | 31 | 53 |
| Ordinary right weapon/link | 58 | 54 | 4 |
| Ordinary both weapon/link | 33 | 22 | 11 |
| Ordinary left weapon/link | 13 | 13 | 0 |
| Sword caller plus equipment | 3 | 3 | 0 |
| Constructor subtype | 44 | 0 | 44 |
| Constructor blend mesh | 22 | 0 | 22 |
| Constructor hidden mesh | 3 | 0 | 3 |
| Constructor blend mesh/light | 2 | 1 | 1 |
| Other appearance, bitmap, caller and lifetime groups | 93 | 93 | 0 |
| Total | 355 | 217 | 138 |

Equipment including sword callers falls 107 to 92. The fifteen assemblies are
right-hand classes 13/26/28/29 and both-hand classes
23/33/35/86/92/98/115/121/127/140/430. All admitted selector lists and the
remaining per-row reasons are in the linked CSVs.

[Research section 14](../research/client-actors.md#14-npc-constructor-state-and-ordinary-link-groups-render-actors-007)
records the instruction addresses, shared verifier and limitations. The new
verifier reuses the constructor, caller and asset checks from ACTORS-005/006.
Each candidate executes its own original constructor under world-0/rand-0
fixture inputs and declining map processors. Its model, scale, class byte,
slots and actual constructor writes must agree with the compiled registration.
Only the proved subtype/hidden/blend/light state is carried into this group;
other unexplained writes, kind/light overrides, joints and cloth stay excluded.

NPC OpenNpc runs in worlds 0/3/2/51/18/30. Complete synthetic model/action
bytes and every ordered AccessModel/OpenTexture argument must match. Identical
repeated texture opens remain in the comparison. Extra models, bitmaps and
unsupported action/model writes reject the candidate. Native loads the exact
registered file and Npc texture directory, then independently resolves and
decodes every mesh bitmap to compare pixels, dimensions, components and sampler
state with its actual upload.

Every admitted full RenderCharacter entry runs 28 contexts over worlds
0/3/2/51 and actions 0..6, carrying its constructor writes. Both sprite
emitters execute. The RenderObject reader runs eight world/alpha contexts
per selector and requires exact flags 2, requested alpha, blend mesh/light,
hidden mesh, bitmap -1, zero UV and translate 1 with 0.4/0.8/0.2 transform
factors. Native stores OBJECT +0x60/+0x68/+0x74/+0xa8 and both render backends
consume the guarded plan. Eight original draw streams per model prove the
ordinary body pass independently.

Weapon rows additionally prove original hand bones, exact item registration,
raw-level draw streams, per-hand isolated poses, preserved body bones and six
native world/action contexts. The monster caller supplies its raw level byte;
the adapter decodes it for the existing native API. All fifteen admitted rows
have raw byte zero, so no general nonzero-level equivalence is claimed. The
trial using the Player shift expectation was rejected and is not delivery
evidence. No item recipe/table or effect-consumer implementation changes.

`validate_actor_groups` has 8,451 positive checks:

| Family | Checks |
|---|---:|
| Original defaults | 2 |
| Weapon native contexts | 90 |
| Original link controls | 104 |
| Weapon draw streams | 72 |
| Exact plans and exclusions | 1,026 |
| Generated table/decision/group reproduction | 3 |
| Constructors | 138 |
| Openers | 828 |
| Whole callers | 3,864 |
| Actual native assets, textures, geometry and alpha | 138 |
| Original body reader | 1,104 |
| Distinct-model draw streams | 864 |
| Additional varied callers | 200 |
| Sword request audit | 12 |
| Type-226 counter/request audit | 6 |

All 21 compiled controls are caught, with zero stops. Thirteen C-plan
controls retain their results at `d53c7df3`: the C source, header and generated
table are unchanged. Eight native controls replay against the strengthened
host at `fbee6e46`, 37.54 s command, including the new write-on-refusal control.

Final consumer review finds that both render callers ignore the helper's
return value. The old helper writes group options before model/scale/weapon
rejection, so a false return alone does not exclude the plan. Sentinel probes
on classes 49/65 reproduce this: all four guards return zero, but only the
effect guard leaves options untouched, 2.70 s command. The fix moves every
option write after all context checks. Classes 13/49/65 then pass all four
byte-for-byte unchanged-option probes, 2.63 s command. The full per-row host
now verifies model, scale, effect and attachment rejection this way. Its
synthetic attachment changes only the loaded-mask bit and is never drawn.

The earlier twenty-control run serialized the C and native translation
controls under one key; the registry correctly rejected nineteen distinct
results. Distinct names and a 3.05 s two-control replay (243.20 s command,
240 s wait) restored twenty results. The final twenty-first control targets
option mutation on scale refusal. No assertion or expected control count is
weakened. Later positive replays run without mutants. Native output is still
published only after cleanup, and absent plans are refused before file reads.

## Verification

All 33 final affected validators pass, **252,538 checks**, zero failures,
errors or skips. The guard correction replays fifteen rows at `fbee6e46`:
119,976 checks, 398.85 s command with zero resource wait. Eighteen results
retain unchanged used inputs from the commits in the table. The full 8,451
new-row checks now include four untouched-option probes per admitted selector.
The registry recheck passes 8,451 positives / 21 distinct controls in 0.10 s.
Guard-delta selection takes 193.85 s including 120 s wait. Current PR selection
remains 33 of 250 rows, 279.49 s including 210 s wait.

After INNER-005 batch 117, 27 rows replay at `4e02b38e`:
214,718 checks, 1,095.71 s command wall including 390 s resource waiting.
Six results retain unchanged inputs: app-polish1 at `e51eba07`; app-polish2/4,
audio-combat, viewport-monsters and worlds-fog at `ebcbb2da`.
The input-delta selector takes 128.03 s including 30 s wait. Current PR
selection remains 33 of 250 registry rows, 158.69 s including 60 s wait.
The fixture party host's IR analysis lacks MU_SESSION_SEED, so conservative
fallback selections remain in the replay rather than being discarded.

After AUDIO-005 batch 116, 32 rows replay at `ebcbb2da`: 251,786 checks,
740.31 s command wall. App-polish1 retains its unchanged-input 752-check pass.
That PR selector keeps 33 of 249 rows, 223.28 s including 90 s wait; its
input-delta selector keeps thirty prior rows, 82.63 s including 30 s wait.
The two newly selected audio rows also replay. Conservative fallback rows
remain selected in every wave. No prior result is retained where its used
compiled inputs change.

Before AUDIO-005, all 31 batch-115 rows pass at `e51eba07`, 213,223 checks,
680.63 s command wall. The initial same selection passes at `b3edf825` in
602.78 s. Batch-115 input selection takes 62.19 s and its PR-wide selection
446.83 s command including 360 s wait. No prior result is retained where its
compiled inputs change.

| Check | Result | Measured wall |
|---|---|---:|
| Final 138-plan generation | 7,228 trial checks, 108 model indices / 99 files | 269.39 s runtime |
| Initial canonical census regeneration | 727 / 217 / 80 | 8.21 s runtime / 128.21 s command, 120 s wait |
| Initial root build | pass | 14.27 s |
| Batch-115 root build | pass | 16.39 s |
| Batch-116 root build at `9d9caf9a` | pass | 22.40 s |
| INNER-005 root build at `4e02b38e` | pass | 19.28 s command |
| INNER-005 explicit world rebuild | pass | 5.56 s runtime / 35.56 s command, 30 s wait |
| Batch-116 explicit world rebuild | pass; final binary SHA recorded below | 8.68 s runtime / 188.68 s command, 180 s wait |
| Focused portable actor modules | 2 pass / 2 expected private skips | 0.032 s |
| New-row comparison and controls before key correction | 8,451 positives; controls caught, registry count rejected | 251.2 s row / 251.34 s command |
| Corrected two-control replay | 2/2 caught, twenty distinct results; registry recheck passes | 3.05 s runtime / 243.20 s command, 240 s wait |
| Guard-order root build at `fbee6e46` | pass | 11.55 s command |
| Guard-order explicit world rebuild | pass | 6.46 s runtime / 96.46 s command, 90 s wait |
| Guard-order default after-side refresh | 230/230 preceding hashes identical | 97.70 s runtime / 97.75 s command, zero wait |
| Guard-order red/green probes | rejected writes reproduced, then all four no-op guards pass | 2.70 s red / 2.63 s green command |
| Refreshed native controls | 8/8 caught, zero stops; 13 C-plan controls retained | 37.54 s command |
| Guard-order affected positive replay | 15/15 pass, 119,976 checks; eighteen unchanged passes retained | 398.85 s command, zero wait |
| Final compiled-control registry recheck | 8,451 positives / 21 distinct controls, pass | 0.10 s command |
| Guard-order permitted portable delta | PENDING_RESULT | PENDING_WALL |
| Guard-order private 8d reduced | PENDING_RESULT | PENDING_WALL |
| Initial affected private validators | 31/31 pass, 213,223 checks | 602.78 s command |
| Batch-115 affected private validators | 31/31 pass, 213,223 checks | 680.63 s command |
| Batch-116 affected private replay | 32/32 pass, 251,786 checks; one unchanged pass retained | 740.31 s command |
| INNER-005 affected private replay | 27/27 pass, 214,718 checks; six unchanged passes retained | 1,095.71 s command, 390 s wait |
| INNER-005 permitted portable delta | 1,419 pass / 337 expected skips, zero failures/errors | 415.2 s runner / 549.30 s command, 60 s wait |
| INNER-005 private 8d finish | PENDING_RESULT | PENDING_WALL |
| Initial permitted portable selection | 1,525 pass / 339 expected skips, zero failures/errors | 390.1 s runner / 568.26 s command |
| Initial private 8d reduced | 4/4 pass, zero skips | 448.08 s runtime / 568.19 s command, 120 s wait |
| Batch-115 permitted portable delta | 1,541 pass / 347 expected skips, zero failures/errors | 371.3 s runner / 612.48 s command, 120 s wait |
| Post-audio default delta | 230/230 prior after-side hashes identical | 71.26 s runtime / 161.34 s command, 90 s wait |
| Post-INNER-005 default delta | 230/230 prior after-side hashes identical | 77.08 s runtime / 287.20 s command, 210 s wait |
| Batch-116 permitted portable delta | 1,474 pass / 345 expected skips, zero failures/errors | 449.9 s runner / 784.21 s command, 270 s wait |
| Batch-116 private 8d reduced | 4/4 pass, zero skips | 427.80 s runtime / 637.94 s command, 210 s wait |
| Final canonical census reproduction | 727 / 217 / 80; both CSVs byte-identical | 8.94 s command, zero wait |
| Final publication audit | PENDING_RESULT | PENDING_WALL |
| Pre-INNER-005 documentation consumers | pass, one expected private skip | 9.11 s command |
| Final documentation consumers | PENDING_RESULT | PENDING_WALL |

Command walls include resource waiting and selection where stated. Heavy
commands use nice 10, build jobs <=4 and validator/portable jobs 2. No full
lane gate runs; the steward owns the combined gate.

**8d reduced:** the first portable selection has 181 items / 169 private
native items. The batch-115 delta selection has 185 / 171. Both exceed forty,
so private finish runs the only native modules changed/added by this lane,
`native.tests.test_actor_groups` and `native.tests.test_actor_plain`, from repo
root with `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`. Portable
runs explicitly exclude `native/tests/test_native_app.py`, leaving 180 and
184 permitted items respectively. The AUDIO-005 delta selects 181 items /
173 private native items, runs 180 after the same app-module exclusion, and
also uses 8d reduced. INNER-005 selects 176 items / 169 private native items;
175 run after the app-module exclusion, followed by the same reduced actor modules.

| Steward validator | Checks | Wall | Tested commit |
|---|---:|---:|---|
| `validate_actor_composites` | 1,427 | 8.8 s | `fbee6e46` |
| `validate_actor_groups` | 8,451 | 192.9 s | `fbee6e46` |
| `validate_actor_monsters` | 1,437 | 40.2 s | `fbee6e46` |
| `validate_actor_plain` | 21,437 | 154.5 s | `fbee6e46` |
| `validate_actor_recipes` | 1,669 | 108.6 s | `fbee6e46` |
| `validate_app_polish1` | 752 | 30.1 s | `e51eba07` |
| `validate_app_polish2` | 1,028 | 6.4 s | `ebcbb2da` |
| `validate_app_polish4` | 10,485 | 39.6 s | `ebcbb2da` |
| `validate_audio_callers` | 5,528 | 4.8 s | `fbee6e46` |
| `validate_audio_combat` | 19,548 | 38.8 s | `ebcbb2da` |
| `validate_audio_domains` | 2,544 | 23.3 s | `fbee6e46` |
| `validate_audio_items` | 3,000 | 4.3 s | `fbee6e46` |
| `validate_audio_kubera` | 1,000 | 1.3 s | `4e02b38e` |
| `validate_audio_monsters` | 38,315 | 17.8 s | `4e02b38e` |
| `validate_audio_objects` | 4,000 | 5.7 s | `4e02b38e` |
| `validate_audio_objects4` | 10,093 | 8.4 s | `4e02b38e` |
| `validate_charsel_items` | 8,817 | 7.9 s | `4e02b38e` |
| `validate_icarus_c2` | 8,400 | 18.3 s | `4e02b38e` |
| `validate_inventory_fx` | 8,017 | 7.1 s | `4e02b38e` |
| `validate_item_callers` | 6,013 | 1.2 s | `4e02b38e` |
| `validate_items_ui` | 8,517 | 10.0 s | `4e02b38e` |
| `validate_movement` | 6,614 | 45.7 s | `fbee6e46` |
| `validate_render_effects16` | 424 | 4.1 s | `fbee6e46` |
| `validate_render_effects17` | 618 | 6.9 s | `fbee6e46` |
| `validate_render_effects18` | 540 | 1.2 s | `4e02b38e` |
| `validate_render_effects19` | 400 | 0.8 s | `4e02b38e` |
| `validate_render_effects24` | 226 | 2.3 s | `fbee6e46` |
| `validate_render_effects25` | 202 | 8.5 s | `fbee6e46` |
| `validate_render_effects26` | 348 | 10.1 s | `fbee6e46` |
| `validate_render_effects28` | 630 | 1.7 s | `4e02b38e` |
| `validate_render_effects31` | 66,051 | 180.8 s | `fbee6e46` |
| `validate_viewport_monsters` | 1,963 | 16.7 s | `ebcbb2da` |
| `validate_worlds_fog` | 4,044 | 10.8 s | `ebcbb2da` |

Steward validators: validate_actor_composites, validate_actor_groups, validate_actor_monsters, validate_actor_plain, validate_actor_recipes, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_audio_callers, validate_audio_combat, validate_audio_domains, validate_audio_items, validate_audio_kubera, validate_audio_monsters, validate_audio_objects, validate_audio_objects4, validate_charsel_items, validate_icarus_c2, validate_inventory_fx, validate_item_callers, validate_items_ui, validate_movement, validate_render_effects16, validate_render_effects17, validate_render_effects18, validate_render_effects19, validate_render_effects24, validate_render_effects25, validate_render_effects26, validate_render_effects28, validate_render_effects31, validate_viewport_monsters, validate_worlds_fog

Mutants needed by steward: none. Use the canonical private environment from
repo root. Every validator above runs privately with zero skips. Main through
batch 115 `df57ab8b` is integrated at `1b194a04`; AUDIO-005 batch 116
`8844d3e9` is integrated at `9d9caf9a`. The `ebcbb2da` checkpoint changes
documentation only after that merged source. INNER-005 batch 117
`d3ec9950` is integrated at `4e02b38e`; `48c2d9bc` changes documentation only.

## Identity and proof renders

The ACTORS-006 baseline at `a9eef31f` and the batch-115 after side each have
an explicit `make -C native -j4 world`. Their SHA-256s differ:

- Before: `935d306d28ab496e0683fce3ab1ceece4c9cdb5f6a9e7be14035ec997549c490`.
- After: `1e855e5234feadb27b80a33682f7193b54c4c38a0ed7584949960353dd45ca12`.

The one complete default sweep has 46 views / 230 files per side, at native
1722x1048, 25 frames, saving frames 0/24. Baseline rendering takes 64.17 s;
after rendering takes 87.87 s. The after explicit world rebuild takes 7.50 s
runtime / 487.50 s command including 480 s wait. Only output-prefix paths
are normalized. No draw_all or live-time sweep runs.

Exactly 182/230 hashes match: 90/92 PNGs and 92/92 OBJECT/light dumps.
All 45 unaffected views retain identical images. Remain's two PNGs change.
All 46 reports append the same two bitmap availability flags, 97 to 99,
preserving their old prefixes; only Remain also changes particle/counter/hash
fields. The comparison asserts that exact change set and bitmap prefix.
These differences agree with incoming EFFECTS-031; there is no default
actor-related image delta. Report hashes are not claimed identical, and no
original-pixel fidelity score is inferred.

AUDIO-005 advances the final world binary to SHA-256
`e4f3d72c8d9c439fc7a14e2c0166fac20baa43891013aa2e158755bc06151d8c`.
After its explicit rebuild, the same default after side is refreshed once:
230/230 hashes match the batch-115 after side exactly, 71.26 s runtime /
161.34 s command including 90 s wait. The saved before baseline is not rerun.

INNER-005 advances the rebuilt world SHA-256 to
`ba79bf503665e710dc1d96ffe233bdde18fa066aa6ee0680cb90b70a5ddbe327`.
Its compiled-input after-side refresh also matches all 230 preceding hashes,
77.08 s runtime / 287.20 s command including 210 s wait. The actor sources
remain unchanged; the single saved before baseline is reused.

The guard correction rebuilds the world at SHA-256
`32575718b0dd19107e59aaca91946fbba37860c7f8ea998c638d7384e4889961`.
Its after-side refresh preserves all 230 preceding hashes, 97.70 s runtime /
97.75 s command with zero wait. Valid admitted render contexts keep their
output; rejected contexts now leave caller options untouched.

The proof after side uses the batch-115 binary `1e855e52`; its actor sources
are unchanged by AUDIO-005. Twenty-four before and twenty-four after GL
proof scenes use world 0,
DemoKnight at 128,124, DemoActor at 129,125, direction 5, 640x480, two frames,
fixed clock 123456 ms, hidden names and no extra players/environment/particles/
helpers/audio. They cover every new weapon assembly, unique constructor-state
signatures, NPC representatives and an empty control. Both contact sheets
were visually inspected. Before takes 19.24 s runtime / 139.33 s command
including 120 s wait; after takes 26.34 s.

Every new weapon changes pixels: 13 = 168, 23 = 486, 26 = 31, 28 = 467,
29 = 78, 33 = 641, 35 = 1,131; 86/92/98/115/121/127/140/430 each = 692.
Class 49 changes 4,788 pixels and class 65 changes 542. Certification/state
representatives 144/149/224/226/647/231 preserve their image, as expected.
The empty control changes zero pixels. Temporary proofs/reports are removed
at cleanup; no new private input is needed by later lanes.

## Limits and next work

These plans certify bounded authored fixture contexts. Initial blend mesh -1,
blend light 1 and zero UV are fresh-body fixture inputs; original hidden-mesh
and subtype defaults are statically visible. Pooled-object reuse is not
proved. Pose/body-light input, buff tint, after-visual, custom/registry handlers
and shadows retain named harness boundaries. No whole-world, buff, temporal,
shadow/fade or original-pixel equivalence follows.

All 217 incomplete selectors retain a specific reason. Class 546 lacks seven
mesh textures; 918 lacks two. Classes 22 and 866 reach RGB draws without the
candidate host's color4 alpha callback, so their effective alpha remains
uncertified; the assertion stays strict. Extra bitmaps, EffectManager, joints,
cloth/world appearances, extra/changed/suppressed callers and secondary NPC
assemblies keep their missing consumer/caller proof.

Classes 1/5/10 retain the original post-link sprite request, bitmap 0x7ef7,
size 1.4, across four fixture worlds. Their link recorder does not establish
weapon-pose/sprite placement, so all three stay incomplete. Classes 595/635
retain six type-226 counter/request controls, with two consumer-lifetime
refusals counted separately from the eighty loader refusals. Their special
idle passes also remain incomplete. EFFECTS-033 owns the consumer files.
Classes 374/642 still need companion lifetime, 378 cloth/aura and 617 its exact
startup file. Those four loader refusal boundaries remain unchanged.

Next work can batch the remaining equipment/NPC groups by their recorded
failure, or complete one of the named appearance, bitmap or lifetime readers.
Do not infer filenames, network/spawn state, statistics or opaque protection.

## WIP checkpoints and delivery

Current WIP: 138 admissions, census, main-through-batch-117 builds,
33 validator results and permitted portable work pass. Final consumer review
finds group options written before model/scale/weapon mismatch rejection;
the render callers ignore the return value. The strengthened host uses
sentinel options and requires all bytes unchanged for model, scale, effect
and attachment mismatch. Before the fix, classes 49/65 return four refusals
but preserve options only for the effect guard: `[0,0,1,0]`, 2.70 s command.
The production writes now follow all checks. Root build passes in 11.55 s;
classes 13/49/65 pass all four untouched-option probes in 2.63 s command.
All eight native controls pass in 37.54 s, zero stops; thirteen unchanged
C-plan controls are retained. Left: post-build affected checks, rebuilt
after-side identity and final publication. Next: select and run the affected
delta with the stronger guard checks. The input-delta selector keeps fifteen
rows (193.85 s including 120 s wait); the PR selector keeps the same 33 of
250 rows (279.49 s including 210 s wait). The rebuilt default after side
matches all 230 hashes, 97.75 s with zero wait. The fifteen-row replay passes 119,976 checks in 398.85 s; the registry
recheck passes 8,451 positives and all 21 distinct controls in 0.10 s.
Next: finish the portable/private delta and publication audit. The prior final-private wrapper run is stopped
before source edits; it is not used as final evidence. No ready entry exists.

Pushed checkpoints include `99409933`, `5425914e`, `d53c7df3`, `b3edf825`,
`967d83e4`, `73ccdc0d`, `e51eba07`, `4863ad70`, `9f096a80`,
`9d9caf9a`, `ebcbb2da`, `74f5c2e6`, `9d088724`, `4e02b38e`,
`48c2d9bc`, `acfeb704` and `fbee6e46`. Early provisional row
counts are superseded by the final 138-row result. PR #396 was the initial
stack; its merged main ancestry is retained. The final delivery changes
only documentation after the tested source. Final push and PR precede the
single ready entry; no push follows it. The steward owns merge and combined
validation. Own scratch/renders/builds, worktree and local branch are removed
at readiness; the remote branch remains. Publication pending final delta checks.
