# CHARSEL-ITEMS-001

PR-ready, branch `codex/charsel-items-001`. Started from main `a2ad8814`, merged documentation main
`9d6ce467`, then item-body main `3732f82a` as `003b561f8ec316621e57b3675f86938a0c1eb43c`.
Final compiled checks below ran at that merge. Later lane changes are documentation only.
No subagents, live client, installed application changes or full lane gate.

## Result and scope

Selection now uses the existing item renderer for the authored equipment records already carried
by APP-POLISH-008's demo list. The adapter loads the record's item textures and bitmap overrides,
then forwards its type, level and excellent flag. Body parts retain ext; linked hands and wings
force ext to zero, as the original linked caller does. File-only items and class parts keep the
previous selection mesh/texture path. Only the shown entry draws.

Two saved GL draws, frames 0 and 11, ticks 100000 and 100452, quality 5:

| Demo | Item/model type | Authored appearance | Mesh passes | Supported effects / refused |
|---|---|---|---:|---:|
| Nightfall | Staff02 `0x14e7` | +7 | 4 | 0 / 0 |
| Ironclad | Cookery Short Sword `0x0b2a` | +9 excellent | 8 | 8 / 0 |
| Ironclad | Small Shield `0x16e6` | +7 | 4 | 0 / 0 |
| Ironclad | Wings of Heaven `0x22e7` | level 0 | 2 | 0 / 0 |
| Windleaf | Bow02 `0x12e7` | +7 | 4 | 0 / 0 |
| Spellblade | Sword05 `0x0aea` | +7 | 4 | 0 / 0 |
| Crownlord | Mace01 `0x0ee6` | +7 | 4 | 0 / 0 |

Every admitted demo item has zero special fallbacks. The standalone tool's new `selection_items`
rows report the admitted fields and cumulative passes/effects; file-only reports remain unchanged.
`record_entry` is a list index, distinct from the character slot. The synthetic test uses slot 7
at entry 0 and slot 3 at entry 1 and checks that undrawn entries accumulate no passes.

Owned changes are in `native/charsel/`, one native test module and one validator. Public/internal
charsel header additions and tool reporting are added lines only. The shared charsel controller
and audio adapters are untouched. No authored edit to `mu_renderchar.c`, item tables/generators,
actor/combat/world code, Makefiles or pins. The validator manifest has one appended row. Incoming
#361 table changes were merged unmodified.

## Recovered callers and evidence

