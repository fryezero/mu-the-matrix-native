# RENDER-ACTORS-004

## Result

Five authored world NPC classes now draw their complete selected secondary body
parts: 230, 248, 250, 253 and 255. They share the recovered Female, Man and Girl
skeletons, scale 0.9 and OpenNpc animation rates. Parts skin against the NPC
pose and use the ordinary textured draw pass with actor alpha. The zero-mesh
base does not acquire Player armour shadows. Canonical placements are unchanged.
The standalone `mu-render actor` command still renders only the base model;
use world fixtures for these assembled NPCs.

The [class census](../research/actor-construction-census.csv) enumerates every
selector in the 0..1023 authored-fixture range. The
[opener inventory](../research/actor-opener-census.csv) covers 601 monster and
147 NPC selectors. [Research section 11](../research/client-actors.md#11-construction-census-and-composite-town-npcs-render-actors-004)
records the original instruction addresses, categories, selected model indices,
method and limits. `scripts/actor_census.py --classes <csv> --openers <csv>
--composite-ready` regenerates both inventories under the canonical private env.

| Native body classification | Before | After |
|---|---:|---:|
| Checked bounded body plan | 28 | 33 |
| Incomplete or unverified special passes | 916 | 911 |
| Refused by the loader | 80 | 80 |
| Fixture selector contexts | 1,024 | 1,024 |

These are fixture contexts, including repeated/default selectors, not unique
creatures or a visual-fidelity percentage. Of the original constructor contexts,
963 resolve and 61 remain unresolved. Six existing EffectManager recipes resolve
before that core lookup. Refusals are 55 unresolved core contexts without an
override, 13 no-opener rows, eight NPC rows lacking file registration and the
four ACTORS-003 boundaries. Construction tags overlap and must not be summed.
The opener inventory has 711 extracted, 29 no-own-file and eight unresolved
mesh-state results; 16 openers request 42 secondary model loads. Its 142 bitmap
and 959 sound service calls are calls, not unique decoded assets.

## Implemented group and evidence

| Class | Skeleton | Selected files |
|---|---|---|
| 230 | Man01 | ManHead01, ManUpper02, ManGloves02, ManBoots01 |
| 248 | Man01 | ManHead02, ManUpper02, ManGloves02, ManBoots02 |
| 250 | Man01 | ManHead01, ManUpper01, ManGloves01, ManBoots01 |
| 253 | Girl01 | GirlHead01, GirlUpper01, GirlLower01 |
| 255 | Female01 | FemaleHead02, FemaleUpper02, FemaleLower02, FemaleBoots02 |

All paths are original `Data/Npc/<name>.bmd` registrations. The opener maps 22
variants; constructors select 15 distinct files. These five classes are the
largest shared group in the audited secondary-opener set. The demo source
explicitly called out their missing assemblies. Of the nine monster secondary
openers, only type 226 has classes in the current extracted table (595/635),
neither in shipped demo placements; the other leads need action/debris/effect
ownership before an extra model load could render correctly.

`validate_actor_composites` has 1,427 checks:

| Family | Checks | Evidence |
|---|---:|---|
| kind_default | 2 | Original CreateCharacter default kind, retained by constructor |
| recipes | 1,026 | Five constructor comparisons; 1,021 excluded selectors |
| openers | 29 | 22 original secondary file registrations; seven invalid indices |
| render | 240 | Whole RenderCharacter entry, ordered part plan and alpha, worlds 0/3/2/51 |
| draw | 120 | Generic RenderObjDraw stream, 15 selected models, eight states each |
| native | 10 | Five classes in worlds 0/3, actual files, textures, pose, scale, alpha and refusal controls |

Thus 389 original-instruction/loader comparisons, 1,028 authored recipe/file
exclusions and ten native contexts. RenderObject is a named base-body/pose
recorder. Stateful world services explicitly decline in these synthetic
fixtures. No original pixel or temporal equivalence is claimed. Native contexts
require a zero-mesh skeleton, positive selected geometry, zero missing textures,
advancing matching frames, requested alpha and no draw refusals. The ten compiled
mutants cover admission, kind, filename, load, scale, slot, tick, frame, alpha
and draw; all ten were caught, none by an emulator stop.

## Verification

Verification is being finalized at main integration `13b0e1c0` (through
ITEMS-UI-001, main `626abce1`). Actor production behavior has not changed since
`95d9f97c`; later source changes add checks and correct one branch-end comment.
Root build and explicit world rebuild are separate commands. All heavy commands
use nice 10, build jobs at most four and validator/test jobs two. Resource waits
are included where stated. No full lane gate or existing-row mutant reruns.

Initial checks at `d835c137`: all 24 affected validators pass, 107,832 row
checks, zero failures/errors/skips, 494.3 s including selection. The new row's
once-only mutant run passes 10/10, 49.7 s. Portable affected run: 1,495 tests,
1,246 passed and 249 expected private skips, zero failures/errors; 440.1 s runner,
650.5 s command including selection and a 120 s resource wait.

Integration checks at `aa330645`: 22 selected validator rows pass, 106,052
checks; 769.4 s including a 360 s resource wait and selection. Two unchanged
app-polish rows retain their initial passes. Portable affected run: 1,773 tests,
1,481 passed, 292 expected skips, zero failures/errors; 384.8 s runner, 596.8 s
command including selection and a 120 s wait. Selection exceeded 40 native
items, so **8d reduced** runs only `test_actor_composites` and
`test_actor_recipes` under `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`
from repo root: 6/6 passed, no skips, 66.5 s plus a 120 s wait.

World/audio main integration `1d0c3c2c`: all 18 overlapping rows pass,
70,012 checks, 325.9 s including selection. All eight symbol fallbacks remain.
The superseded portable follow-up was stopped when ITEMS-UI-001 landed; it is
not counted as a pass. The final portable run covers both main deltas.

FINAL_CHECKS_PENDING

## Identity and proof renders

The one-time before default sweep at ACTORS-003 base `a2398637` covers 46 views,
92 PNGs, 92 geometry dumps and 46 normalized reports (230 files), 61.0 s.
Only report output-directory prefixes are normalized. The world executable was
explicitly rebuilt before hashing. Before binary SHA-256:
`1be079965a22399f472ca6c7d0f657fa67b62e46b9a47ba6f6c5e7b100d34440`.

Before WORLDS-INNER-002 landed, the distinct after binary
`b3bcddd6409b8988554051c2e980e02cfd0e737624e2eef235ddb6176452f161`
replayed all 230 hashes identically, 95.0 s. WORLDS-INNER-002 then intentionally
changed Elbeland and Swamp. The final replay is checked against that known
main delta and records the final binary separately below.

FINAL_IDENTITY_PENDING

The five proof scenes use a world-0 authored fixture with DemoKnight and
DemoActor, no extra players/environment/particles/audio, hidden labels,
640x480, two frames and a fixed start time. Each has a complete textured body.
All five were visually inspected. Initial changed pixels versus the empty
control: 230 = 1,370; 248 = 1,399; 250 = 1,342; 253 = 835; 255 = 1,071.
Six scenes took 6.0 s. Proof frames and private hashes are temporary lane
artifacts under `~/Documents/MTM/mu-mac-tools/native/`; removed at cleanup.
No README images, owner app or live client were touched.

## Limits and next work

Classes 374/642 need companion lifetime; 378 needs cloth/aura; 617 needs an
exact startup file registration. Their refusals are unchanged. None of the
740 completed ordinary opener executions registers model `0x5ba`; eight NPC
openers remain unresolved. This narrows the class-617 lead without proving
absence from every manager/startup path. No filename was guessed.

Generic walking, head/weapon links, buff-driven appearance, fade/shadow parity,
world override state, all special passes and original motion/pixel comparison
remain open. This lane admits five bounded world body assemblies only. Next:
trace the nine monster secondary models into action/lifetime consumers, or
recover class 617's exact registration. Do not treat the opener census as a
count of complete actors.

## WIP checkpoints

Commit/push checkpoints: `95d9f97c` (21:48), `27e9b6f4` (22:17),
`0f0341b4` (22:37), `aa330645` (22:57), `eb5fb34d` (23:19),
`086f3335` (23:40), all on 2026-11-11. Earlier provisional census counts
in those WIP snapshots are superseded by the 33/911/80 table above.
Final validation, audit and PR delivery remain pending at this checkpoint.

Checkpoint, 00:00 on 2026-11-12: main through ITEMS-UI-001 is integrated as
`13b0e1c0`. Six overlapping validator rows pass, 13,276 checks, 220.5 s including
selection and a 120 s resource wait. Root build and explicit world rebuild pass,
241.2 s including 240 s of waits, and 7.9 s. The final combined portable run has
started with 168 work items. Reduced private tests, image replay, final identity,
audit, PR and ready entry remain pending. Main still matches `626abce1`.
