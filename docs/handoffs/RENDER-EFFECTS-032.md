# RENDER-EFFECTS-032

## WIP

Branch `codex/render-effects-032`, isolated worktree from main `b7dfd2ed`.
No subagents. Original visual callers for seven summons, Defense, Fire Breath,
Crescent Moon Slash and bow/wing action selection are traced. Fixture requests
and admission are implemented; comparator and native tests are authored.
Compilation, original comparisons, mutants and native tests remain unchecked.
Next step is the guarded root build, then the small original comparator.

The default baseline was explicitly built with `make -C native -j4 world`.
Binary SHA-256 `e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.
One successful 46-view default sweep took 74.61 s, 184 PNG/OBJECT/light files
and 46 JSON streams. Old absolute paths in the local manifest were rebased to
the canonical MTM tools directory before the successful sweep. No baseline
images were produced by the two preflight path errors.

Local scripts/reports are under
`~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-032/`, renders under
the matching `renders/render-effects-032/`. The local guard waits for load <=14
and memory free >=25% before heavy work. The root build is currently waiting
on that guard. Latest observed shared load exceeded 30 with memory free >40%.

Research: [caller inventory and limits](../research/client-render-effects-032.md).
Not PR-ready. Latest-main merge, final checks, render proof, audit, status lines,
PR and ready queue remain pending. No installed app or owner client was touched.
