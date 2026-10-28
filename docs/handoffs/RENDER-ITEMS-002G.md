# RENDER-ITEMS-002 part 7

Implementation checkpoint. Worktree `render-items-002g`, branch `codex/render-items-002g`,
base `40f34a9`. No live client or launcher used. Owns renderchar/item sources,
local validators and minimal item hooks; audio/session-global lanes remain separate.

Baseline local Mac gate passes. The committed README stress loadouts contain one
refused body, mace model `0x0eee`, group 2/index 8. Its bounded body and three
additional pulse-link targets are implemented. The analogous ground-armour
fallback now resolves glow textures under Data/Effect, as the remote loader does.

Checkpoint evidence: 28 candidate body types pass 8,176 full instruction cases;
three links pass 1,200 cases. Additional ranked candidates are being screened.
The expanded clamped-wave recipes initially overfit saturated probe clocks. The
independent comparison caught them; generation now includes clocks below the
clamp. No release coverage claim is made for unscreened candidates in this WIP.

Rank 5's real pose caller now executes with authored action/bone tracks. It
matches production pose C in 608 cases across all nineteen types. Two nonzero
points per pose add 1,216 TransformPosition checks. Named-mesh rendering and
native pose lifecycle remain unresolved, so these bodies remain refused.

Next: finish independent body screening, compiled mutants, native loader/render
regressions, coverage TSVs, evidence documentation, and the lock-held merge/gate.
Local reports and a small before binary are confined to the lane scratch/render
directories. Delete all lane outputs, worktree and local branch after merge.
