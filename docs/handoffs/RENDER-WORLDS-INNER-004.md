# RENDER-WORLDS-INNER-004

Branch `codex/render-worlds-inner-004`, starting main `b7dfd2ed`. Implementation by Codex, GPT-6.1 Sol,
without subagents. Work is offline and fixture-only. Merge belongs to the steward.

## Scope and what draws now

Complete visual leaves for Crywolf 30 and shared Barracks/Refuge 41/42. Bounded Kalima 24..29/36 and tower 39
branches add named glows, particles, smoke and joint requests. Unsupported consumers retain their counts.
Kalima types 15/29/32 need hero/water helper context and remain counted refusals; tower type 0 needs its
nested event sequence and remains refused. Worlds 46/98 have no registration in the static 48-class factory
and remain refused per loaded object. No authoritative event model is invented.

The Kanturu 0x60 extra RGBA mesh now carries GREATER 0 through the scene driver to software, immediate GL and
batched GL. The callback flushes pending batches before changing the reference and restores GREATER 0.25.
Default draws leave the reference alone. No particle/joint consumer, installed app or README changes.

## Checks so far

- Starting root build: pass, 30.64 s. Explicit starting world build: pass, 4.00 s.
- Eight small original families: 1,600 cases, zero mismatches/stops, 11.60 s.
- Producer module, private: four tests passed, 4.98 s. Additional refusal/registry tests were added afterward.
- Production object host: one test passed, 1.00 s.
- Alpha scene host: fifteen scene cases across software/immediate/batched GL and restore, one test, 0.82 s.
- Root build after alpha integration: pass, 10.00 s.
- Before default tours and authored layouts: pass, 65.51 s. Analysis and after results are pending.

Before binary, explicitly rebuilt from starting main:
`e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.
All render commands use `--hero-name Preview` and `MU_GFX_PUBLIC_DEMO=1` limited to render subprocesses.

An early alpha host omitted its synthetic software camera matrices and drew no software pixels; identity
matrices corrected the fixture. The first small comparator caught the type-3 particle pair and Crywolf's
extra random kind selection; both corrected. The first alpha-enabled root build found two positional backend
initializers, which now explicitly initialize the new callback. No unresolved failures from these runs.

## Limits and next

| World / type | Remaining address or dependency |
|---|---|
| Kalima 15/29/32 | Hero motion helper `0x00dfa988` and water-height getter `0x00deeb4e` |
| Tower 39 type 0 | Parent `0x00e84941`, tower state at singleton +0x78, nested sequence `0x00e8d888` |
| 46/98 | Common chain `0x017fcb5c..0x017fccbc`, manager `0x00ea2dc1`, slot 0x34; no factory registration |

No new original input/capture. The private tools/python, evidence and input symlinks are never staged.
Lane scratch/renders stay under the matching `~/Documents/MTM/mu-mac-tools/native/` folders until checks finish.

## WIP

Done: producers/adapters, explicit refusal boundaries, small original comparisons, alpha scene implementation
and synthetic render checks, before default renders. Left: full original/mutant run, affected selection/checks,
8d reduced, after/reference render analysis, final main integration and docs/PR/ready entry.
Next: complete the affected selection after the root build, then execute the selected checks with jobs 2.
No PR-ready claim or ready-prs line yet.