[Full finding](../research/client-character-select.md#charsel-items-001-authored-equipment-levels-in-selection).
Pinned restored text capture09 SHA-256
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`; data/flag/feature pins are
in `scripts/pins.py`.

| Address | Static observation, with argument slices instruction-compared |
|---|---|
| `0x01857aee` | Selection draws the shown live/visible character through RenderCharacter, with select argument 0. |
| `0x0136a374` | Body slots descend 5..0 at CHARACTER `+0x1c4 + slot*0x3fc`. |
| `0x0136a490` | Part lookup reaches GetModel `0x00eaa8cf`; its item loader `0x00cd558e` supplies the existing client texture rules. |
| `0x0136a6d7` | Ordinary body RenderPartObject caller forwards signed level byte `<<3`, boolean excellent and ext. |
| `0x017e7960`, `0x017e7997` | RenderPartObject forwards these fields to RenderObjDraw; existing INVENTORY-FX comparison covers both sinks. |
| `0x0136c428` | Ordinary hand RenderLinkItem caller forwards type, level and excellent. |
| `0x0139eefc` | Ordinary wing RenderLinkItem caller forwards type, level and excellent. |
| `0x012bdb19` | RenderLinkItem clears model lighting; the adapter applies this in a draw-local model view. |
| `0x012c6a83` | Linked RenderObjDraw caller encodes level `<<3`, boolean excellent, ext 0. |

`validate_charsel_items`: 5,000 body argument cases, 3,000 linked argument cases, 48 fallback/boundary
checks, one selection call-site check and 768 full ordered mesh/color stream comparisons. Total
8,817, zero mismatches. The mesh matrix covers body/hand types, all levels 0..15, quality 0..5,
excellent 0/1, body ext controls, two fixed clocks and scene state 5. The declared renderchar
service recorders remain the comparison boundary; this is not a whole RenderCharacter comparison.

Seven independently compiled header mutants were caught: model base 256, level 240, excellent
256, body ext 159, linked ext 96, unset record 280, invalid slot zero 2 detections. Every anchor
matches exactly once; compilation failures do not count as detections.

## Checks and budget

Commands ran from the repository root with nice 10, make at most four jobs and validator runners
two workers. The canonical private environment is
`. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`; render/GL pixel controls additionally use
`MU_LANG_DIR="$MU_NATIVE_DATA_DIR/lang"`. Wall times exclude resource cooldowns and are not
performance acceptance measurements. The initial baseline root build passed but was untimed.

| Final check | Result | Wall |
|---|---|---:|
| Root build after main merge, `make -j4` | Pass, no warnings | 10.91 s |
| Affected portable, `MU_RECOVERY_INTEGRATION=0 MU_GATE_JOBS=2 ... run_test_suites.py --affected origin/main` | 112 work items; 1,142 tests, 952 passed, 190 expected skips, zero failures/errors | 450.37 s including selection; 370.2 s test wall |
| Affected private validators, `--private --no-mutants --cache --affected origin/main --jobs 2` | Eight rows pass, zero failures/errors/skips | 345.64 s including selection |
| New row's compiled mutants, `--private --cache --only validate_charsel_items --jobs 2` | 8,817 comparisons, zero mismatches, 7/7 caught | 14.5 s row; 14.66 s command |
| Private 8d reduced plus world-entry/demo-record controls | 12/12 pass, zero skips | 17.15 s |
| GL target rebuild | Pass | 0.29 s |
| Staged-source audit | 2,146 staged files, zero rejected | 22.67 s |

The eight rows below ran at `003b561f8ec316621e57b3675f86938a0c1eb43c`. This is also the exact
post-build affected selection; movement is a retained symbol fallback. No row was dropped.

| Validator | Cases | Wall |
|---|---:|---:|
| `validate_meshdraw` | 14,619 | 83.6 s |
| `validate_model_edge` | 954 | 240.7 s |
| `validate_movement` | 6,614 | 101.6 s |
| `validate_audio_callers` | 5,528 | 11.9 s |
| `validate_audio_domains` | 2,544 | 59.6 s |
| `validate_audio_items` | 3,000 | 10.2 s |
| `validate_app_polish4` | 10,485 | 63.1 s |
| `validate_charsel_items` | 8,817 | 17.8 s |

Mutants ran once at `2a1702906248d91ae4a6db014637176ad400b9cf`. The helper header, its included
ABI headers and validator are unchanged through the texture fix and latest-main merge; the
mutant comparisons exercise the pure record adapter. Therefore no repeat of those seven
mutants was needed. The normal full-count row reran against the merged renderchar library.
No mutants were run for unchanged validators.

**8d reduced:** the native selection is 109 modules, above the 40-item cost cap. The canonical
private run covers `test_charsel_items`, plus explicit existing
`test_native_shell.PrivateDemoSessionTests` and `test_app_polish8.PrivateRecords`. It checks the
new real-texture pixel regression, original argument/mesh smoke, selection admission/fallback,
world entry/re-entry, hero slot/class/world and existing world equipment records. The portable
selection also includes main's updated native-renderchar consumer. The steward owns the full
combined gate.

Pre-merge completed runs are superseded for shared compiled inputs: portable 1,141 tests,
951 passed/190 skips, 358.62 s; eight validators pass, 259.09 s; private 12/12, 18.26 s. The earlier
pre-texture run also passed but did not establish visible glows. No passing check is attributed
to a resource-blocked launch.

## Render and identity proofs

Native GL, 640x400, no UI, the demo list, each of five selected slots, 12 fixed-clock steps,
`--every 11`: two saved draws at ticks 100000/100452. No map-object argument was added to these
isolated character proofs. Before comes once from main `a2ad8814`; final after uses the merged
lane. Item textures and EnchantEffect tables are read-only inputs. These are native renders,
not original-client captures.

All ten authored-record PNGs change; all ten file-only PNGs are byte-identical to main.

| Selected demo | Changed pixels, frame 0 | Changed pixels, frame 11 |
|---|---:|---:|
| Nightfall | 363 | 374 |
| Ironclad | 808 | 1,498 |
| Windleaf | 151 | 138 |
| Spellblade | 382 | 454 |
| Crownlord | 263 | 254 |

Level 0 versus +9 changes 455 pixels at frame 11; +9 versus +9 excellent changes 447 pixels.
The repeat excellent scene matches both PNGs byte for byte. All 26 selection/control PNGs
are also byte-identical to the completed post-texture-fix proofs before #361's merge.
Selection before 16.72 s; final after 16.78 s across two completed/resumed commands.
Final sword controls 3.75 s; final combined byte comparison 0.94 s.


The isolated same-code sword controls keep the rest of the demo outfit fixed. Pass counts are
2 / 6 / 8 at level 0 / +9 / +9 excellent. All three create eight supported effects with zero
refusals. A repeat excellent scene is byte-identical at both clocks. The private pixel regression
also removes shield/wings and requires level and excellent to change pixels independently.

An initial control had correct pass counts but zero changed pixels, even without wings and
shield. The viewer's model-folder texture lookup left the sword white. The selection-only
`mu_item_textures_character` call fixes that failure. The obsolete after-images are excluded
from the final results and removed during cleanup. This is why pass counts alone were not used
to claim visible glows.

One default-draw sweep uses the October 22 and DATA-ACQ-002 manifests, 46 maps, no draw_all or
live_time. Baseline taken once: 25.17 / 102.96 s. Final after 23.19 / 68.44 s. Both sets pass: 92/92 PNGs, 46/46 OBJECT dumps,
46/46 light dumps, 46/46 normalized reports and 46/46 logs byte-identical. The after
sweep was refreshed following #361; before captures were reused without rerunning them.
Only output-path fields `png` and `fidelity_dump` are normalized in reports. Native source
outside selection is unchanged by this lane; #361's incoming body tables are included in the
post-merge checks. World-entry fixture controls pass separately from the capture identity test.

## Limits, next and cleanup

- Records remain authored appearance fixtures. No character-list packet decoding, account-backed
  equipment, stats/power work, network/login work, live memory access or protection analysis.
- FILE still selects the mesh. A handwritten mismatched code/file pair can apply one type's
  textures/effects to another mesh. Existing APP-POLISH-008 tests check the bundled pairs.
- Existing selection assembly, attachment order and class/pose restrictions remain. This lane
  does not add class-specific replacement meshes, +15 class attachments (`0x016d53a4`), cloth
  setup or unsupported item recipes. +15 mesh-pass coverage does not prove its attachments.
- Quality 5 is the existing native item environment default. No original-client visual-equivalence
  or performance acceptance claim. The installed Native Preview and Wine play/staged apps are untouched.

Next: steward integration/full gate, then an APP-REFRESH lane may install. Further selection
geometry/cloth work needs its own bounded original-caller proof. Account-backed appearance stays
excluded.

Cleanup removes this lane's scratch/renders/build outputs, worktree and local branch after the
ready line. No new input needs retention. Validator original-side shared caches remain. All
source/docs/pushes finish before the ready line; no branch push follows it.

Steward validators: validate_meshdraw,validate_model_edge,validate_movement,validate_audio_callers,validate_audio_domains,validate_audio_items,validate_app_polish4,validate_charsel_items.
Tested commit: `003b561f8ec316621e57b3675f86938a0c1eb43c`; canonical private-env above; no pending mutants.
