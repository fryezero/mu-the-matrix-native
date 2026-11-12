# MUUN-VISUAL-002

WIP. Branch `codex/muun-visual-002`, based on main `d4af71dd`.
Offline/static only. No installed-app change, live client, network, protection work or proprietary data commits.

## What draws

The fixture's fifteen attachment models now take the original ordinary MuunMeshInfo branch. Five appearances
add eight ordered mesh passes, including pulsing textures and code 363's colour/alpha passes. The base-slot
shadow uses its original alpha/world gates  through the existing shadow renderer.
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

Left: native render proof inspection, affected selectors and portable/private checks, final default identity sweep,
latest-main merge, final docs/PR/queue. Next: finish the proof run, then select and run affected checks.
Local resume inputs are under `~/Documents/MTM/mu-mac-tools/native/scratch/muun-visual-002/`
and `renders/muun-visual-002/`.

## Limits

Ordinary mesh branch for the fifteen audited models. Later special models remain refused. Missing, dummy and
out-of-range bones stay refused. No remote-owner command motion, helper timer parity or `0x47a` transition effect.
No production selection, Muun packets, inventory, bonuses, damage or authoritative target feed. No live screenshot
or original full-motion equivalence. The environment switch remains because an in-scope source of owner slot
selection was not established. No README edits.
