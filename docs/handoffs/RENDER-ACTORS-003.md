# RENDER-ACTORS-003

## WIP checkpoint

Branch `codex/render-actors-003`, base `d4af71dd`. Offline/static only, no subagents.
The owner removed the stop deadline on 2026-11-11. Continue through PR-ready, keeping
commit/push/WIP checkpoints every 20-30 minutes. No ready entry has been written.

Done: binding briefs, current handoffs and actor/Muun sources read. Baseline root
build and explicit `make -C native -j4 world` complete. One-time 46-map default sweep
saved as hashes, 230 files, 78.9 s. Before binary SHA-256
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.

Classes 625/626 now have provisional recipes for the constructor's kind-1,
class-byte-0 fixture context, with startup files `Data/Item/iron_robot.bmd` and
`Data/Item/iron_robot_gold.bmd`. The first private iteration passes 734 checks,
zero mismatches, 53.5 s, including 34 native loads, textured robot bodies and four
native refusals. Two portable recipe tests pass in 1.1 s.

New bounded original-instruction audits pass separately: 270 robot action-hook
cases, 16 companion allocation/reuse controls, eight class-378 prefix controls.
The prefix ends before cloth allocation; it is not the complete 378 branch.
These new checks have not yet run in the full validator or through mutants.

Left: finish the four refusal investigations, review fixture-context boundaries,
full actor comparison and changed mutants, affected selection/checks, private 8d
under its cost cap, two robot demo renders, final rebuilt-binary identity sweep,
main integration, final documentation and PR-ready delivery. Whole-client actor
coverage and transformed-player hooks remain outside these recipes.

Next: retain 374/642 until companion update/draw/destruction is recovered, 378
until its cloth and aura path is recovered, and 617 until a startup model file is
proved. Do not supply them with a guessed body or file. Current bounded census
is provisionally 26 admitted / six refused to 28 admitted / four refused.

Local inputs for resuming: the one-time hashes and helper scripts in
`~/Documents/MTM/mu-mac-tools/native/scratch/render-actors-003/`. No live process,
installed app, Muun module, item generator or effect consumer was changed.
