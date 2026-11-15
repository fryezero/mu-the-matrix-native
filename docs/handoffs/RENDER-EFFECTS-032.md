# RENDER-EFFECTS-032

## WIP

Branch `codex/render-effects-032`, isolated worktree from main `b7dfd2ed`.
Main `2b0b2716`, AUDIO-004 #388, is integrated as `8187e8e3` with the registry
resolved at `fb561cff`. Both independent validator entries parse through the
repository loader. No subagents or full lane gate.

Done: seven summon callers, Defense and Fire Breath poses, Crescent Moon Slash
step/end requests, bow/wing action context, active learned admission, original
comparisons and new mutants. Full proof passes 4,233 checks, 28/28 compiled
mutants, zero original stops, 31.32 s. Six initial native tests pass, 7.77 s.
Root build on integrated main passes, 24.79 s; explicit world build 6.20 s.

Next: guarded installed-data fixture renders, affected portable/private selection
and checks, default after sweep, final audit/status/PR. New 0x7f84/3, 0x8001/0,
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
