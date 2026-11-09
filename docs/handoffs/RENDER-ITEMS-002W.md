# RENDER-ITEMS-002W

Branch `codex/render-items-002w`, worktree `~/Documents/MTM/worktrees/render-items-002w`, from main
`127489e0`, after prerequisite #355 merged. Codex, GPT-6.1 Sol; no subagents. Offline/static work only.
The installed Preview and Wine apps are untouched. No full gate in this lane.
Research uses part 34: main assigned parts 32/33 to RENDER-EFFECTS-023 and CLOAK-004 during verification.
Latest main `6736cb57` is merged; both lanes' source and documentation are retained.

## Result

Bodies **1,370 -> 1,404 of 1,674**, adding three read-program bows and all
31 rank-5 strlen parts. The body header is 515,323 bytes, below 512 KiB; recipe rows 1,351 -> 1,385. **270 remain**. Raw classification, stopped states and shape identities
are retained; 34 type rows and eight shape totals change, complete shapes 592 -> 600. Skins and links are unchanged.

- Worn `0x0f2a` receives the original caller's blend-light input, `1.0`, and its counter atlas becomes visible.
- Bows `0x1313`, `0x1317`, `0x1319` retain binary32 scalar operations and range-wrapper random attribution.
  Their pre-programs use the existing host; particle consumers belong to RENDER-EFFECTS-023.
- The 28 armour parts are groups `0x1a00`, `0x1e00`, `0x2000`, `0x2200` plus indices
  `0x26`, `0x27`, `0x2c`, `0x2e`, `0x2f`, `0x33`, `0x44`. Weapons are `0x0b5c`, `0x0b62`, `0x0b68`.
  Each exact texture-name result is an independent signed mesh input, including `-1`.
- `mu_rc_item_context` appends a name-lookup callback and its context, preserving the existing prefix.
  Both native initializers and both ctypes mirrors are updated. The native callback returns the first exact
  texture-name match. The upload census makes named passes reachable without guessing a worn model's indices.
- Original streams retain MESH(-1) calls. Native drawing rejects these calls before drawing, as the original
  mesh callee does; it no longer interprets a missing part as a whole-model draw.

## Causes and addresses

`RenderLinkItem` builds the linked OBJECT at PART+0x24, then calls `ItemObjectAttribute` at `0x012bdafb`.
At `0x016da0fb` the callee loads `1.0` from `0x01a7dd48`; `0x016da103` writes OBJECT+a8. This happens after
ObjectInit's zero initialization. Guarded execution at four clocks confirms the value and blend mesh -1.
The native correction is scoped to `0x0f2a`, whose worn input was established here.

Name lookup is `0x012bd4a6`. Generated scalar kind 8 preserves its raw integer bits rather than converting an
index to float. With no context or callback the result is -1. The original mesh draw rejects a negative or
out-of-range mesh at `0x012b8d46..0x012b8d51`; the wrapper reaches it at `0x00966e9b`.

The `0x0b62` block at `0x0172972d` computes tick % 415 / 83. Its signed remainder-by-one idiom at
`0x01729754..0x01729766` yields U=0; V uses the saved cell times .2 at `0x0172977a..0x0172978a`.
The clock reader now accepts the zero-low-bit mask in its already byte-checked signed-remainder idiom.
No runtime clock opcode was added. `0x0b68` additionally reads the rendered-frame counter.

The `0x2301`/`0x2302` wave call at `0x017b1d91..0x017b1dad` supplies exact words `(0, 0xc0800000)`.
The pinned helper yields +0, including the masked invalid conversion/remainder route. Only that operand pair
is folded; the nearby signed-zero and other operand pairs remain refused. Both types read afterwards but still
fail body fitting. A successful read is not an admission.

## Effects routed vs refused (natively)

The three bows' existing sprite/particle requests pass through the item host, with its shared random sequence.
Missing bones, unsupported kinds and textures remain refusals. No particle kind, sprite consumer, pool,
particle-request recovery for `0x0f2a`, or world owner API is changed here. RENDER-EFFECTS-023 owns that work.
Named body parts add mesh passes, not owner-effect programs. Existing process-counter and rand-phase limits remain.

## Checks

Final comparisons in progress; portable and reduced private native checks pass. Commands run from the repo root after
`. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`; row-specific section 3 uses
`MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`.
Heavy work uses `nice -n 10`, make `-j4`, runners `--jobs 2`; load/memory guards precede steps.

## Native visibility and app-path proof

Before correction, the regression fails: three fixed-pose images at counters 0/7/8 have one hash. The original
caller assertions pass. After correction, all three hashes differ (1,701 / 1,672 changed RGB pixels vs counter 0, 2.73 s). Pose is action 1 / frame .5, world time
123456, Hammer15.bmd / type `0x0f2a` / level 9, class 1, 640x480. No moving pose is used as counter evidence.

A locally built Preview bundle supplies `--print-plan`, then its own bundled mu-client runs that plan under
its network guard. Support, logs, session and options are isolated, `--no-store`; demo Atlas wears the same
mace, at Lorencia 138,123. The baseline client runs the same plan and fixture. Matching world frames differ
at the mace: frame 150 changes 1,084 RGB pixels (16.42 s for both clients), with zero network calls denied in both reports. The first replay reached the character-creation panel because auto selects slot 1; the fixture
was corrected to slot 1. The next replay reached the world but opened the menu; the retained replay holds scene 6 in the open plaza.
These are offline app-path proofs, not an installed-app refresh or original live-animation comparison.

