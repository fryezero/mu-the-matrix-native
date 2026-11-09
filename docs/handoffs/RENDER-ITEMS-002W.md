# RENDER-ITEMS-002W

Branch `codex/render-items-002w`, from main `127489e0` after prerequisite #355 merged. Codex, GPT-6.1 Sol;
no subagents. Latest main `6736cb57` is merged, retaining GFX-FRAME0-001, RENDER-EFFECTS-023 and CLOAK-004.
Research is [part 35](../research/client-render-items.md#part-35-worn-mace-light-and-named-part-meshes-render-items-002w):
main assigned parts 32/33 while this lane verified its changes. Offline/static only. No full gate in the lane.
The installed Native Preview and Wine apps are untouched.

## Result

- Bodies **1,370 -> 1,404 of 1,674**; **270 remain**. Additions: bows `0x1313`, `0x1317`, `0x1319`, all 28 armour
  parts in groups `0x1a00/0x1e00/0x2000/0x2200` plus indices `0x26/0x27/0x2c/0x2e/0x2f/0x33/0x44`, and
  weapons `0x0b5c`, `0x0b62`, `0x0b68`. Skins 17/17 and links eighteen targets/twenty-four types are unchanged.
- Recipe rows **1,351 -> 1,385**. `item_bodies.h` is **515,323 bytes**, below 512 KiB. The existing scalar/op caps
  remain. Survey: 34 type memberships and eight shape totals change; complete shapes **592 -> 600 of 798**.
  Raw shape identities, classifications and stopped states are preserved, including the original strlen stops.
- The worn `0x0f2a` caller supplies blend light **1.0**, making its counter atlas visible. A body-only native
  negative control and a current-source local Preview-path comparison establish the effect of that input.
- The three bows gain their pre-programs. Exact SSE order, extended probes and range-wrapper random attribution
  resolve their prior independent-state failures; no tolerance was relaxed.
- Named part meshes are independent model inputs. The context appends a pure texture-name callback and its
  context, preserving the old lighting/blue/random prefix. Both native initializers and both ctypes mirrors
  are updated. Scalar kind 8 copies the signed mesh result as an integer word, including -1.
- Native lookup returns the first exact texture-name match. The bitmap census supplies present results to reach
  every referenced overlay. The native draw adapter skips negative mesh calls, as the original callee does;
  the reconstructed request stream retains MESH(-1). Synthetic models cover missing and duplicate names.

## Causes and addresses

`RenderLinkItem` reaches the linked OBJECT at PART+0x24, sets the type and calls `ItemObjectAttribute` at
`0x012bdafb`. The callee loads 1.0 from `0x01a7dd48` at `0x016da0fb` and writes OBJECT+a8 at `0x016da103`,
overriding ObjectInit's earlier zero at `0x0129ed3c`. Guarded execution with poisoned prior fields at clocks
0, 1, 123456 and -8000 confirms blend light 1 and blend mesh -1. The native correction is scoped to `0x0f2a`.

Texture-name lookup is `0x012bd4a6`. The 21 exact names are declared in `validate_renderchar.NAMED_MESH_NAMES`;
missing context/callback/name yields -1. The original MeshDraw rejects a negative or out-of-range mesh at
`0x012b8d46..0x012b8d51`, reached by the wrapper at `0x00966e9b`. Skipping MESH(-1) in the reconstructed stream
was rejected by independent comparisons; only native drawing treats that request as a no-op.

`0x0b62` computes tick % 415 / 83 at `0x0172972d`. The signed remainder-by-one idiom at
`0x01729754..0x01729766` stores U=0, then the saved cell times .2 supplies V at `0x0172977a..0x0172978a`.
The reader accepts the zero-low-bit mask in its existing byte-checked remainder idiom. No runtime opcode was
added. An authored portable instruction test checks both chains, including negative clocks. `0x0b68` joins
59 frame-counter types with its `(counter + 1) % 60` scroll. Named phase probes preserve the level/quality split.

`0x2301/0x2302` call the wave helper at `0x017b1d91..0x017b1dad` with exact words `(0, 0xc0800000)`.
The pinned masked SSE/CVTT route yields INT_MIN dividend/divisor, remainder zero and +0. A directed 200-state
screen includes finite/signed-zero/NaN/infinity boundaries. Only that exact operand pair is folded; portable
negative tests preserve nearby refusals. Both types now read (312 operations), but their bodies still fail fitting.

## Effects routed vs refused (natively)

| Group | Route | Bound |
|---|---|---|
| Three bows | Existing item host, sprites/particles and shared rand stream | Missing bones, unsupported kinds and textures remain refusals. |
| 31 named parts | Body mesh requests and existing bitmaps | No new pose or rank-5 owner-effect program is claimed. |
| Mace particles/consumers | RENDER-EFFECTS-023, merged from main | This lane does not recover those requests or implement their consumers. |

The full owned pre/post family covers 3,392 states: 23,059 sprites, 903 particle requests, 2,222 joints,
15,045 refusals, 4,401 rand draws and 371 flag-clear states. These are harness counts, not native-pool creations.
Body comparisons execute RenderObjDraw under the existing recording draw/effect boundaries. They compare
request words and model writes, with declared name results; they do not compare original pose construction,
mesh geometry or pixels. Native fixtures and the atlas/app renders provide separate integration evidence.

## Checks

From the repository root, canonical `. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`; where required,
`MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`.
Heavy work uses `nice -n 10`, make `-j4`, runners `--jobs 2`. Load/memory guards preceded steps; waits were
applied above load 14. Shared original-side caches are retained.

Initial source/merge **`94c1d5f6`**: all 52 selected rows pass, **934,143 comparisons**. Fifty run without mutants
in **1,961.93 s elapsed / 3,873.1 s aggregate row wall**; changed rows named/pre-draw run once with mutants in
**287.85 s elapsed**, individual walls below. After main merge and controls, source **`ad9f8c77`**:
all **57** since-tested-commit rows pass, **332,512 comparisons**, **487.14 s elapsed**, without mutants.
The selector prunes 29 rows whose used symbols did not change. The current PR selection is **54 rows**,
**937,936 row comparisons**, including three fallbacks: meshdraw/model_edge (viewer global W), movement (shell objects).
Rows outside the merge rerun retain their earlier results because their compiled inputs/used symbols are unchanged.
Subsequent documentation edits change no validation logic or native compiled code.

| Check | Result | Wall time |
|---|---|---:|
| Full body / owner table generation | Both tables generated; full generation and reproduction checks pass | 883.91 / 11.18 s |
| Root build before / after late main | Pass | 11.20 / 9.85 s |
| Final world/client / local app build | Pass | 0.24 / 2.13 s |
| Initial portable affected run | 148 work items; 1,413 tests, 1,181 passed, 232 private skips, no errors | 335.96 s; 277.1 s test wall |
| Merged portable affected run | 151 work items; 1,641 tests, 1,367 passed, 274 skips, no errors | 311.07 s; 258.9 s test wall |
| Initial canonical private renderer module | 22/22, zero skips | 6.16 s |
| Merged canonical private changed/added native modules | 38/38, zero skips; renderer, particles, FX023 and NPC cloth | 26.47 s |
| Bounded-callback portable renderchar suite | 107 tests, 84 passed, 23 private skips, no errors | 1.06 s |
| Bounded-callback owned reference and two affected bone mutants | 3,392 states unchanged; object-domain 282 / object-bone 133 detections; no callback exceptions | 21.72 s |
| Native body-only zero-light control | Blend 0: one hash; blend 1: three; all six images have zero FX/particles | 8.64 s |
| C-to-C against saved prerequisite-main library | 216,448 states; exactly the intended 34 types change | 4.95 s |
| Initial staged-source audit | 2,119 files, zero rejected | 18.71 s |
| Final staged-source audit | 2,128 files, zero rejected | 16.88 s |

**8d reduced:** initial native selection 142 modules, merged selection 143, both above the 40-item cap.
Only the changed/added native modules ran privately. Portable skips remain visible; private instruction rows
are run through the validator runner. The full combined gate remains the steward's responsibility.

The first pre-draw mutant stderr exposed suppressed Python IndexErrors on planted invalid bone calls.
The host now records explicit invalid-transform diagnostics and zeroes those callback outputs. All valid owned
states remain identical. Only the two affected bone mutants were rebuilt/rechecked; the other 46 pre-draw
mutants and eight named mutants were not repeated. The new portable boundary regression covers all three callbacks.

### Current PR / steward selection

Initial walls are at `94c1d5f6`; rerun walls are at `ad9f8c77`. All rows pass. **No steward mutants requested**;
the lane completed the changed mutant checks. Per TEST BUDGET 8, reuse rows when their inputs have not changed.

| Steward validator | Cases | Initial s | Merge rerun s | Lane mutants |
|---|---:|---:|---:|---|
| `validate_item_ranked` | 17,736 | 111.8 | — | — |
| `validate_item_continuation` | 25,772 | 148.7 | — | — |
| `validate_item_expansion` | 52,172 | 261.4 | — | — |
| `validate_item_clusters` | 74,292 | 306.4 | — | — |
| `validate_item_types` | 135,176 | 26.8 | — | — |
| `validate_fidelity` | 991 | 49.2 | — | — |
| `validate_meshdraw` | 14,619 | 50.7 | 58.4 | — |
| `validate_model_edge` | 954 | 109.3 | 106.0 | — |
| `validate_movement` | 6,614 | 49.4 | 48.9 | — |
| `validate_renderchar` | 1,706 | 44.7 | — | — |
| `validate_icarus_c2` | 8,400 | 13.9 | 15.0 | — |
| `validate_audio_callers` | 5,528 | 5.1 | 4.4 | — |
| `validate_item_gear` | 25,256 | 169.7 | — | — |
| `validate_item_next` | 14,992 | 194.8 | — | — |
| `validate_render_effects5` | 1,190 | 2.9 | 2.9 | — |
| `validate_render_effects7` | 596 | 1.3 | 1.1 | — |
| `validate_render_effects9` | 304 | 0.6 | 0.7 | — |
| `validate_render_effects10` | 154 | 0.3 | 0.3 | — |
| `validate_render_effects11` | 176 | 0.2 | 0.2 | — |
| `validate_render_effects12` | 64 | 0.2 | 0.2 | — |
| `validate_audio_domains` | 2,544 | 18.5 | 22.8 | — |
| `validate_audio_items` | 3,000 | 2.2 | 2.3 | — |
| `validate_item_coverage` | 31,724 | 168.9 | — | — |
| `validate_item_wings_next` | 33,622 | 179.0 | — | — |
| `validate_item_scalars` | 26,274 | 141.8 | — | — |
| `validate_item_chains` | 35,406 | 188.3 | — | — |
| `validate_item_carry` | 114,388 | 471.4 | — | — |
| `validate_item_quality` | 28,080 | 137.4 | — | — |
| `validate_item_product` | 2,874 | 51.4 | — | — |
| `validate_item_derived` | 36,252 | 181.0 | — | — |
| `validate_item_ownerfx` | 14,964 | 136.1 | — | — |
| `validate_item_predraw` | 37,556 | 287.8 | 249.5 | 48/48; two rechecked |
| `validate_item_hiddenmesh` | 116,281 | 400.2 | — | — |
| `validate_app_polish1` | 752 | 19.1 | 17.8 | — |
| `validate_app_polish2` | 1,028 | 3.3 | — | — |
| `validate_app_polish4` | 10,485 | 34.7 | 28.4 | — |
| `validate_render_effects13` | 180 | 0.7 | 0.4 | — |
| `validate_render_effects14` | 660 | 1.3 | 0.9 | — |
| `validate_render_effects15` | 509 | 0.8 | 0.6 | — |
| `validate_render_effects16` | 424 | 3.5 | 2.3 | — |
| `validate_worlds_fog` | 4,044 | 7.0 | 4.1 | — |
| `validate_render_effects17` | 618 | 8.0 | 6.2 | — |
| `validate_item_callers` | 6,013 | 1.5 | 1.1 | — |
| `validate_inventory_fx` | 8,017 | 12.2 | 6.7 | — |
| `validate_render_effects18` | 540 | 3.2 | 0.8 | — |
| `validate_render_effects19` | 400 | 0.8 | 0.6 | — |
| `validate_render_effects20` | 148 | 0.4 | 0.2 | — |
| `validate_render_effects21` | 267 | 0.5 | 0.2 | — |
| `validate_item_cloak` | 5,694 | 113.3 | 117.3 | — |
| `validate_armour_cloak` | 4,448 | 35.3 | 39.4 | — |
| `validate_render_effects22` | 202 | 3.9 | 4.4 | — |
| `validate_item_named` | 20,057 | 114.3 | — | 8/8 |
| `validate_npc_cloak` | 2,619 | — | 25.9 | — |
| `validate_render_effects23` | 1,174 | — | 4.9 | — |

Steward validators: validate_item_ranked, validate_item_continuation, validate_item_expansion, validate_item_clusters, validate_item_types, validate_fidelity, validate_meshdraw, validate_model_edge, validate_movement, validate_renderchar, validate_icarus_c2, validate_audio_callers, validate_item_gear, validate_item_next, validate_render_effects5, validate_render_effects7, validate_render_effects9, validate_render_effects10, validate_render_effects11, validate_render_effects12, validate_audio_domains, validate_audio_items, validate_item_coverage, validate_item_wings_next, validate_item_scalars, validate_item_chains, validate_item_carry, validate_item_quality, validate_item_product, validate_item_derived, validate_item_ownerfx, validate_item_predraw, validate_item_hiddenmesh, validate_app_polish1, validate_app_polish2, validate_app_polish4, validate_render_effects13, validate_render_effects14, validate_render_effects15, validate_render_effects16, validate_worlds_fog, validate_render_effects17, validate_item_callers, validate_inventory_fx, validate_render_effects18, validate_render_effects19, validate_render_effects20, validate_render_effects21, validate_item_cloak, validate_armour_cloak, validate_render_effects22, validate_item_named, validate_npc_cloak, validate_render_effects23.

### Merge-only reruns

These rows were selected by late-main compiled changes, passed at `ad9f8c77`, and are not in the current PR's
54-row selection. They are listed to account for the required post-merge checks, without expanding the ready list.

| Merge-only validator | Cases | Wall s |
|---|---:|---:|
| `validate_item_effects` | 1,500 | 0.8 |
| `validate_particles` | 407 | 0.7 |
| `validate_render_effects` | 660 | 0.7 |
| `validate_render_effects3` | 720 | 0.7 |
| `validate_render_effects4` | 1,920 | 4.4 |
| `validate_render_effects6` | 1,000 | 0.9 |
| `validate_render_worlds_a` | 9,000 | 8.2 |
| `validate_world_particle_consumers` | 900 | 0.6 |
| `validate_worlds_121` | 4,000 | 3.1 |
| `validate_worlds_after` | 13,424 | 9.3 |
| `validate_worlds_after2` | 32,216 | 24.1 |
| `validate_worlds_after3` | 10,212 | 7.4 |
| `validate_worlds_after4` | 9,181 | 12.5 |
| `validate_worlds_after5` | 6,000 | 6.8 |
| `validate_worlds_after6` | 7,300 | 46.9 |
| `validate_worlds_e` | 4,840 | 11.8 |
| `validate_worlds_g3` | 4,000 | 3.0 |
| `validate_worlds_karutan` | 3,000 | 2.1 |
| `validate_worlds_l` | 1,260 | 0.8 |
| `validate_worlds_m` | 1,080 | 0.7 |
| `validate_worlds_raklion` | 3,000 | 2.4 |
| `validate_worlds_slots` | 18,999 | 11.0 |
| `validate_worlds_slots2` | 33,000 | 20.1 |
| `validate_worlds_slots3` | 36,000 | 19.9 |

## Native visibility and app-path proof

The original regression first fails with one hash at counters 0/7/8 despite correct original-caller assertions.
After correction it has three hashes. The final control uses `--item-body-only`, holding class 1, Hammer15.bmd,
type `0x0f2a`, level 9, action 1, pose frame .5, world time 123456 and 640x480 fixed. A private compiled copy
forcing the one input back to zero restores the single hash; the corrected input gives three. Every control
reports zero pre-effects, refusals and created particles. This isolates the atlas after FX023's particles merge.

The current local Preview bundle supplies `--print-plan`. Its bundled client runs that plan under its network
guard, isolated support/logs/session/options and `--no-store`. A second current client links the same code and
libraries with only the blend-light input forced to zero. Demo Atlas (class 1, fixture level 1, appearance-only
mace +9) stands at Lorencia 138,123. Other players/NPC/combat/environment effects are off, particles are off,
and `--hold 6` keeps the system menu closed. Matching frame 150 differs by **1,084 RGB pixels**, in the mace box
**(331,198)..(375,258)**. Both guard exit reports have zero inet/connect/lookup/other denials.
Current app client link: 3.29 s; both app-path renders: **15.46 s**. Earlier baseline-app comparisons agreed,
but the final proof uses matching current code so merged effects/cloth changes cannot explain the delta.
This is a local app-path proof, not an installed refresh or original-client pixel comparison.

## Default-draw identity

Baseline sets were taken once from prerequisite main: October 22's 14 maps **20.88 s**, DATA-ACQ-002's 32 maps
**57.34 s**. The single final sweep passes: **92/92 PNGs, 92/92 dumps and 46/46 normalized reports byte-identical**.
Raw JSON reports differ only by FX023's bitmap-load vector growing 79 -> 93. Normalization maps the original
79 bitmap identities and verifies all 14 added slots loaded in every report; all other report bytes match.
Final walls: **15.45 / 39.51 s**. Default 25-frame draws only; no draw_all or live-time recapture.

## Limits

- **270 bodies remain:** 21 read-program candidates, 54 helper-group-count types, 195 others. The wave pair reads
  but does not fit; `0x23a8/0x23a9` still fail default/carry/exit independent-state fitting. No relaxed comparisons.
- All 31 strlen bodies are admitted with explicit model-name inputs; raw classification stops remain. This does
  not establish new rank-5 pose, owner-effect, buff, selected-item, record or character-power coverage.
- Host-free bow bodies and absent-context named bodies use zero rand results. Owned/context-present comparisons
  check nonzero sequences and consumption; those guarantees are not attributed to host-free paths. The absolute
  process rand/counter phases and earlier model/bone limits remain.
- The helper-count two-seed level-zero screen is exploratory, not a passing census of that 54-type group.
- No original-client process or memory access, protected-component analysis, or live service/packet work was used.
  No new private capture is retained. Native Preview and Wine apps are untouched; all shown names are demo names.

## Next groups

1. The remaining 21 read-program candidates, especially the two wing failures and now-readable wave pair.
2. The 54 helper-group-count types with full level/record/quality and independent-state checks, then the other 195.
3. Existing pose/owner/bone/record domains and separate FX023 bitmap gaps remain with their respective lanes.

After the final push and ready-prs entry, lane-owned builds, scratch, renders, worktree and local branch are
removed. The remote branch stays for the steward. Shared caches and the main checkout's input/tool symlinks
are untouched. No lane input needs retention; the committed atlas regression reproduces the native proof.
