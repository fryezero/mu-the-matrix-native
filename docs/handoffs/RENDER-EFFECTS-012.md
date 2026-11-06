# RENDER-EFFECTS-012

Ten bow joint kinds, multishot02/1 and 0x45e's white model colour.
[Finding and addresses](../research/client-render-effects-012.md).

The 33 bow scenes now have **77 → 27 unsupported requests**, with **119 → 119 arrows**.
The 50 removed refusals are 39 joint requests across ten kinds and 11 multishot02 effects.
The ten other combat scenes remain at zero unsupported requests and have identical images.
No pet-specific code changed. Nine bow scenes change visually; the other 24 remain byte-identical.

Started from `origin/claude/render-effects-011` at `a1fe59cb5816abbd7cce89fb39549e87136a4f58` using the
owner-authorized fallback after batch 32 reported failure with PR #292 still open. The fallback includes
011 and its known limits; 012 depends on it. The baseline was taken once from that unchanged base.
After #292 merged at 2026-11-06 03:11:38 UTC, main `9e93e6c9` was merged in `fbb7c282`.
That merge changed no files (`git diff 02a8463f..fbb7c282` is empty), so source checks remain valid.
Worktree: `~/Documents/MTM/worktrees/render-effects-012`, branch `codex/render-effects-012`.
Shared `tools/python`, `evidence`, `input` links are never committed.

## Scope and integration

- `reconstructed/joints/bow_joints.inc`: 0x80e3/4, 0x80e4/1, 0x814c/a, 0x8182/a, 0x8185/a,
  0x85cc/0, 0x828c/2, 0x7f79/c, /12, /16. Subtypes here are hexadecimal.
- `joints.c`: admission/create/move hooks and Flare02/c's per-tail colour in the existing renderer.
- `arrow_fx.inc`: 0x38b5/1 create/move. This model effect is explicitly excluded from arrow counting.
- `native/core/mu_combat.{c,h}`: eight bitmap slots (16 → 24), emitted joint key/skill/colour,
  multishot02's model slot and emitted scale/key, model draw above 0x7a4, and white 0x45e colour.
- `validate_render_effects12`, registry row and portable synthetic tests. The installed combat test's bitmap
  expectation now reads 24. No changes to the world particle table or the other lanes' owned code.

## Scene measurements

All scenes: 640x400 software renderer, Lorencia tile 182,128, actor 3 at 186,128, 30 frames, every fifth frame,
no audio/items/remote players; each bow uses class 2 and `2:skill:24:spider;3:stop`. The ten staff scenes use
skills 1,2,3,4,5,7,8,9,10,14. Inputs are the installed client and the read-only plain objects directory.

| Bow | Unsupported before → after |
|---|---:|
| 0x1300 | 8 → 0 |
| 0x1304, 0x12fd, 0x12ff, 0x1305, 0x130c, 0x132c | 4 → 0 each |
| 0x12fa | 3 → 0 |
| 0x130e | 15 → 0 |
| 0x12f7 | 12 → 12 (0x7f78/b) |
| 0x12fb | 3 → 3 (0x7f79/e) |
| 0x12fc | 4 → 4 (0x7f79/f) |
| 0x130a, 0x131e | 4 → 4 each (0x80e3/5) |
| Other 19 bows | 0 → 0 |

Nine bows above improve; 0x1300 contains two new joint kinds. Those nine scenes change visually.
Four small window-only native PNGs (before/after for 0x1300 and 0x12fa) are kept at
`~/Documents/MTM/mu-mac-tools/native/renders/render-effects-012/`, as requested. These are native renders,
not live-client comparison captures. The black arrow-model surfaces visible on 0x1300 also occur in the baseline.

## Checks

Final validation and wall times will be filled before the ready entry. No lane full gate; the steward owns it.

## Remaining work

The 27 requests above stay explicitly unsupported. See the finding for their missing owner-state and particle
contracts. Ground skills still need 0x703..0x706, stone/0x13, their native route and the +0x64 clearing site.
0x45e's decal is still counted but not drawn for subtypes 3..7. Uruk needs weather input/capture; Muun needs
owners. No live session, network work, memory write, protection work or installed-app change was performed.

## Cleanup

After final push and ready entry: remove this lane's scratch/build directories, shared-input links and owned
worktree/local branch. Preserve the remote branch for the steward and the four requested PNGs above. There are
no new private inputs a later lane needs to retain.