## Default-draw identity

Before sets were rendered once from prerequisite main: October 22's 14 maps (20.88 s), DATA-ACQ-002's 32 maps
(57.34 s), 25 frames each, default draw, no draw_all or live clock. Final comparison pending.

C-to-C against the saved prerequisite-main library: 216,448 cases, exactly the intended 34 types change,
4.95 s. Streams compare declared fields, not structure padding.

## Limits

- 21 of the 24 read-program candidates remain unadmitted. The wave pair now reads but has no fit;
  `0x23a8`/`0x23a9` still fail independent input states. Default, carry and exit probes did not justify admission.
- The 54 helper-group-count types are not admitted. A two-seed level-zero screen is exploratory, not a census
  or comparison claim for that group. Full per-type recovery remains.
- Named lookups are explicit fixture/model inputs. This does not claim new bone pose, rank-5 owner-effect,
  buff, selected-item, record, server or character-power coverage. No new private capture is retained.
- Host-free bow bodies and absent-context named bodies use zero rand results. Owned/context-present comparisons
  check nonzero sequences and exact consumption; those guarantees are not attributed to the host-free path.
- Original-side caches stay in the shared tools directory. Lane scratch, proof renders and builds will be removed
  after queueing. Reproduce the fixed-pose proof using the committed regression and canonical private environment.

## Next groups

1. The remaining 21 read-program candidates: independent-state failures of `0x23a8`/`0x23a9`, the now-readable
   zero-frequency wave pair, and other failed fits.
2. The 54 helper-group-count types, preserving full level/record/quality and independent-state checks.
3. The other 195 unadmitted types, within the earlier rank-5 pose/owner and record limits.
4. RENDER-EFFECTS-023's particle requests/consumers remain separate.

## Verification checkpoint

At implementation/merge `94c1d5f6`:

| Check | Result | Wall time |
|---|---|---:|
| Full body / owner table generation | 1,385 body rows; both tables generated | 883.91 / 11.18 s |
| Root build / unchanged-input build after main merge | pass | 11.20 / 0.52 s |
| Portable affected selection and run, two workers | 148 work items, 1,413 tests, 1,181 passed, 232 skips, no failures/errors | 335.96 s (277.1 s test wall) |
| Canonical private renderer module from root | 22/22, no skips; **8d reduced**, selection 142 native modules >40 | 6.16 s |
| `validate_item_named --mutations` | 20,057 cases, zero mismatches, 8/8 mutants | 114.3 s |
| `validate_item_predraw --mutations` | 37,556 cases, zero mismatches, 48/48 detected; callback audit below | 287.8 s |
| Staged-source audit before checkpoint | 2,119 files, zero rejected | 18.71 s |

The pre-draw frame family covers 59 types / 7,068 counter values. Its owned family covers 3,392 states,
23,059 sprites, 903 particle requests, 2,222 joints, 15,045 refusals, 4,401 rand draws and 371 flag-clear states.
These are comparison-harness request counts, not native-pool creation counts.

Reviewing the mutant stderr found suppressed Python IndexErrors when planted bad-bone calls reached a
ctypes host callback. Reference comparisons are clean. A bounded callback diagnostic and portable boundary
regression are prepared; after the unchanged 50-row batch finishes, only the two affected bone mutants and
the two actual host consumers will be rechecked. Other mutants will not be repeated. This checkpoint is not
PR-ready until that audit and the remaining validator/default-draw checks finish.

The unchanged-source, no-mutant batch has passed 30/50 rows at this documentation checkpoint, including
carry, derived, record/quality, coverage and next-wing families. No failures or skips. Latest main is
`c26bd0e8`, RENDER-EFFECTS-023, reserving research part 32. Its merge and the bounded callback/body-only
proof refinements follow the current batch so each report remains tied to stable source.

## Late-main checkpoint

Main `6736cb57` (FX023 and CLOAK-004) is merged. Source `ad9f8c77` adds explicit callback bounds diagnostics
and the viewer's `--item-body-only` control. The atlas regression requires zero effect requests and zero
created particles, so merged particle motion cannot make a frozen atlas pass.

| Check | Result | Wall time |
|---|---|---:|
| Merged root build | pass | 9.85 s |
| Portable merge-affected run | 151 work items, 1,641 tests, 1,367 passed, 274 skipped, no failures/errors | 311.07 s (258.9 s test wall) |
| Canonical private changed/added native modules | 38/38, no skips; **8d reduced**, 143 selected native modules >40 | 26.47 s |
| Bounded host's portable renderchar suite | 107 tests, 84 passed, 23 private skips, no errors | 1.06 s |
| Bounded host reference and only two affected bone mutants | 3,392 owned states unchanged; object-domain 282 / object-bone 133 detections; no callback errors | 21.72 s |
| Current body-only zero-light control | private viewer copy with blend 0 has one hash; corrected viewer has three; counters 0/7/8, pose/time fixed, zero FX/particles throughout | 8.64 s |

The other 46 pre-draw mutants and eight named mutants were not repeated. The current PR selector keeps
54 rows, including all three symbol fallbacks. The since-tested-commit selector keeps 57 merge-affected rows,
pruning 29 rows with unchanged used symbols. Its no-mutant rerun is in progress; both selection lists and
per-row results will be reconciled before the ready-prs entry.
