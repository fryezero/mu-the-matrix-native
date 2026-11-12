# ITEMS-UI-001

Branch `codex/items-ui-001`, based on main `d4af71dd`. GPT-6.1 Sol. Offline/static only.
No subagents, live client, installed apps, protection analysis or server data.
[Original addresses, observations and boundaries](../research/client-items-ui.md).

## WIP

Done: read the binding briefs and owning handoffs; isolated worktree and private-input
symlinks; baseline world binary rebuilt and saved; original cursor/WM_MOUSEMOVE conversion
recovered; native integer cursor and equipment tooltip implemented; focused arithmetic and
layer unit tests pass. A 200-case iteration produced 344 cursor, 264 mouse, 2,304 option-bit
and five static ordering checks, all with zero mismatches, 8.92 s.

The original low bits `0x87` do not add a glow in the compared bodies. Excellent and
set flags already reach rendering separately. Main-game GFx frame ordering reaches an
opaque hook and is explicitly unresolved; no guessed order change is made.

Native root build passes in 0.30 s and the rebuilt world in 5.30 s, with no compiler
warnings. Six focused portable/private tests pass in 6.42 s, including Retina hover,
rollout/close, a real fixed-clock equipment tooltip and all six accessory icons.
The stand-in test host emits three pre-existing missing-field-initializer warnings.
After binary SHA-256 is
`750020165d5a20bc1f8512ca564e17e27b45a81e4fd5910ed25621b2b31765dd`.

Checkpoint update: main `710ac816`, including UI-WINDOWS-001 #372, merged cleanly
as `43d97c28`. The full new validator at `57ad1819` passes 8,517 checks, zero
mismatches, and catches 8/8 compiled mutants in 20.12 s. The first mutant attempt
stopped on an unused-variable warning in the endpoint-rounding mutant; its anchor
was corrected, then the complete final run passed. No production arithmetic changed.
The native closed-inventory fast path was added afterward to avoid unnecessary
movie hit tests. Final affected checks cover that adapter change.

Affected selection: ten validator rows, 29.22 s; 123 test work items, including
121 native items, 71.34 s. Private tests will use the binding **8d reduced** cap.

Left: affected
selection/checks, private reduced tests, fixed-clock hover/overlap captures, final-main
merge, audit, status lines and PR/steward readiness.

Next: wait for the resource guard, run the build and new validator, then inspect a
native equipment hover with the fixed-clock library from canonical private-env.sh.

## Baseline

`mu-world` at `d4af71dd` SHA-256:
`4954601057b7ee7976c787157b321703d40c65dba68c46901b08d22adb1be76c`.
Built with `make -C native -j4 world`. Root/native builds succeeded; their wall time
was not instrumented. One world build was launched by a combined resource-print/build
command before its high-load output was inspected. Subsequent heavy launches inspect
the guard separately.

Baseline fixed-clock inventory/accessory scene: 5.25 s, nine equipment records,
37 item models, zero missing. Local files are under
`~/Documents/MTM/mu-mac-tools/native/scratch/items-ui-001/`; no game bytes or renders
are committed. The captures show only the native window framebuffer and the demo name
Preview. This lane does not replace the Native Preview app.
