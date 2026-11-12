# MUUN-VISUAL-002

WIP. Branch `codex/muun-visual-002`, based on main `d4af71dd`.
Offline/static only. No installed-app change, live client, network, protection work or proprietary data commits.

## What draws

The fixture's fifteen attachment models now take the original ordinary MuunMeshInfo branch. Five appearances
add eight ordered mesh passes, including pulsing textures and code 363's colour/alpha passes. The base-slot
shadow uses its original alpha/world gates through the existing shadow renderer.
`MU_MUUN_FIXTURE=<id>` retains explicit fixture selection.

`MU_MUUN_COMMAND_FIXTURE=50..55` requests an authored command pose every 100 logic steps, using the original
same-owner category/action map and animation-end return to idle. Fourteen actual models can pose actions 3/4;
363 refuses them because its model has only three actions. This is synthetic command input; the installed
MuunInfo table has no auxiliary categories. [Addresses and scope](../research/client-muun.md).

## WIP checkpoint

Done: full static audit, before default sweeps using a rebuilt world binary, mesh/shadow/command implementation,
original-instruction comparison and all 15 compiled mutants, and six private native Muun tests including
GL/software pixel controls. Private tests 13.28 s; mutant row 13.21 s, 1,361 cases and 15/15 caught.
Full build 9.42 s. Baselines took 32.85 s and 82.09 s.
Before binary SHA-256: `601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
After rebuilt binary SHA-256: `eb7853668e46c82d4c2581780c80cf033077b788a753c90aade75db6b4d98f85`.

Portable affected batch at `27627248`: 1,412 tests, 1,170 passed, 242 skipped, no failures/errors,
494.96 s including selection, 378.0 s execution. Native proof: 17 GL renders, all visible with zero missing
textures/refused meshes/refused bones, 17.98 s, contact sheet inspected. Selection: 28 private validators,
44.02 s; the no-mutant affected batch is running with two workers. **8d reduced:** the native affected
selection exceeds 40 items; the changed private Muun module passed all six tests.

Left: finish the running 28-row validator batch, final default identity sweep, latest-main check,
final docs/PR/ready queue and cleanup. Next: inspect the validator result, then render the after sweep.
Local resume inputs are under `~/Documents/MTM/mu-mac-tools/native/scratch/muun-visual-002/`
and `renders/muun-visual-002/`. No new live capture or future-lane input needs retention.

Owner's updated cutoff: all work stops by 02:30 on 2026-11-12. If not PR-ready by 02:15, push a WIP handoff
by 02:30 and stop. Do not start a check that cannot finish before then.

## Limits

Ordinary mesh branch for the fifteen audited models. Later special models remain refused. Missing, dummy and
out-of-range bones stay refused. No remote-owner command motion, helper timer parity or `0x47a` transition effect.
No production selection, Muun packets, inventory, bonuses, damage or authoritative target feed. No live screenshot
or original full-motion equivalence. The environment switch remains because an in-scope source of owner slot
selection was not established. No README edits.
