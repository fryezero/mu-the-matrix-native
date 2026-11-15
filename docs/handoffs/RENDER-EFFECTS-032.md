# RENDER-EFFECTS-032

## WIP

Branch `codex/render-effects-032`, isolated worktree from main `b7dfd2ed`.
Main `2b0b2716`, AUDIO-004 #388, is integrated as `8187e8e3` with the registry
resolved at `fb561cff`. Both independent validator entries parse through the
repository loader. No subagents or full lane gate.

Done: summon, Defense, Fire Breath and Crescent callers; authored bow/wing actions;
active learned admission; the constructor/caller RNG interleaving correction.
Final proof at `8965554f` passes 4,433 checks, 31/31 compiled mutants, zero original
stops, 71.71 s. The post-fix root build passes in 12.70 s. Reduced private native
checks pass 15/15, zero skips/failures, 25.75 s. The unmodified native selection
is 174 items, so the brief's 40-item cap requires 8d reduced.

The first private affected validator run passed all 23 rows, 358.29 s at
`fb40a57e`, before the interleaving correction. Those affected inputs still need
refreshing. Initial twelve installed scenes pass 72 image pairs, plus ten early
arrow pairs. Final after/repeat renders must be refreshed without repeating the
baseline. Default after sweep and final world SHA-256 remain pending.

Portable validation is running 170 affected work items with two workers. The
local driver calls the repository runner with --affected origin/main and filters
only native/tests/test_native_app.py. That module packages Native Preview, which
the owner forbids this session. No app bundle is produced. Check the existing
foreground job/log before starting a duplicate on resume.

Next: finish portable validation, explicit world build, final after/repeat and
default identity, affected private validator refresh, audit, final docs/PR/queue.
New 0x7f84/3, 0x8001/0,
0x49e/0 requests remain refused. Defense and Crescent are L, all summons and
Fire Breath M. Coverage is 11 P / 5 L / 13 M -> 11 P / 7 L / 11 M for this
lane alone. EFFECTS-031's separate consumer work is excluded from that delta.

The default baseline was explicitly built with `make -C native -j4 world`.
Binary SHA-256 `e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.
One successful 46-view default sweep took 74.61 s, 184 PNG/OBJECT/light files
and 46 JSON streams. Old absolute paths in the local manifest were rebased to
the canonical MTM tools directory before the successful sweep. No baseline
images were produced by the two preflight path errors.

Local scripts/reports are under
`~/Documents/MTM/mu-mac-tools/native/scratch/render-effects-032/`, renders under
the matching `renders/render-effects-032/`. The guard waits for load <=14 and
memory free >=25% before heavy work. Resource pauses were observed.

Research: [caller inventory and limits](../research/client-render-effects-032.md).
Not PR-ready. No installed app or owner client was touched.
