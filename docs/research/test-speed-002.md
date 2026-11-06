# Validator finish costs after TEST-SPEED-001

The 24-row profile found three different costs. Meshdraw spent 313 of 354 profiled seconds launching
`mu-render info` for the installed model census. Terrain spent 61 of 97 profiled seconds generating synthetic
scenes. Model-edge spent 199 of 353 profiled seconds in emulation, including Python memory-access hooks;
122 seconds also went into the Python LEA fallback because the fresh worktree had not built model-recovery.
These are cumulative profile times, which overlap and include instrumentation overhead. They are not timing
claims for a normal finish run. The terrain profile stopped at the missing v14 reader before writing its report.

The meshdraw census now invokes a test-only batch host, 64 paths per process. That host calls the existing
`mu-render info` main entry point for every path, with fresh options each time. It emits the identical JSON
for successful inputs and an empty object for the failures the old census skipped. All model parsing remains
live. No installed names, native results, or native success decisions are cached.

Meshdraw's original name-parser, math and draw calls use the existing opt-in original cache. Draw cases reset
their memory from their case input. The cache stores only original results, coverage and x87 counters, and
original trig arguments/results. Native replay, ctypes calls, stream comparisons, host libm comparisons and
negative controls execute on every run. Trig hooks record observations while filling a cache entry; the same
host comparison runs after either a hit or a miss. Case inputs are hashed to keep large model arrays out of
cache keys. The existing identity includes all pin hashes, including section3, Python and Unicorn versions,
and the Python harness import closure. Pins are still verified before any cache lookup.

Terrain's decal loop used only every third generated scene. Each used scene had seed 800, with world as its
only varying input. Its generator uses a local RNG. The loop now generates that template once, takes a new
dictionary with the same world field for each load, and copies the same arrays into fresh ctypes buffers and
client memory. Native calls, original calls, random case draws and comparisons are unchanged. No disk cache
or emulated state replay is used for terrain.

Model-edge and terrain now declare model-recovery as a build prerequisite. This avoids the Python LEA fallback
and the missing Crypto++ v14 reader in a new worktree. Model-edge's original execution remains uncached: its
allocation graph, definedness tracking, foreign reads/writes and stale-memory experiments require more than
caching a return value. No shortcut to those checks was taken.

Fifteen native build rows now name the artifacts they consume. Selection follows a forced make dry run,
recursive includes, included make fragments and available dependency files. Directly compiled C files named
by a validator also contribute their header closure. Archive consumers retain the entire archive dependency
set. A failed make dry run falls back to the whole directory. The owning unittest remains a trigger but does
not contribute its unrelated imports to a standalone validator process. The validator's own native fixture
imports are followed. Swift app sources and C test hosts are gate-owned; explicit validator references still
select those rows, while unknown production inputs still select everything.

[Timings, replay, commands and limits](../testing/TEST-BUDGET.md).
[Delivery checks and steward handoff](../handoffs/TEST-SPEED-002.md).
