# RENDER-ITEMS-002W

Branch `codex/render-items-002w`, worktree `~/Documents/MTM/worktrees/render-items-002w`, from main
`127489e0`, after prerequisite #355 merged. Codex, GPT-6.1 Sol; no subagents. Offline/static work only.
The installed Preview and Wine apps are untouched. No full gate in this lane.

## Result

Verification in progress. Target: bodies **1,370 -> 1,404 of 1,674**, adding three read-program bows and all
31 rank-5 strlen parts. **270 remain** if final checks pass. Raw classification, stopped states and shape identities
are retained; only admitted membership changes. Skins and links are unchanged.

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

Pending final table, affected checks and timings. Commands run from the repo root after
`. ~/Documents/MTM/mu-mac-tools/native/private-env.sh`; row-specific section 3 uses
`MU_SECTION3="$HOME/Documents/MTM/main-exe-study/evidence/x86-linux-capture-04/main-01ced000.bin"`.
Heavy work uses `nice -n 10`, make `-j4`, runners `--jobs 2`; load/memory guards precede steps.

## Native visibility and app-path proof

Before correction, the regression fails: three fixed-pose images at counters 0/7/8 have one hash. The original
caller assertions pass. After correction, all three hashes differ. Pose is action 1 / frame .5, world time
123456, Hammer15.bmd / type `0x0f2a` / level 9, class 1, 640x480. No moving pose is used as counter evidence.

A locally built Preview bundle supplies `--print-plan`, then its own bundled mu-client runs that plan under
its network guard. Support, logs, session and options are isolated, `--no-store`; demo Atlas wears the same
mace, at Lorencia 128,124. The baseline client runs the same plan and fixture. Matching world frames differ
at the mace. The first replay reached the character-creation panel because auto selects slot 1; the fixture
was corrected to slot 1. The next replay reached the world but opened the menu; the retained replay holds scene 6.
These are offline app-path proofs, not an installed-app refresh or original live-animation comparison.

## Default-draw identity

Before sets were rendered once from prerequisite main: October 22's 14 maps (20.88 s), DATA-ACQ-002's 32 maps
(57.34 s), 25 frames each, default draw, no draw_all or live clock. Final comparison pending.

## Limits

- 21 of the 24 read-program candidates remain unadmitted. The wave pair now reads but has no fit;
  `0x23a8`/`0x23a9` still fail independent input states. Default, carry and exit probes did not justify admission.
- The 54 helper-group-count types are not admitted. A two-seed level-zero screen is exploratory, not a census
  or comparison claim for that group. Full per-type recovery remains.
- Named lookups are explicit fixture/model inputs. This does not claim new bone pose, rank-5 owner-effect,
  buff, selected-item, record, server or character-power coverage. No new private capture is retained.
- Original-side caches stay in the shared tools directory. Lane scratch, proof renders and builds will be removed
  after queueing. Reproduce the fixed-pose proof using the committed regression and canonical private environment.

## Next groups

1. The remaining 21 read-program candidates: independent-state failures of `0x23a8`/`0x23a9`, the now-readable
   zero-frequency wave pair, and other failed fits.
2. The 54 helper-group-count types, preserving full level/record/quality and independent-state checks.
3. The other 195 unadmitted types, within the earlier rank-5 pose/owner and record limits.
4. RENDER-EFFECTS-023's particle requests/consumers remain separate.
