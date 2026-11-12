# MUUN-VISUAL-003

Work in progress on `codex/muun-visual-003`, from main `626abce1`. Offline/static only.
No installed-app, live client, service, packet, protection, actor, item table or particle-consumer edits.

## What draws

Focused comparisons and native tests pass; finish checks are pending. The explicit kind-1 mount fixture loads an independent secondary
skeleton for render-info ids 16/17/100..105. It uses the recovered model-header lookup, scales, action map,
speeds, owner position/angle and named-bone attachment offset. The existing fifteen attachment appearances
and their eight extra mesh rows are unchanged. The other ten appearances have no additional rows.

## WIP

Done: read both binding briefs and the 001/002 handoffs; created the assigned worktree; built the baseline;
re-audited installed mesh rows; traced secondary construction, action mapping, speed, render gates and
attachment; wrote the implementation, instruction comparator and native fixture tests.

Checked: new native target builds under `-Werror`, 4.63 s; private secondary module 4/4 tests, 16.73 s;
873 original cases, zero mismatches; 16/16 compiled mutants caught under `-Werror`, 7.10 s. All eight real
secondary skeletons have their named bone, actions 0/2/4 and zero missing textures. GL and software pixel
differences pass. Default before sweeps complete: fourteen views 30.31 s, thirty-two views 59.46 s.
The original comparison caught and corrected the initial WolfA run-speed error. Two validator-stub stack
cleanup errors were corrected before the successful run. Historical baseline manifests had stale paths;
those failed before rendering and were replaced with the current fourteen-view manifest.

Left: retained native proof renders, affected checks, after identity sweep, audit and final-main integration.
Shared-host load caused waits. One probe/build batch and one probe/test batch started before their high-load
output was inspected; subsequent probes and heavy launches are separate.

Next step: resource guard, repository audit and checkpoint push; then full build, affected selection/checks
and retained proofs. No further unchanged mutant rerun. Keep the 02:15 WIP and 02:30 stop deadlines.

## Limits and next

Hero rider placement, model-specific secondary effects, owner-kind-2 fade, buff-0x12 render mode and remote
transitions are not implemented. Production selection, inventory, bonuses, damage, commands and network
feeds remain excluded. No claim of complete kind-1 or full-scene equivalence.

## Checkpoints and cleanup

Local scratch and renders are under `~/Documents/MTM/mu-mac-tools/native/{scratch,renders}/muun-visual-003`.
No future-lane input has been created. Keep only needed resume inputs if stopped WIP; remove generated
outputs, worktree and local branch after the ready queue entry on successful delivery.
