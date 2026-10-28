# RENDER-ITEMS-002 part 9

Base `00bb4d9`, isolated branch/worktree `codex/render-items-002i`, issue #226.
Checkpoint `6b88dc0` is pushed. Only this lane is edited and built. No live client/launcher or hosted workflow is used.

## Coverage and implementation

Bounded bodies increase **662 to 769 of 1,674**, adding **107 types**: 43 armour,
five weapons, one wing and 58 survey `pet/item` types. All **17/17 skins** remain.
Consumed links increase **fourteen targets/nineteen types to fifteen/twenty**.
All 1,691 survey memberships agree with compiled admission. Historical shapes,
ranks, stop counts and service addresses are preserved. Fifty-five more shapes
are complete, including seven-type ranks 21, 36, 46 and 49; 192 shapes are complete.
Visibility is model-index inference, not measured wear frequency.

The four armour shapes use the existing rank-5 cosine pulse and a level-gated
scrolling overlay. The shared pulse helper preserves signed conversion/remainder
and SSE rounding. The helper's optional raw-level word is present only on the
high-quality glow path. Both raw level and effective glow level matter: a record
can force glow level 9 on a raw level 0 item without enabling the overlay. Flag
0x400 may clear glow before a record overrides it. Recipes distinguish both base
flag variants and both overlay states; other phases keep their existing meaning.

The generator screened the remaining survey in rank order. Of 133 additional
probe-fitting candidates, independent full-function comparisons rejected 54.
Only the other 79 are admitted. Prior rejected ancient-tail candidates remain
refused. Fitting probes alone do not establish coverage.

Shield 0x16fa, target **0x012dbc1e..0x012dc0ee**, emits nine 0x7ef7 flares on
bones 1..9, scale 1.5, colour `(abs(sin(time*0.001))+0.1)*(0.8,0.3,0.8)`.
Its unused common intensity still consumes one random call. The existing native
saved-pose adapter consumes it, including missing-bone and full-pool behavior.
Only its admission hook changed; no effect/particle/joint, perf/mesh/scene,
per-world object or audio implementation changed. New frame paths allocate no storage.

## Checks and evidence

The executable/text/data identities in the [finding](../research/client-render-items.md)
remain unchanged. `validate_item_coverage.py --mutations` owns the new families
and its manifest/private test. The strict run passes **31,724 cases, zero mismatches**:

| Family | Cases | Mismatches |
|---|---:|---:|
| Complete bounded body streams, 107 types times 292 states | 31,244 | 0 |
| Signed/remainder/conversion clock boundaries, four representative shapes | 80 | 0 |
| Full shield callers, clocks/random sequences/hand variants | 400 | 0 |

All **9/9 separately compiled mutants** are caught. Detection counts: cosine
period 8,215; overlay quality 407; overlay raw-level threshold 305; overlay scroll
2,230; mesh index 26,944; object alpha 23,088; ancient phase 307; shield absolute
value 200; shield bone 400. Both generated tables reproduce from pinned instructions.
Combined with the inherited run below, **46,716 original-instruction comparisons**
have zero mismatches and **18/18 mutants** are caught. The C-to-C preservation
checks below are separate from that instruction count.

Portable renderchar: **51 tests, twelve explicit private-input skips**. Native
character renderer: **11 tests, one installed-client skip**. The new native test
checks two sprites with a three-bone model and nine with all required bones.
Saved translations, missing bones and full pools pass through the existing host.
All **643 existing generated rows** retain identical six recipes and scalar/flag
metadata after re-indexing. Compiled before/after draws for all **679 existing
body/skin types** match in **21,728 cases**, zero mismatches.

Inherited part 8 passes **14,992 cases, zero mismatches, 9/9 mutants**, including
11,856 rank-5 lighting/record/clock cases, 2,336 armour cases and 800 link cases.
Both generated tables reproduce from the pinned instructions.

Six inspected PNGs compare three authored scenes before/after. The ordinary
control stays byte-identical, framebuffer SHA-256
`44061fca1b7785a415ca53e4091b7eb9f71aec5fc65e6e32db0eb27c7eb4d3e2`.
The body scene replaces one refusal with zero, increases passes 21 to 27 and
changes 6,255/120,000 pixels. The shield scene adds nine sprites and changes
17,059 pixels with authored textures. Additive untextured geometry saturates
white; these images do not establish material or live-client fidelity.

Self-review against the brief and repository evidence rules found the native
fixture's missing shield bones, corrected with separate bounded/full-bone cases.
The original stream comparisons corrected the raw/effective-level guard and
excluded the 54 failing fitting candidates. A phase-selection mutant was
ineffective because those two new recipe phases are equal; the compiled ancient
phase mutant tests an actual difference instead.
 A temporary
candidate table deliberately fails the historical refusal tests; the rejected
candidates are removed and the production suite passes. The initial broad gate
ran during edits, and the next preflight retained the older shield-test assertion
in an already-imported module. Neither is a release result. The corrected native
suite passes in a fresh process; the final full gate runs after integration under
the lock.

## Remaining work and coordination

**905 bodies remain.** Rank-5 owner effects still need readable OBJECT bones
35/26, particles 0x84e2/0x83de, 0x7fdd sprites, level-9 overlays and pose-state
handling. These are listed for RENDER-EFFECTS-003 coordination; this lane does
not edit that lane's consumers. Further links include owner-dependent Laser/17
at 0x012c8571 and shared clock/bone state at 0x012c91fe. Prior record/buff,
selection/shadow/mesh-override, hero-instance, owner/random, model-mapping,
NewUI and external Box of Luck limits remain. Muun/nested map-object tables stay deferred.

Local scratch/renders are scoped to `mu-mac-tools/native/{scratch,renders}/render-items-002i/`.
After merge, release the lock and delete both folders, lane build/verification
outputs, worktree and local branch. Shared Python/evidence links are never staged
or traversed during cleanup. No new local input needs retention.
